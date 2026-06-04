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

# ── Franjas horarias: duracion exacta de 2 horas ─────────────────
# Jornada manana : 07-09, 09-11, 11-13
# Jornada noche  : 18-20, 20-22
# Sabado         : 07-09, 09-11, 11-13 + franja especial 15-17
FRANJAS_MANANA = ["07:00", "09:00", "11:00"]
FRANJAS_NOCHE  = ["18:00", "20:00"]
FRANJAS_SABADO = ["07:00", "09:00", "11:00", "15:00"]

FIN_FRANJA = {
    "07:00": "09:00",
    "09:00": "11:00",
    "11:00": "13:00",
    "15:00": "17:00",
    "18:00": "20:00",
    "20:00": "22:00",
}

# Pares de dias para clases 2 veces por semana (Lunes-Viernes)
PARES_DIAS_LV = [
    ("Lunes",     "Miercoles"),
    ("Martes",    "Jueves"),
    ("Miercoles", "Viernes"),
    ("Lunes",     "Jueves"),
    ("Martes",    "Viernes"),
]

# Sabado: la clase se dicta dos veces el mismo sabado
PARES_DIAS_SABADO = [("Sabado", "Sabado")]

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


def _salones_ocupados_en(session: Session, dia: str, hora: str,
                          excluir_grupo: int = 0) -> set:
    """OCP: consulta salones ocupados en ambas sesiones sin modificar logica existente."""
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
    """SRP: busca el primer salon libre del tipo preferido, con fallback."""
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


def _franjas_ya_usadas_globalmente(session: Session) -> set:
    """
    Retorna el conjunto de (dia, hora) que ya tiene al menos un grupo asignado.
    Incluye sesion_1 y sesion_2 de todos los grupos existentes.
    Sirve para que cada nueva materia reciba una franja distinta.
    """
    usadas: set = set()
    grupos = session.exec(select(Grupo)).all()
    for g in grupos:
        if g.dia  and g.hora:  usadas.add((g.dia,  g.hora))
        if g.dia2 and g.hora2: usadas.add((g.dia2, g.hora2))
    return usadas


def _buscar_franja_con_salones(session: Session, prefSal: str,
                                facultad: str, jornada: str = "manana",
                                franjas_bloqueadas: set = None):
    """
    SRP: encuentra la primera franja disponible con salones libres para 2 sesiones.
    OCP: agregar jornadas nuevas = agregar entradas en los diccionarios.
    franjas_bloqueadas: set de (dia, hora) que NO se pueden usar (horario del estudiante
                        o franjas ya ocupadas globalmente).
    Retorna (hora, dia1, id_salon1, dia2, id_salon2) o None.
    """
    fallback = "AULA-%" if facultad == "Sistemas" else None
    bloqueadas = franjas_bloqueadas or set()

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
            # Saltar si dia1+hora o dia2+hora ya están bloqueadas
            if (dia1, hora) in bloqueadas or (dia2, hora) in bloqueadas:
                continue
            ocup1 = _salones_ocupados_en(session, dia1, hora)
            ocup2 = _salones_ocupados_en(session, dia2, hora) if dia2 != dia1 else ocup1
            sal1  = _salon_libre(session, prefSal, fallback, ocup1)
            sal2  = _salon_libre(session, prefSal, fallback, ocup2)
            if sal1 and sal2:
                return hora, dia1, sal1.id, dia2, sal2.id
    return None


