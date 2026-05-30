from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, func
from typing import Dict, Any
from database import ObtenerSes
from modelos.entidades import Usuario, Estudiante, Profesor, Inscripcion, Grupo, Materia, Salon, SesionToken
from servicios.sesiones import ObtenerSesAct

router = APIRouter()


@router.get("/horarios", status_code=200, response_model=Dict[str, Any])
def ObtenerHor(
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    us = session.exec(select(Usuario).where(Usuario.codigo == sesion.codigo_usuario)).first()
    if not us:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    horario = {}

    if sesion.rol == "Estudiante":
        est = session.exec(select(Estudiante).where(Estudiante.id_usuario == us.id)).first()
        if est:
            for ins in session.exec(select(Inscripcion).where(Inscripcion.id_estudiante == est.id)).all():
                grupo = session.get(Grupo, ins.id_grupo)
                if grupo and grupo.hora and grupo.dia:
                    mat  = session.get(Materia,  grupo.id_materia)
                    sal  = session.get(Salon,    grupo.id_salon)
                    prof = session.get(Profesor, grupo.id_profesor)
                    horario.setdefault(grupo.hora, {})[grupo.dia] = {
                        "materia":    mat.nombre  if mat  else "N/A",
                        "salon":      sal.nombre  if sal  else "N/A",
                        "num_grupo":  grupo.num_grupo,
                        "info_extra": f"Profesor(a): {prof.nombre}" if prof else "Profesor: N/A"
                    }

    elif sesion.rol == "Profesor":
        prof = session.exec(select(Profesor).where(Profesor.id_usuario == us.id)).first()
        if prof:
            for g in session.exec(select(Grupo).where(Grupo.id_profesor == prof.id)).all():
                if g.hora and g.dia:
                    mat   = session.get(Materia, g.id_materia)
                    sal   = session.get(Salon,   g.id_salon)
                    inscC = session.exec(
                        select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)
                    ).one()
                    horario.setdefault(g.hora, {})[g.dia] = {
                        "materia":    mat.nombre if mat else "N/A",
                        "salon":      sal.nombre if sal else "N/A",
                        "id_grupo":   g.id,
                        "num_grupo":  g.num_grupo,
                        "info_extra": f"Estudiantes matriculados: {inscC}"
                    }

    elif sesion.rol == "Administrador":
        raise HTTPException(status_code=403, detail="Los administradores no tienen horario asignado.")

    return horario