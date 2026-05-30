from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, func
from database import ObtenerSes
from modelos.entidades import Usuario, Estudiante, Materia, Salon, Grupo, Inscripcion, Profesor, SesionToken
from modelos.esquemas import EsquemaMatric
from servicios.eventos import ContextoIns, EstrategiaVac
from servicios.fabricas import ConstructorGrup
from servicios.sesiones import ObtenerSesAct

router = APIRouter()


@router.get("/materias/{id_materia}/grupos", status_code=200)
def ObtenerGrup(
    id_materia: int,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    materia = session.get(Materia, id_materia)
    if not materia:
        raise HTTPException(status_code=404, detail="Materia no encontrada.")

    grupos  = session.exec(select(Grupo).where(Grupo.id_materia == id_materia)).all()
    limite  = 30 if materia.facultad == "Sistemas" else 35

    return [
        {
            "id_grupo":  g.id,
            "num_grupo": g.num_grupo,
            "dia":       g.dia,
            "hora":      g.hora,
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

    if session.exec(
        select(Inscripcion).where(
            Inscripcion.id_estudiante == est.id,
            Inscripcion.id_materia == data.id_materia
        )
    ).first():
        raise HTTPException(status_code=409, detail="Ya estás matriculado en esta materia.")

    especReq   = "Ingeniería de Sistemas" if materia.facultad == "Sistemas" else "Ciencias Básicas"
    profesorAs = session.exec(select(Profesor).where(Profesor.especialidad == especReq)).first()
    if not profesorAs:
        raise HTTPException(status_code=400, detail="No hay profesores con la especialidad requerida.")

    grupos   = session.exec(select(Grupo).where(Grupo.id_materia == data.id_materia)).all()
    limiteC  = 30 if materia.facultad == "Sistemas" else 35
    prefSal  = "Sala de Computo%" if materia.facultad == "Sistemas" else "AULA-%"

    if not grupos:
        sal = session.exec(select(Salon).where(Salon.nombre.like(prefSal))).first()
        if not sal:
            raise HTTPException(status_code=400, detail="No hay salones disponibles para esta facultad.")
        grupoEleg = (ConstructorGrup()
            .conNumero(1).conMateria(data.id_materia)
            .conSalon(sal.id).conProfesor(profesorAs.id)
            .conHorario("Lunes", "7:00").construir())
        session.add(grupoEleg)
        session.commit()
        session.refresh(grupoEleg)
        inscritos = 0
    else:
        if data.id_grupo:
            grupoEleg = session.get(Grupo, data.id_grupo)
            if not grupoEleg or grupoEleg.id_materia != data.id_materia:
                raise HTTPException(status_code=400, detail="El grupo seleccionado no es válido para esta materia.")
        else:
            grupoEleg = ContextoIns(EstrategiaVac()).seleccionar(list(grupos), session)
        inscritos = session.exec(
            select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == grupoEleg.id)
        ).one()

    if inscritos >= limiteC:
        ocupados = session.exec(
            select(Grupo.id_salon).where(Grupo.dia == grupoEleg.dia, Grupo.hora == grupoEleg.hora)
        ).all()
        nuevoSal = session.exec(
            select(Salon).where(Salon.nombre.like(prefSal))
            .where(Salon.id.not_in(ocupados) if ocupados else True)
        ).first()
        if not nuevoSal and materia.facultad == "Sistemas":
            nuevoSal = session.exec(
                select(Salon).where(Salon.nombre.like("AULA-%"))
                .where(Salon.id.not_in(ocupados) if ocupados else True)
            ).first()
        if not nuevoSal:
            raise HTTPException(status_code=400, detail="No hay salones disponibles para aperturar un nuevo grupo.")

        nuevoGrup = (ConstructorGrup()
            .conNumero(len(grupos) + 1).conMateria(data.id_materia)
            .conSalon(nuevoSal.id).conProfesor(profesorAs.id)
            .conHorario(grupoEleg.dia, grupoEleg.hora).construir())
        session.add(nuevoGrup)
        session.commit()
        session.refresh(nuevoGrup)

        for estIns in session.exec(
            select(Inscripcion).where(Inscripcion.id_grupo == grupoEleg.id).limit(4)
        ).all():
            estIns.id_grupo = nuevoGrup.id
            session.add(estIns)

        session.add(Inscripcion(id_estudiante=est.id, id_materia=data.id_materia, id_grupo=nuevoGrup.id, estado="Activo"))
        session.commit()
        return {"alerta": False, "mensaje": f"Matrícula exitosa. Se aperturó la sección {nuevoGrup.num_grupo}."}

    session.add(Inscripcion(id_estudiante=est.id, id_materia=data.id_materia, id_grupo=grupoEleg.id, estado="Activo"))
    session.commit()
    return {"alerta": False, "mensaje": f"Matrícula exitosa en el Grupo {grupoEleg.num_grupo}."}