def _buscar_profesor(session: Session, facultad: str):
    """SRP: resuelve el profesor adecuado para la facultad dada."""
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
    catalogo=true  -> todas las materias (vista Ver Materias).
    catalogo=false -> filtradas por semestre/prerequisitos del estudiante.
    """
    materias = session.exec(select(Materia)).all()

    est:           object = None
    aprobadas_ids: set    = set()
    inscritas_ids: set    = set()

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

        resultado.append({
            "id": m.id, "nombre": m.nombre,
            "creditos": m.creditos, "facultad": m.facultad,
            "semestre": m.semestre, "prerequisito": prereq_nombre,
            "inscrita": m.id in inscritas_ids,
            "aprobada": m.id in aprobadas_ids,
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
            "limite": limite,
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

    # ── Franjas ya ocupadas por este estudiante ───────────────────────
    grupos_inscritos = session.exec(
        select(Grupo).join(Inscripcion, Grupo.id == Inscripcion.id_grupo).where(
            Inscripcion.id_estudiante == est.id
        )
    ).all()

    franjas_estudiante: set = set()
    for g in grupos_inscritos:
        if g.dia  and g.hora:  franjas_estudiante.add((g.dia,  g.hora))
        if g.dia2 and g.hora2: franjas_estudiante.add((g.dia2, g.hora2))

    def _tiene_conflicto(hora: str, dia1: str, dia2: str) -> bool:
        return (dia1, hora) in franjas_estudiante or (dia2, hora) in franjas_estudiante

    # ── Validacion: grupos existentes de esta materia vs horario del estudiante ──
    grupos_existentes = session.exec(
        select(Grupo).where(Grupo.id_materia == data.id_materia)
    ).all()
    todos_con_conflicto = [
        g for g in grupos_existentes
        if g.dia and g.hora and g.dia2 and g.hora2
        and _tiene_conflicto(g.hora, g.dia, g.dia2)
    ]
    # Si TODOS los grupos disponibles chocan, no hay salida — rechazar
    grupos_sin_conflicto = [
        g for g in grupos_existentes
        if g.dia and g.hora and g.dia2 and g.hora2
        and not _tiene_conflicto(g.hora, g.dia, g.dia2)
    ]
    if grupos_existentes and not grupos_sin_conflicto:
        g = todos_con_conflicto[0]
        raise HTTPException(
            status_code=409,
            detail=(
                f"Conflicto de horario: todos los grupos de '{materia.nombre}' "
                f"coinciden con clases que ya tienes. "
                f"El grupo 1 es {g.dia}/{g.dia2} a las {_hora_display(g.hora)}. "
                "Elige otra jornada o materia."
            )
        )

    profesorAs = _buscar_profesor(session, materia.facultad)
    id_prof    = profesorAs.id if profesorAs else None
    prefSal    = FACULTAD_A_SALON.get(materia.facultad, "AULA-%")
    limiteC    = CUPO_POR_FACULTAD.get(materia.facultad, 30)
    grupos     = session.exec(select(Grupo).where(Grupo.id_materia == data.id_materia)).all()
    jornada    = data.jornada or "manana"

    # Franjas globalmente ocupadas (para que cada materia nueva quede en franja distinta)
    franjas_globales = _franjas_ya_usadas_globalmente(session)
    # Al crear un grupo nuevo, bloqueamos tanto las del estudiante como las globales
    franjas_bloqueadas_nuevo = franjas_estudiante | franjas_globales

    def _crear_grupo(numero: int) -> Grupo:
        """
        SRP: fabrica interna que crea el grupo con ambas sesiones usando el Builder.
        Pasa franjas_bloqueadas para que el nuevo grupo NO caiga en una franja
        ya usada por otro grupo existente NI por el horario del estudiante.
        """
        franja = _buscar_franja_con_salones(
            session, prefSal, materia.facultad, jornada,
            franjas_bloqueadas=franjas_bloqueadas_nuevo
        )
        if not franja:
            # Fallback: ignorar globales pero respetar las del estudiante
            franja = _buscar_franja_con_salones(
                session, prefSal, materia.facultad, "manana",
                franjas_bloqueadas=franjas_estudiante
            )
        if not franja:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No hay franjas horarias disponibles sin conflicto "
                    "con tu horario actual. Intenta con otra jornada."
                )
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
                raise HTTPException(
                    status_code=400,
                    detail="El grupo seleccionado no es valido para esta materia."
                )
            # Validar que el grupo elegido manualmente no choque
            if grupoEleg.dia and grupoEleg.hora and _tiene_conflicto(grupoEleg.hora, grupoEleg.dia, grupoEleg.dia2 or grupoEleg.dia):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"El grupo {grupoEleg.num_grupo} choca con tu horario actual "
                        f"({grupoEleg.dia}/{grupoEleg.dia2} a las {_hora_display(grupoEleg.hora)}). "
                        "Elige otro grupo o jornada."
                    )
                )
        else:
            # Elegir el primer grupo sin conflicto con el estudiante
            if grupos_sin_conflicto:
                grupoEleg = ContextoIns(EstrategiaVac()).seleccionar(grupos_sin_conflicto, session)
            else:
                # No habia grupos previos con horario asignado — crear uno nuevo libre
                grupoEleg = _crear_grupo(len(grupos) + 1)
                session.add(grupoEleg)
                session.commit()
                session.refresh(grupoEleg)
                inscritos = 0

        if 'inscritos' not in dir():
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
        return {"alerta": False,
                "mensaje": f"Matricula exitosa. Se aperturo la seccion {nuevoGrup.num_grupo}.{aviso}"}

    session.add(Inscripcion(
        id_estudiante=est.id, id_materia=data.id_materia,
        id_grupo=grupoEleg.id, estado="Activo", aprobada=None
    ))
    session.commit()
    aviso = "" if grupoEleg.id_profesor else " (sin profesor aun, se asignara automaticamente)"
    return {"alerta": False,
            "mensaje": f"Matricula exitosa en el Grupo {grupoEleg.num_grupo}.{aviso}"}


@router.put("/inscripcion/{id_inscripcion}/estado", status_code=200)
def ActualizarEstado(
    id_inscripcion: int,
    aprobada: bool,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    if sesion.rol not in ["Profesor", "Administrador"]:
        raise HTTPException(
            status_code=403,
            detail="Solo profesores y administradores pueden calificar."
        )
    insc = session.get(Inscripcion, id_inscripcion)
    if not insc:
        raise HTTPException(status_code=404, detail="Inscripcion no encontrada.")
    insc.aprobada = aprobada
    insc.estado   = "Aprobado" if aprobada else "Reprobado"
    session.add(insc)
    session.commit()
    return {"mensaje": "Estado actualizado correctamente."}