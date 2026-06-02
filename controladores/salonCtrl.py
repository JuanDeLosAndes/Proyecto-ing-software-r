from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, func
from database import ObtenerSes
from modelos.entidades import (
    Grupo, Materia, Salon, Inscripcion,
    Usuario, Profesor, SesionToken
)
from servicios.eventos import GestorEv, ObservadorCon
from servicios.sesiones import ObtenerSesAct

router = APIRouter()


def _ocupados_en(session: Session, dia: str, hora: str, excluir_id: int) -> set:
    s1 = session.exec(
        select(Grupo.id_salon).where(
            Grupo.dia  == dia, Grupo.hora  == hora,
            Grupo.id   != excluir_id, Grupo.id_salon != None
        )
    ).all()
    s2 = session.exec(
        select(Grupo.id_salon2).where(
            Grupo.dia2 == dia, Grupo.hora2 == hora,
            Grupo.id   != excluir_id, Grupo.id_salon2 != None
        )
    ).all()
    return {x for x in (s1 + s2) if x}


def _salon_valido_para_facultad(salon: Salon, facultad: str) -> bool:
    """
    Ciencias Basicas solo aulas (nunca Salas de Computo).
    Sistemas  prefiere salas, puede usar aulas.
    """
    if facultad == "Ciencias Básicas" and "Sala" in salon.nombre:
        return False
    return True


@router.get("/profesor/salones-disponibles/{id_grupo}", status_code=200)
def ObtenerSal(
    id_grupo: int,
    num_sesion: int = 1,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    """
    Filtra ocupados y filtra incompatibles con la facultad:
    Ciencias Basicas nunca ve Salas de Computo.
    """
    if sesion.rol != "Profesor":
        raise HTTPException(status_code=403, detail="Solo los profesores pueden acceder a esta operacion.")

    grupo = session.get(Grupo, id_grupo)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado.")

    materia  = session.get(Materia, grupo.id_materia)
    dia      = grupo.dia  if num_sesion == 1 else grupo.dia2
    hora     = grupo.hora if num_sesion == 1 else grupo.hora2

    if not dia or not hora:
        raise HTTPException(status_code=400, detail=f"El grupo no tiene sesion {num_sesion} configurada.")

    ocupados = _ocupados_en(session, dia, hora, grupo.id)
    facultad = materia.facultad if materia else None

    query = select(Salon)
    if ocupados:
        query = query.where(Salon.id.not_in(ocupados))

    return [
        {"id": s.id, "nombre": s.nombre, "capacidad": s.capacidad}
        for s in session.exec(query).all()
        if not facultad or _salon_valido_para_facultad(s, facultad)
    ]


@router.put("/profesor/cambiar-salon", status_code=200)
def CambiarSal(
    id_grupo: int,
    id_nuevo_salon: int,
    num_sesion: int = 1,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    """
    si prof cambia salon
    Valida compatibilidad de facultad, aforo y disponibilidad.
    """
    if sesion.rol != "Profesor":
        raise HTTPException(status_code=403, detail="Solo los profesores pueden cambiar salones.")

    us    = session.exec(select(Usuario).where(Usuario.codigo == sesion.codigo_usuario)).first()
    prof  = session.exec(select(Profesor).where(Profesor.id_usuario == us.id)).first()
    grupo = session.get(Grupo, id_grupo)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado.")

    if grupo.id_profesor != prof.id:
        raise HTTPException(status_code=403, detail="Solo puedes cambiar salones de tus propios grupos.")

    materia  = session.get(Materia, grupo.id_materia)
    nuevoSal = session.get(Salon,   id_nuevo_salon)
    if not nuevoSal:
        raise HTTPException(status_code=404, detail="Salon no encontrado.")

    facultad = materia.facultad if materia else None
    if facultad and not _salon_valido_para_facultad(nuevoSal, facultad):
        raise HTTPException(
            status_code=400,
            detail="Las materias de Ciencias Basicas no se dictan en Salas de Computo."
        )

    inscC = session.exec(
        select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == id_grupo)
    ).one()
    if inscC > nuevoSal.capacidad:
        raise HTTPException(
            status_code=400,
            detail=f"Aforo excedido: el salon tiene {nuevoSal.capacidad} lugares para {inscC} inscritos."
        )

    dia  = grupo.dia  if num_sesion == 1 else grupo.dia2
    hora = grupo.hora if num_sesion == 1 else grupo.hora2
    if dia and hora:
        ocupados = _ocupados_en(session, dia, hora, grupo.id)
        if id_nuevo_salon in ocupados:
            raise HTTPException(
                status_code=409,
                detail=f"El salon '{nuevoSal.nombre}' ya esta ocupado en {dia} {hora}."
            )

    if num_sesion == 1:
        grupo.id_salon  = nuevoSal.id
    else:
        grupo.id_salon2 = nuevoSal.id
    session.add(grupo)
    session.commit()

    gestor = GestorEv()
    gestor.suscribir(ObservadorCon())
    gestor.NotificarTod("CAMBIO_SALON", {
        "grupo_id": id_grupo, "nuevo_salon_id": id_nuevo_salon,
        "num_sesion": num_sesion
    })

    return {
        "mensaje": (
            f"Salon de sesion {num_sesion} actualizado a '{nuevoSal.nombre}'. "
            "Los estudiantes del grupo veran el cambio de inmediato."
        )
    }