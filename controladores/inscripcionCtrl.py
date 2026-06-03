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

# ── Franjas horarias: 2h de duracion obligatoria ──────────────────
# Jornada manana : 07-09, 09-11, 11-13
# Jornada noche  : 18-20, 20-22
# Sabado manana  : 07-09, 09-11, 11-13
# Sabado especial: 15-17 (unica franja de tarde, solo sabado)
FRANJAS_MANANA  = ["07:00", "09:00", "11:00"]
FRANJAS_NOCHE   = ["18:00", "20:00"]
FRANJAS_SABADO  = ["07:00", "09:00", "11:00", "15:00"]

FIN_FRANJA = {
    "07:00": "09:00",
    "09:00": "11:00",
    "11:00": "13:00",
    "15:00": "17:00",
    "18:00": "20:00",
    "20:00": "22:00",
}

PARES_DIAS_LV = [
    ("Lunes",     "Miercoles"),
    ("Martes",    "Jueves"),
    ("Miercoles", "Viernes"),
    ("Lunes",     "Jueves"),
    ("Martes",    "Viernes"),
]

PARES_DIAS_SABADO = [("Sabado", "Sabado")]

FRANJAS_POR_JORNADA = {
    "manana": FRANJAS_MANANA,
    "noche":  FRANJAS_NOCHE,
    "sabado": FRANJAS_SABADO,
}

FACULTAD_A_ESPECIALIDAD = {
    "Sistemas":         "Ingeniería de Sistemas",
    "Ciencias Básicas": "Ciencias Básicas",
}

FACULTAD_A_SALON = {
    "Sistemas":         "Sala de Computo%",
    "Ciencias Básicas": "AULA-%",
}

CUPO_POR_FACULTAD = {
    "Sistemas":         30,
    "Ciencias Básicas": 35,
}


def _hora_display(hora: str) -> str:
    return f"{hora} - {FIN_FRANJA.get(hora, hora)}"


def _salones_ocupados_en(session: Session, dia: str, hora: str, excluir_grupo: int = 0) -> set:
    """OCP: consulta salones ocupados revisando AMBAS sesiones."""
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


def _salon_libre(session: Session, pref: str, fallback: str, ocupados: set):
    """SRP: busca primer salon libre del tipo preferido, o fallback."""
    q = select(Salon).where(Salon.nombre.like(pref))
    if ocupados:
        q = q.where(Salon.id.not_in(ocupados))
    sal = session.exec(q).first()
    if not sal and fallback:
        q2 = select(Salon).where(Salon.nombre.like(fallback))
        if ocupados:
            q2 = q2.where(Salon.id.not_in(ocupados))
        sal = session.exec(q2).first()
    return sal


def _buscar_franja_con_salones(session: Session, prefSal: str, facultad: str, jornada: str = "manana"):
    """
    Builder: busca franja libre para 2 sesiones semanales.
    jornada = 'manana' | 'noche' | 'sabado'
    Retorna (hora, dia1, id_salon1, dia2, id_salon2) o None.
    """
    fallback = "AULA-%" if facultad == "Sistemas" else None

    if jornada == "sabado":
        franjas = FRANJAS_SABADO
        pares   = PARES_DIAS_SABADO
    elif jornada == "noche":
        franjas = FRANJAS_NOCHE
        pares   = PARES_DIAS_LV
    else:
        franjas = FRANJAS_MANANA
        pares   = PARES_DIAS_LV

    for hora in franjas:
        for dia1, dia2 in pares:
            ocup1 = _salones_ocupados_en(session, dia1, hora)
            ocup2 = _salones_ocupados_en(session, dia2, hora) if dia2 != dia1 else ocup1
            sal1  = _salon_libre(session, prefSal, fallback, ocup1)
            sal2  = _salon_libre(session, prefSal, fallback, ocup2)
            if sal1 and sal2:
                return hora, dia1, sal1.id, dia2, sal2.id
    return None


def _buscar_profesor(session: Session, facultad: str):
    especialidad = FACULTAD_A_ESPECIALIDAD.get(facultad)
    if not especialidad:
        return None
    return session.exec(
        select(Profesor).where(Profesor.especialidad == especialidad)
    ).first()


