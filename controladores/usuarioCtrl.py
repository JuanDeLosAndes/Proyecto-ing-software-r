from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from database import ObtenerSes
from modelos.entidades import Usuario, Rol
from modelos.esquemas import EsquemaLogin, EsquemaRegistro
from servicios.fabricas import CreadorUs
from servicios.sesiones import GestorSesion

router = APIRouter()


@router.post("/login", status_code=200)
def IniciarSes(data: EsquemaLogin, session: Session = Depends(ObtenerSes)):
    us = session.exec(
        select(Usuario).where(
            Usuario.codigo == data.codigo,
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


@router.post("/usuarios/registrar", status_code=201)
def RegistrarUs(data: EsquemaRegistro, session: Session = Depends(ObtenerSes)):
    # ── Validaciones de formato de codigo por rol ──
    if data.rol_nombre == "Estudiante":
        if len(data.codigo) != 8 or not data.codigo.startswith("6700"):
            raise HTTPException(
                status_code=400,
                detail="Codigo de Estudiante invalido: debe tener 8 digitos y comenzar con 6700."
            )
        # SRP: semestre obligatorio para estudiantes
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
        # Especialidad obligatoria para profesores
        if not data.especialidad or data.especialidad.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="La especialidad es obligatoria para Profesores: 'Ingenieria de Sistemas' o 'Ciencias Basicas'."
            )

    # ── Verificar codigo unico ──
    existente = session.exec(select(Usuario).where(Usuario.codigo == data.codigo)).first()
    if existente:
        raise HTTPException(
            status_code=409,
            detail=f"El codigo {data.codigo} ya esta registrado en el sistema."
        )

    try:
        creds = {"codigo": data.codigo, "contrasena": data.contrasena}
        perfilDatos = {
            "nombre":      data.nombre,
            "especialidad": data.especialidad,
            "semestre":    data.semestre or 1
        }
        nuevoUs = CreadorUs.RegistrarUs(session, data.rol_nombre, creds, perfilDatos)
        return {"mensaje": f"Usuario [{data.rol_nombre}] registrado exitosamente.", "id": nuevoUs.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))