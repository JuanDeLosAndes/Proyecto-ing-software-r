from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, func
from database import ObtenerSes
from modelos.entidades import (
    Grupo, Materia, Salon, Inscripcion,
    Usuario, Profesor, SesionToken
)

from servicios.eventos import obtener_gestor
from servicios.sesiones import ObtenerSesAct

router = APIRouter()


def _ocupados_en(session: Session, dia: str, hora: str, excluir_id: int) -> set:
    """SRP: devuelve IDs de salones ocupados en una franja dada."""
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
    OCP: regla de compatibilidad en un solo lugar.
    Ciencias Basicas nunca usa Salas de Computo.
    """
    if facultad == "Ciencias Básicas" and "Sala" in salon.nombre:
        return False
    return True


def _obtener_profesor_de_sesion(sesion: SesionToken, session: Session) -> Profesor:
    """SRP: resuelve el Profesor a partir del token de sesion."""
    us = session.exec(
        select(Usuario).where(Usuario.codigo == sesion.codigo_usuario)
    ).first()
    if not us:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    prof = session.exec(
        select(Profesor).where(Profesor.id_usuario == us.id)
    ).first()
    if not prof:
        raise HTTPException(status_code=404, detail="Perfil de profesor no encontrado.")
    return prof



@router.get("/mis-grupos", status_code=200)
def MisGrupos(
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    """Devuelve los grupos asignados al profesor autenticado."""
    if sesion.rol != "Profesor":
        raise HTTPException(status_code=403, detail="Solo los profesores pueden acceder.")
    prof = _obtener_profesor_de_sesion(sesion, session)
    grupos = session.exec(select(Grupo).where(Grupo.id_profesor == prof.id)).all()
    resultado = []
    for g in grupos:
        mat = session.get(Materia, g.id_materia)
        resultado.append({
            "id_grupo":  g.id,
            "num_grupo": g.num_grupo,
            "materia":   mat.nombre if mat else "—",
            "dia":       g.dia  or "—",
            "hora":      g.hora or "—",
        })
    return resultado



@router.get("/salones-libres", status_code=200)
def SalonesLibres(
    id_grupo: int,
    num_sesion: int = 1,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    """
    Alias simplificado para el frontend.
    Filtra salones incompatibles con la facultad.
    """
    if sesion.rol != "Profesor":
        raise HTTPException(status_code=403, detail="Solo los profesores pueden acceder.")

    grupo = session.get(Grupo, id_grupo)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado.")

    materia  = session.get(Materia, grupo.id_materia)
    dia      = grupo.dia  if num_sesion == 1 else grupo.dia2
    hora     = grupo.hora if num_sesion == 1 else grupo.hora2

    if not dia or not hora:
        raise HTTPException(
            status_code=400,
            detail=f"El grupo no tiene sesion {num_sesion} configurada."
        )

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



@router.put("/grupos/{id_grupo}/salon/{id_nuevo_salon}", status_code=200)
def CambiarSalPorRuta(
    id_grupo: int,
    id_nuevo_salon: int,
    num_sesion: int = 1,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    """
    Endpoint con ruta limpia para el frontend.
    DIP: notifica via gestor global, sin instanciar concretos aqui.
    """
    if sesion.rol != "Profesor":
        raise HTTPException(status_code=403, detail="Solo los profesores pueden cambiar salones.")

    prof  = _obtener_profesor_de_sesion(sesion, session)
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

    obtener_gestor().NotificarTod("CAMBIO_SALON", {
        "grupo_id":       id_grupo,
        "nuevo_salon_id": id_nuevo_salon,
        "num_sesion":     num_sesion,
    })

    return {
        "mensaje": (
            f"Salon de sesion {num_sesion} actualizado a '{nuevoSal.nombre}'. "
            "Los estudiantes del grupo veran el cambio de inmediato."
        )
    }



@router.get("/profesor/salones-disponibles/{id_grupo}", status_code=200)
def ObtenerSal(
    id_grupo: int,
    num_sesion: int = 1,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    """Endpoint original — redirige a SalonesLibres para no duplicar logica."""
    return SalonesLibres(id_grupo=id_grupo, num_sesion=num_sesion,
                         sesion=sesion, session=session)


@router.put("/profesor/cambiar-salon", status_code=200)
def CambiarSal(
    id_grupo: int,
    id_nuevo_salon: int,
    num_sesion: int = 1,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    """Endpoint original — delega en CambiarSalPorRuta para no duplicar logica."""
    return CambiarSalPorRuta(
        id_grupo=id_grupo, id_nuevo_salon=id_nuevo_salon,
        num_sesion=num_sesion, sesion=sesion, session=session
    )