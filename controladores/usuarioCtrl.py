from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from database import ObtenerSes
from modelos.entidades import (
    Usuario, Rol, Estudiante, Profesor, Administrador, SesionToken
)
from modelos.esquemas import EsquemaLogin, EsquemaRegistro, EsquemaCambioContrasena
from servicios.fabricas import CreadorUs
from servicios.sesiones import GestorSesion, ObtenerSesAct

router = APIRouter()

ESPECIALIDADES_VALIDAS = {"Ingeniería de Sistemas", "Ciencias Básicas"}
ESPECIALIDAD_A_FACULTAD = {
    "Ingeniería de Sistemas": "Sistemas",
    "Ciencias Básicas":       "Ciencias Básicas",
}


def _asignar_profe_pendiente(session: Session, facultad: str) -> None:

    from modelos.entidades import Grupo, Materia
    especialidad_map = {
        "Sistemas":         "Ingeniería de Sistemas",
        "Ciencias Básicas": "Ciencias Básicas",
    }
    especialidad = especialidad_map.get(facultad)
    if not especialidad:
        return
    prof = session.exec(
        select(Profesor).where(Profesor.especialidad == especialidad)
    ).first()
    if not prof:
        return
    grupos_sin_prof = session.exec(
        select(Grupo)
        .join(Materia, Grupo.id_materia == Materia.id)
        .where(Grupo.id_profesor == None, Materia.facultad == facultad)
    ).all()
    for g in grupos_sin_prof:
        g.id_profesor = prof.id
        session.add(g)
    if grupos_sin_prof:
        session.commit()


@router.post("/login", status_code=200)
def IniciarSes(data: EsquemaLogin, session: Session = Depends(ObtenerSes)):
    us = session.exec(
        select(Usuario).where(
            Usuario.codigo     == data.codigo,
            Usuario.contrasena == data.contrasena
        )
    ).first()
    if not us:
        raise HTTPException(
            status_code=401,
            detail="Codigo o contrasena incorrectos. Verifique sus credenciales."
        )
    rol = session.get(Rol, us.id_rol)
    rolNombre = rol.nombre_rol if rol else "Sin Rol"
    token = GestorSesion.CrearSesion(session, us.id, us.codigo, rolNombre)
    return {"token": token, "rol": rolNombre}


@router.post("/logout", status_code=200)
def CerrarSes(token: str, session: Session = Depends(ObtenerSes)):
    GestorSesion.CerrarSesion(session, token)
    return {"mensaje": "Sesion cerrada correctamente."}


@router.post("/usuarios/cambiar-contraseña", status_code=200)
def CambiarContrasena(
    data: EsquemaCambioContrasena,
    session: Session = Depends(ObtenerSes)
):
    us = session.exec(select(Usuario).where(Usuario.codigo == data.codigo)).first()
    if not us:
        raise HTTPException(
            status_code=404,
            detail="No existe un usuario con ese codigo institucional."
        )
    if us.contrasena == data.nueva_contrasena:
        raise HTTPException(
            status_code=400,
            detail="La nueva contrasena no puede ser igual a la contrasena actual."
        )
    us.contrasena = data.nueva_contrasena
    session.add(us)
    session.commit()
    return {"mensaje": "Contraseña actualizada correctamente. Ya puede iniciar sesion."}


@router.post("/usuarios/registrar", status_code=201)
def RegistrarUs(data: EsquemaRegistro, session: Session = Depends(ObtenerSes)):
    if data.rol_nombre == "Estudiante":
        if len(data.codigo) != 8 or not data.codigo.startswith("6700"):
            raise HTTPException(
                status_code=400,
                detail="Codigo de Estudiante invalido: debe tener 8 digitos y comenzar con 6700."
            )
        if data.semestre is None:
            raise HTTPException(
                status_code=400,
                detail="El semestre es obligatorio para registrar un Estudiante (1 a 10)."
            )
    elif data.rol_nombre == "Administrador":
        if len(data.codigo) != 8 or not data.codigo.startswith("9900"):
            raise HTTPException(
                status_code=400,
                detail="Codigo de Administrador invalido: debe tener 8 digitos y comenzar con 9900."
            )
    elif data.rol_nombre == "Profesor":
        if len(data.codigo) != 10 or data.codigo.startswith("6700") or data.codigo.startswith("9900"):
            raise HTTPException(
                status_code=400,
                detail="Codigo de Profesor invalido: debe tener 10 digitos y no comenzar con 6700 ni 9900."
            )
        if not data.especialidad or data.especialidad.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="La especialidad es obligatoria para Profesores: 'Ingeniería de Sistemas' o 'Ciencias Básicas'."
            )
        if data.especialidad.strip() not in ESPECIALIDADES_VALIDAS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Especialidad '{data.especialidad}' no valida. "
                    "Use exactamente 'Ingeniería de Sistemas' o 'Ciencias Básicas'."
                )
            )

    if session.exec(select(Usuario).where(Usuario.codigo == data.codigo)).first():
        raise HTTPException(
            status_code=409,
            detail=f"El codigo {data.codigo} ya esta registrado en el sistema."
        )

    try:
        creds = {"codigo": data.codigo, "contrasena": data.contrasena}
        perfilDatos = {
            "nombre":       data.nombre,
            "especialidad": data.especialidad.strip() if data.especialidad else None,
            "semestre":     data.semestre or 1,
        }
        nuevoUs = CreadorUs.RegistrarUs(session, data.rol_nombre, creds, perfilDatos)


        if data.rol_nombre == "Profesor":
            facultad = ESPECIALIDAD_A_FACULTAD.get(
                data.especialidad.strip() if data.especialidad else ""
            )
            if facultad:
                _asignar_profe_pendiente(session, facultad)

        return {"mensaje": f"Usuario [{data.rol_nombre}] registrado exitosamente.", "id": nuevoUs.id}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/admin/usuarios/agregar", status_code=201)
def AgregarUsuarioAdmin(
    data: EsquemaRegistro,
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):

    if sesion.rol != "Administrador":
        raise HTTPException(status_code=403, detail="Solo los administradores pueden agregar usuarios.")
    return RegistrarUs(data, session)