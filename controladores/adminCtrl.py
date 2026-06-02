from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from database import ObtenerSes
from servicios.optimizador import OptimizadorAud, ComponenteAlg
from servicios.sesiones import ObtenerSesAct
from modelos.entidades import (
    SesionToken, Usuario, Rol, Estudiante, Profesor,
    Administrador, Materia, Salon, Grupo, Inscripcion
)

router = APIRouter()


@router.post("/admin/optimizar-horarios", status_code=200)
def OptimizarInf(
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    if sesion.rol != "Administrador":
        raise HTTPException(
            status_code=403,
            detail="Solo los administradores pueden ejecutar la optimizacion de horarios."
        )
    return OptimizadorAud(ComponenteAlg()).ejecutar(session)


@router.get("/admin/bd", status_code=200)
def VerBD(
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    """
    Vista completa de la base de datos para administradores.
    DIP: usa la sesion inyectada, no crea motores propios.
    """
    if sesion.rol != "Administrador":
        raise HTTPException(status_code=403, detail="Solo los administradores pueden ver la base de datos.")

    roles = [{"id": r.id, "nombre": r.nombre_rol} for r in session.exec(select(Rol)).all()]

    usuarios_raw = session.exec(select(Usuario)).all()
    usuarios = []
    for u in usuarios_raw:
        rol_obj = session.get(Rol, u.id_rol)
        nombre_perfil = "—"
        rol_nombre = rol_obj.nombre_rol if rol_obj else "Sin rol"
        if rol_nombre == "Estudiante":
            est = session.exec(select(Estudiante).where(Estudiante.id_usuario == u.id)).first()
            nombre_perfil = est.nombre if est else "—"
        elif rol_nombre == "Profesor":
            prof = session.exec(select(Profesor).where(Profesor.id_usuario == u.id)).first()
            nombre_perfil = prof.nombre if prof else "—"
        elif rol_nombre == "Administrador":
            adm = session.exec(select(Administrador).where(Administrador.id_usuario == u.id)).first()
            nombre_perfil = adm.nombre if adm else "—"
        usuarios.append({
            "id": u.id, "codigo": u.codigo,
            "rol": rol_nombre, "nombre": nombre_perfil
        })

    estudiantes = [
        {"id": e.id, "nombre": e.nombre, "semestre": e.semestre, "id_usuario": e.id_usuario}
        for e in session.exec(select(Estudiante)).all()
    ]

    profesores = [
        {"id": p.id, "nombre": p.nombre, "especialidad": p.especialidad, "id_usuario": p.id_usuario}
        for p in session.exec(select(Profesor)).all()
    ]

    administradores = [
        {"id": a.id, "nombre": a.nombre, "codigo_admin": a.codigo_admin, "id_usuario": a.id_usuario}
        for a in session.exec(select(Administrador)).all()
    ]

    materias = [
        {
            "id": m.id, "nombre": m.nombre, "creditos": m.creditos,
            "facultad": m.facultad, "semestre": m.semestre,
            "id_prerequisito": m.id_prerequisito
        }
        for m in session.exec(select(Materia)).all()
    ]

    salones = [
        {"id": s.id, "nombre": s.nombre, "capacidad": s.capacidad}
        for s in session.exec(select(Salon)).all()
    ]

    grupos_raw = session.exec(select(Grupo)).all()
    grupos = []
    for g in grupos_raw:
        mat  = session.get(Materia,  g.id_materia)
        prof = session.get(Profesor, g.id_profesor)
        sal  = session.get(Salon,    g.id_salon)
        sal2 = session.get(Salon,    g.id_salon2)
        grupos.append({
            "id": g.id, "num_grupo": g.num_grupo,
            "materia": mat.nombre if mat else "—",
            "profesor": prof.nombre if prof else "Sin asignar",
            "sesion_1": f"{g.dia} {g.hora}" if g.dia and g.hora else "—",
            "salon_1": sal.nombre if sal else "—",
            "sesion_2": f"{g.dia2} {g.hora2}" if g.dia2 and g.hora2 else "—",
            "salon_2": sal2.nombre if sal2 else "—",
        })

    inscripciones_raw = session.exec(select(Inscripcion)).all()
    inscripciones = []
    for i in inscripciones_raw:
        est = session.get(Estudiante, i.id_estudiante)
        mat = session.get(Materia,    i.id_materia)
        inscripciones.append({
            "id": i.id,
            "estudiante": est.nombre if est else "—",
            "materia": mat.nombre if mat else "—",
            "id_grupo": i.id_grupo,
            "estado": i.estado,
            "aprobada": i.aprobada
        })

    return {
        "roles":           roles,
        "usuarios":        usuarios,
        "estudiantes":     estudiantes,
        "profesores":      profesores,
        "administradores": administradores,
        "materias":        materias,
        "salones":         salones,
        "grupos":          grupos,
        "inscripciones":   inscripciones,
    }

