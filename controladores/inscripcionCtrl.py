from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, func
from database import ObtenerSes
from modelos.entidades import (
    Usuario, Estudiante, Materia, Salon, Grupo,
    Inscripcion, Profesor, SesionToken
)
from modelos.esquemas import EsquemaMatric
from servicios.eventos import ContextoIns, EstrategiaVac
from servicios.fabricas import ConstructorGrup
from servicios.sesiones import ObtenerSesAct

router = APIRouter()

# ── Reglas de horario (SRP: constantes aisladas, no dispersas en el codigo) ──
# Franjas de 2 horas: manana 7-13, noche 18-22
FRANJAS_HORARIO = ["07:00", "09:00", "11:00", "18:00", "20:00"]

# Pares de dias para las 2 sesiones semanales
PARES_DIAS = [
    ("Lunes",    "Miercoles"),
    ("Martes",   "Jueves"),
    ("Miercoles","Viernes"),
    ("Lunes",    "Jueves"),
    ("Martes",   "Viernes"),
]

FIN_FRANJA = {
    "07:00": "09:00", "09:00": "11:00", "11:00": "13:00",
    "18:00": "20:00", "20:00": "22:00"
}


def _hora_display(hora: str) -> str:
    """Formatea "07:00" -> "07:00 - 09:00" para mostrar en el horario."""
    return f"{hora} - {FIN_FRANJA.get(hora, hora)}"


def _salones_ocupados_en(session: Session, dia: str, hora: str, excluir_grupo: int = 0):
    """
    OCP: funcion unica para consultar salones ocupados en una franja,
    revisando AMBAS sesiones de todos los grupos.
    """
    ocup_s1 = session.exec(
        select(Grupo.id_salon).where(
            Grupo.dia  == dia,  Grupo.hora  == hora,
            Grupo.id   != excluir_grupo,
            Grupo.id_salon != None
        )
    ).all()
    ocup_s2 = session.exec(
        select(Grupo.id_salon2).where(
            Grupo.dia2 == dia,  Grupo.hora2 == hora,
            Grupo.id   != excluir_grupo,
            Grupo.id_salon2 != None
        )
    ).all()
    return {x for x in (ocup_s1 + ocup_s2) if x}


def _buscar_franja_con_salones(session: Session, prefSal: str, facultad: str):
    """
    Builder: busca la primera franja horaria (hora + par de dias)
    que tenga salones libres para ambas sesiones.
    Retorna (hora, dia1, id_salon1, dia2, id_salon2) o None.
    """
    for hora in FRANJAS_HORARIO:
        for dia1, dia2 in PARES_DIAS:
            ocup1 = _salones_ocupados_en(session, dia1, hora)
            ocup2 = _salones_ocupados_en(session, dia2, hora)

            q1 = select(Salon).where(Salon.nombre.like(prefSal))
            if ocup1:
                q1 = q1.where(Salon.id.not_in(ocup1))
            sal1 = session.exec(q1).first()

            if not sal1:
                if facultad == "Sistemas":
                    q1b = select(Salon).where(Salon.nombre.like("AULA-%"))
                    if ocup1:
                        q1b = q1b.where(Salon.id.not_in(ocup1))
                    sal1 = session.exec(q1b).first()
                if not sal1:
                    continue

            q2 = select(Salon).where(Salon.nombre.like(prefSal))
            if ocup2:
                q2 = q2.where(Salon.id.not_in(ocup2))
            sal2 = session.exec(q2).first()

            if not sal2:
                if facultad == "Sistemas":
                    q2b = select(Salon).where(Salon.nombre.like("AULA-%"))
                    if ocup2:
                        q2b = q2b.where(Salon.id.not_in(ocup2))
                    sal2 = session.exec(q2b).first()
                if not sal2:
                    continue

            return hora, dia1, sal1.id, dia2, sal2.id

    return None