@router.get("/materias", status_code=200)
def ListarMaterias(
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes),
    catalogo: bool = False
):
    """
    Lista materias.
    - catalogo=true  → devuelve TODAS las 20 materias (vista 'Ver Materias').
    - catalogo=false → filtra por semestre/prerequisitos del estudiante (para inscribir).
    """
    materias = session.exec(select(Materia)).all()

    est            = None
    aprobadas_ids: set = set()
    inscritas_ids: set = set()

    if sesion.rol == "Estudiante" and not catalogo:
        us = session.exec(
            select(Usuario).where(Usuario.codigo == sesion.codigo_usuario)
        ).first()
        if us:
            est = session.exec(
                select(Estudiante).where(Estudiante.id_usuario == us.id)
            ).first()
        if est:
            aprobadas_ids = {
                i.id_materia
                for i in session.exec(
                    select(Inscripcion).where(
                        Inscripcion.id_estudiante == est.id,
                        Inscripcion.aprobada == True
                    )
                ).all()
            }
            inscritas_ids = {
                i.id_materia
                for i in session.exec(
                    select(Inscripcion).where(Inscripcion.id_estudiante == est.id)
                ).all()
            }

    resultado = []
    for m in materias:
        prereq_nombre = None
        if m.id_prerequisito:
            pm = session.get(Materia, m.id_prerequisito)
            prereq_nombre = pm.nombre if pm else None

        if est and not catalogo:
            if m.semestre > est.semestre:
                continue
            if m.id in inscritas_ids:
                continue
            if m.id_prerequisito and m.id_prerequisito not in aprobadas_ids:
                continue

        inscrita = m.id in inscritas_ids
        aprobada = m.id in aprobadas_ids

        resultado.append({
            "id": m.id, "nombre": m.nombre,
            "creditos": m.creditos, "facultad": m.facultad,
            "semestre": m.semestre, "prerequisito": prereq_nombre,
            "inscrita": inscrita, "aprobada": aprobada
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
    limite = CUPO_POR_FACULTAD.get(materia.facultad, 30)

    return [
        {
            "id_grupo":  g.id,
            "num_grupo": g.num_grupo,
            "profesor":  session.get(Profesor, g.id_profesor).nombre
                         if g.id_profesor else "Sin asignar",
            "sesion_1":  f"{g.dia} {_hora_display(g.hora)}"   if g.dia  and g.hora  else "Sin asignar",
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

    if est.semestre < materia.semestre:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No puedes inscribir materias de semestre {materia.semestre}. "
                f"Tu semestre actual es {est.semestre}."
            )
        )

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
                detail=(
                    f"Prerequisito no cumplido: debes aprobar '{nombre_pre}' "
                    f"antes de inscribir '{materia.nombre}'."
                )
            )

    if session.exec(
        select(Inscripcion).where(
            Inscripcion.id_estudiante == est.id,
            Inscripcion.id_materia    == data.id_materia
        )
    ).first():
        raise HTTPException(status_code=409, detail="Ya estas matriculado en esta materia.")

    profesorAs = _buscar_profesor(session, materia.facultad)
    id_prof    = profesorAs.id if profesorAs else None

    prefSal = FACULTAD_A_SALON.get(materia.facultad, "AULA-%")
    limiteC = CUPO_POR_FACULTAD.get(materia.facultad, 30)
    grupos  = session.exec(select(Grupo).where(Grupo.id_materia == data.id_materia)).all()
    jornada = data.jornada or "manana"

    def _crear_grupo(numero: int) -> Grupo:
        """SRP: crea grupo con 2 sesiones usando el Builder completo."""
        franja = _buscar_franja_con_salones(session, prefSal, materia.facultad, jornada)
        if not franja:
            franja = _buscar_franja_con_salones(session, prefSal, materia.facultad, "manana")
        if not franja:
            raise HTTPException(
                status_code=400,
                detail="No hay franjas horarias disponibles con salones libres para 2 sesiones."
            )
        hora, dia1, id_sal1, dia2, id_sal2 = franja
        return (ConstructorGrup()
            .conNumero(numero)
            .conMateria(data.id_materia)
            .conSalon(id_sal1)
            .conProfesor(id_prof)
            .conHorario(dia1, hora)
            .conSesion2(dia2, hora, id_sal2)
            .construir())

    if not grupos:
        grupoEleg = _crear_grupo(1)
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

    if inscritos >= limiteC:
        nuevoGrup = _crear_grupo(len(grupos) + 1)
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
        aviso = "" if id_prof else " (sin profesor aun, se asignara automaticamente)"
        return {"alerta": False, "mensaje": f"Matricula exitosa. Se aperturo la seccion {nuevoGrup.num_grupo}.{aviso}"}

    session.add(Inscripcion(
        id_estudiante=est.id, id_materia=data.id_materia,
        id_grupo=grupoEleg.id, estado="Activo", aprobada=None
    ))
    session.commit()
    aviso = "" if grupoEleg.id_profesor else " (sin profesor aun, se asignara automaticamente)"
    return {"alerta": False, "mensaje": f"Matricula exitosa en el Grupo {grupoEleg.num_grupo}.{aviso}"}


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