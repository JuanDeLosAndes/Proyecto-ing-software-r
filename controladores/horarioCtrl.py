from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, func
from typing import Dict, Any
from database import ObtenerSes
from modelos.entidades import (
    Usuario, Estudiante, Profesor, Inscripcion,
    Grupo, Materia, Salon, SesionToken
)
from servicios.sesiones import ObtenerSesAct

router = APIRouter()

FIN_FRANJA = {
    "07:00": "09:00", "09:00": "11:00", "11:00": "13:00",
    "18:00": "20:00", "20:00": "22:00"
}


def _hora_display(hora: str) -> str:
    return f"{hora} - {FIN_FRANJA.get(hora, hora)}"


def _agregar_celda(horario: dict, hora: str, dia: str, payload: dict):
    """SRP: inserta una celda en el dict de horario usando la hora formateada."""
    if hora and dia:
        clave = _hora_display(hora)
        horario.setdefault(clave, {})[dia] = payload


@router.get("/horarios", status_code=200, response_model=Dict[str, Any])
def ObtenerHor(
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    us = session.exec(select(Usuario).where(Usuario.codigo == sesion.codigo_usuario)).first()
    if not us:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    horario: Dict[str, Any] = {}

    if sesion.rol == "Estudiante":
        est = session.exec(select(Estudiante).where(Estudiante.id_usuario == us.id)).first()
        if est:
            for ins in session.exec(
                select(Inscripcion).where(Inscripcion.id_estudiante == est.id)
            ).all():
                grupo = session.get(Grupo, ins.id_grupo)
                if not grupo:
                    continue
                mat  = session.get(Materia,  grupo.id_materia)
                sal  = session.get(Salon,    grupo.id_salon)
                sal2 = session.get(Salon,    grupo.id_salon2) if grupo.id_salon2 else sal
                prof = session.get(Profesor, grupo.id_profesor)

                nombre_mat  = mat.nombre   if mat  else "N/A"
                nombre_prof = prof.nombre  if prof else "N/A"

                # Sesion 1
                _agregar_celda(horario, grupo.hora, grupo.dia, {
                    "materia":      nombre_mat,
                    "salon":        sal.nombre  if sal  else "Sin salon",
                    "num_grupo":    grupo.num_grupo,
                    "info_extra":   f"Profesor(a): {nombre_prof}",
                    # Datos para tooltip
                    "salon_nombre": sal.nombre  if sal  else "Sin salon",
                    "prof_nombre":  nombre_prof,
                    "sesion":       1
                })
                # Sesion 2
                _agregar_celda(horario, grupo.hora2, grupo.dia2, {
                    "materia":      nombre_mat,
                    "salon":        sal2.nombre if sal2 else "Sin salon",
                    "num_grupo":    grupo.num_grupo,
                    "info_extra":   f"Profesor(a): {nombre_prof}",
                    "salon_nombre": sal2.nombre if sal2 else "Sin salon",
                    "prof_nombre":  nombre_prof,
                    "sesion":       2
                })

    elif sesion.rol == "Profesor":
        prof = session.exec(select(Profesor).where(Profesor.id_usuario == us.id)).first()
        if prof:
            for g in session.exec(
                select(Grupo).where(Grupo.id_profesor == prof.id)
            ).all():
                mat   = session.get(Materia, g.id_materia)
                sal   = session.get(Salon,   g.id_salon)
                sal2  = session.get(Salon,   g.id_salon2) if g.id_salon2 else sal
                inscC = session.exec(
                    select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)
                ).one()

                extra = f"Estudiantes matriculados: {inscC}"
                # Sesion 1
                _agregar_celda(horario, g.hora, g.dia, {
                    "materia":      mat.nombre if mat else "N/A",
                    "salon":        sal.nombre if sal else "Sin salon",
                    "id_grupo":     g.id,
                    "num_grupo":    g.num_grupo,
                    "info_extra":   extra,
                    "salon_nombre": sal.nombre if sal else "Sin salon",
                    "prof_nombre":  prof.nombre,
                    "sesion":       1
                })
                # Sesion 2
                _agregar_celda(horario, g.hora2, g.dia2, {
                    "materia":      mat.nombre  if mat  else "N/A",
                    "salon":        sal2.nombre if sal2 else "Sin salon",
                    "id_grupo":     g.id,
                    "num_grupo":    g.num_grupo,
                    "info_extra":   extra,
                    "salon_nombre": sal2.nombre if sal2 else "Sin salon",
                    "prof_nombre":  prof.nombre,
                    "sesion":       2
                })

    elif sesion.rol == "Administrador":
        raise HTTPException(status_code=403, detail="Los administradores no tienen horario asignado.")

    return horario