@router.get("/materias", status_code=200)
def ListarMaterias(
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    """Lista el pensum con semestre y prerequisito. Jinja2: usado en asignacion.html."""
    materias = session.exec(select(Materia)).all()
    resultado = []
    for m in materias:
        prereq = None
        if m.id_prerequisito:
            pm = session.get(Materia, m.id_prerequisito)
            prereq = pm.nombre if pm else None
        resultado.append({
            "id": m.id, "nombre": m.nombre,
            "creditos": m.creditos, "facultad": m.facultad,
            "semestre": m.semestre, "prerequisito": prereq
        })
    return sorted(resultado, key=lambda x: (x["semestre"], x["nombre"]))


@router.get("/materias/{id_materia}/grupos", status_code=200)
def ObtenerGrup(
    id_materia: int,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    materia = session.get(Materia, id_materia)
    if not materia:
        raise HTTPException(status_code=404, detail="Materia no encontrada.")

    grupos = session.exec(select(Grupo).where(Grupo.id_materia == id_materia)).all()
    limite = 30 if materia.facultad == "Sistemas" else 35

    return [
        {
            "id_grupo":  g.id,
            "num_grupo": g.num_grupo,
            "sesion_1":  f"{g.dia} {_hora_display(g.hora)}"  if g.dia  and g.hora  else "Sin asignar",
            "sesion_2":  f"{g.dia2} {_hora_display(g.hora2)}" if g.dia2 and g.hora2 else "Sin asignar",
            "inscritos": session.exec(
                select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)
            ).one(),
            "limite": limite
        }
        for g in grupos
    ]


@router.post("/inscribir", status_code=201)
def InscribirEst(
    data: EsquemaMatric,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    if sesion.rol != "Estudiante":
        raise HTTPException(status_code=403, detail="Solo los estudiantes pueden inscribirse.")

    us      = session.exec(select(Usuario).where(Usuario.codigo == sesion.codigo_usuario)).first()
    est     = session.exec(select(Estudiante).where(Estudiante.id_usuario == us.id)).first()
    materia = session.get(Materia, data.id_materia)

    if not materia:
        raise HTTPException(status_code=404, detail="Materia no encontrada.")

    # ── Validacion 1: semestre del estudiante ──
    if est.semestre < materia.semestre:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No puedes inscribir materias de semestre {materia.semestre}. "
                f"Tu semestre actual es {est.semestre}."
            )
        )

    # ── Validacion 2: prerequisito de Ciencias Basicas ──
    if materia.id_prerequisito:
        prereq_mat = session.get(Materia, materia.id_prerequisito)
        prereq_ok  = session.exec(
            select(Inscripcion).where(
                Inscripcion.id_estudiante == est.id,
                Inscripcion.id_materia    == materia.id_prerequisito,
                Inscripcion.aprobada      == True
            )
        ).first()
        if not prereq_ok:
            nombre_pre = prereq_mat.nombre if prereq_mat else f"ID {materia.id_prerequisito}"
            raise HTTPException(
                status_code=400,
                detail=f"Prerequisito no cumplido: debes aprobar '{nombre_pre}' antes de inscribir '{materia.nombre}'."
            )

    # ── Validacion 3: no duplicar ──
    if session.exec(
        select(Inscripcion).where(
            Inscripcion.id_estudiante == est.id,
            Inscripcion.id_materia    == data.id_materia
        )
    ).first():
        raise HTTPException(status_code=409, detail="Ya estas matriculado en esta materia.")

    # ── Asignacion automatica de profesor ──
    especReq   = "Ingeniería de Sistemas" if materia.facultad == "Sistemas" else "Ciencias Básicas"
    profesorAs = session.exec(select(Profesor).where(Profesor.especialidad == especReq)).first()
    if not profesorAs:
        raise HTTPException(status_code=400, detail="No hay profesores con la especialidad requerida.")

    grupos  = session.exec(select(Grupo).where(Grupo.id_materia == data.id_materia)).all()
    limiteC = 30 if materia.facultad == "Sistemas" else 35
    prefSal = "Sala de Computo%" if materia.facultad == "Sistemas" else "AULA-%"

    # ── Crear nuevo grupo con 2 sesiones automaticas ──
    if not grupos:
        franja = _buscar_franja_con_salones(session, prefSal, materia.facultad)
        if not franja:
            raise HTTPException(
                status_code=400,
                detail="No hay franjas horarias disponibles con salones libres para 2 sesiones."
            )
        hora, dia1, id_sal1, dia2, id_sal2 = franja

        grupoEleg = (ConstructorGrup()
            .conNumero(1)
            .conMateria(data.id_materia)
            .conSalon(id_sal1)
            .conProfesor(profesorAs.id)
            .conHorario(dia1, hora)
            .construir())
        # Asignar sesion 2
        grupoEleg.dia2      = dia2
        grupoEleg.hora2     = hora   # misma franja horaria, dia diferente
        grupoEleg.id_salon2 = id_sal2

        session.add(grupoEleg)
        session.commit()
        session.refresh(grupoEleg)
        inscritos = 0

    else:
        if data.id_grupo:
            grupoEleg = session.get(Grupo, data.id_grupo)
            if not grupoEleg or grupoEleg.id_materia != data.id_materia:
                raise HTTPException(status_code=400, detail="El grupo seleccionado no es valido para esta materia.")
        else:
            grupoEleg = ContextoIns(EstrategiaVac()).seleccionar(list(grupos), session)
        inscritos = session.exec(
            select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == grupoEleg.id)
        ).one()

    # ── Apertura de nueva seccion si el grupo esta lleno ──
    if inscritos >= limiteC:
        franja = _buscar_franja_con_salones(session, prefSal, materia.facultad)
        if not franja:
            raise HTTPException(status_code=400, detail="No hay salones disponibles para aperturar un nuevo grupo.")

        hora, dia1, id_sal1, dia2, id_sal2 = franja
        nuevoGrup = (ConstructorGrup()
            .conNumero(len(grupos) + 1)
            .conMateria(data.id_materia)
            .conSalon(id_sal1)
            .conProfesor(profesorAs.id)
            .conHorario(dia1, hora)
            .construir())
        nuevoGrup.dia2      = dia2
        nuevoGrup.hora2     = hora
        nuevoGrup.id_salon2 = id_sal2

        session.add(nuevoGrup)
        session.commit()
        session.refresh(nuevoGrup)

        for estIns in session.exec(
            select(Inscripcion).where(Inscripcion.id_grupo == grupoEleg.id).limit(4)
        ).all():
            estIns.id_grupo = nuevoGrup.id
            session.add(estIns)

        session.add(Inscripcion(
            id_estudiante=est.id, id_materia=data.id_materia,
            id_grupo=nuevoGrup.id, estado="Activo", aprobada=None
        ))
        session.commit()
        return {"alerta": False, "mensaje": f"Matricula exitosa. Se aperturo la seccion {nuevoGrup.num_grupo}."}

    session.add(Inscripcion(
        id_estudiante=est.id, id_materia=data.id_materia,
        id_grupo=grupoEleg.id, estado="Activo", aprobada=None
    ))
    session.commit()
    return {"alerta": False, "mensaje": f"Matricula exitosa en el Grupo {grupoEleg.num_grupo}."}


@router.put("/inscripcion/{id_inscripcion}/estado", status_code=200)
def ActualizarEstado(
    id_inscripcion: int,
    aprobada: bool,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    if sesion.rol not in ["Profesor", "Administrador"]:
        raise HTTPException(status_code=403, detail="Solo profesores y administradores pueden calificar.")
    insc = session.get(Inscripcion, id_inscripcion)
    if not insc:
        raise HTTPException(status_code=404, detail="Inscripcion no encontrada.")
    insc.aprobada = aprobada
    insc.estado   = "Aprobado" if aprobada else "Reprobado"
    session.add(insc)
    session.commit()
    return {"mensaje": f"Estado actualizado: {'Aprobado' if aprobada else 'Reprobado'}."}