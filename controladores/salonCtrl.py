from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, func
from database import ObtenerSes
from modelos.entidades import Grupo, Materia, Salon, Inscripcion, Usuario, Profesor, SesionToken
from servicios.eventos import GestorEv, ObservadorIA, ObservadorCon
from servicios.sesiones import ObtenerSesAct

router = APIRouter()


@router.get("/profesor/salones-disponibles/{id_grupo}", status_code=200)
def ObtenerSal(
    id_grupo: int,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    if sesion.rol != "Profesor":
        raise HTTPException(status_code=403, detail="Solo los profesores pueden acceder a esta operación.")

    grupo = session.get(Grupo, id_grupo)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado.")

    materia    = session.get(Materia, grupo.id_materia)
    salonesOcup = session.exec(
        select(Grupo.id_salon).where(
            Grupo.dia == grupo.dia, Grupo.hora == grupo.hora, Grupo.id != grupo.id
        )
    ).all()

    query = select(Salon)
    if salonesOcup:
        query = query.where(Salon.id.not_in(salonesOcup))

    return [
        {"id": s.id, "nombre": s.nombre, "capacidad": s.capacidad}
        for s in session.exec(query).all()
        if not (materia and materia.facultad == "Ciencias Básicas" and "Sala" in s.nombre)
    ]


@router.put("/profesor/cambiar-salon", status_code=200)
def CambiarSal(
    id_grupo: int,
    id_nuevo_salon: int,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    if sesion.rol != "Profesor":
        raise HTTPException(status_code=403, detail="Solo los profesores pueden cambiar salones.")

    us       = session.exec(select(Usuario).where(Usuario.codigo == sesion.codigo_usuario)).first()
    prof     = session.exec(select(Profesor).where(Profesor.id_usuario == us.id)).first()
    grupo    = session.get(Grupo, id_grupo)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado.")

    materia  = session.get(Materia, grupo.id_materia)
    nuevoSal = session.get(Salon, id_nuevo_salon)
    if not nuevoSal:
        raise HTTPException(status_code=404, detail="Salón no encontrado.")

    if prof.especialidad == "Ciencias Básicas" and "Sala" in nuevoSal.nombre:
        raise HTTPException(status_code=400, detail="Profesores de Ciencias Básicas no pueden usar salas de cómputo.")
    if materia and materia.facultad == "Ciencias Básicas" and "AULA" not in nuevoSal.nombre:
        raise HTTPException(status_code=400, detail="Incompatibilidad: materias de Ciencias Básicas no se dictan en laboratorios.")

    inscC = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == id_grupo)).one()
    if inscC > nuevoSal.capacidad:
        raise HTTPException(
            status_code=400,
            detail=f"Aforo excedido: el salón tiene capacidad para {nuevoSal.capacidad} y hay {inscC} inscritos."
        )

    grupo.id_salon = nuevoSal.id
    session.add(grupo)
    session.commit()

    gestor = GestorEv()
    gestor.suscribir(ObservadorIA())
    gestor.suscribir(ObservadorCon())
    gestor.NotificarTod("CAMBIO_SALON", {"grupo_id": id_grupo, "nuevo_salon_id": id_nuevo_salon, "session": session})

    return {"mensaje": "Salón actualizado y validación genética completada."}