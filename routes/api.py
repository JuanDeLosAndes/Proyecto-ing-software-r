from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List, Optional
from database import get_session
from models import (Usuario, Rol, Estudiante, Materia, Salon, 
                    ConfiguracionFront, Administrador, Profesor)

router = APIRouter()

# --- RUTAS ORIGINALES PRESERVADAS Y ADAPTADAS ---

@router.get("/clases", response_model=List[Materia])
def obtener_clases(session: Session = Depends(get_session)):
    """Se adaptó 'Clases' a 'Materias' según el nuevo diagrama."""
    return session.exec(select(Materia)).all()

@router.post("/clases")
def crear_clase(materia: Materia, session: Session = Depends(get_session)):
    session.add(materia)
    session.commit()
    session.refresh(materia)
    return {"mensaje": "Clase/Materia creada", "data": materia}

@router.get("/clases/{id}", response_model=Materia)
def obtener_clase(id: int, session: Session = Depends(get_session)):
    materia = session.get(Materia, id)
    if not materia:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    return materia

@router.get("/buscar", response_model=List[Materia])
def buscar_clases(facultad: Optional[str] = None, session: Session = Depends(get_session)):
    statement = select(Materia)
    if facultad:
        statement = statement.where(Materia.facultad == facultad)
    return session.exec(statement).all()

@router.post("/estudiantes")
def crear_estudiante(codigo: str, contrasena: str, nombre: str, session: Session = Depends(get_session)):
    """Crea el Usuario y el Perfil de Estudiante enlazados."""
    # Buscar si existe el rol estudiante, si no, crearlo
    rol = session.exec(select(Rol).where(Rol.nombre_rol == "Estudiante")).first()
    if not rol:
        rol = Rol(nombre_rol="Estudiante")
        session.add(rol)
        session.commit()

    existe = session.exec(select(Usuario).where(Usuario.codigo == codigo)).first()
    if existe:
        raise HTTPException(status_code=400, detail="El código de usuario ya existe")

    nuevo_usuario = Usuario(codigo=codigo, contrasena=contrasena, id_rol=rol.id)
    session.add(nuevo_usuario)
    session.commit()

    nuevo_estudiante = Estudiante(nombre=nombre, id_usuario=nuevo_usuario.id)
    session.add(nuevo_estudiante)
    session.commit()

    return {"mensaje": "Estudiante creado exitosamente"}

@router.post("/login")
def login(codigo: str, contrasena: str, session: Session = Depends(get_session)):
    statement = select(Usuario).where(Usuario.codigo == codigo, Usuario.contrasena == contrasena)
    usuario = session.exec(statement).first()
    
    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    rol = session.get(Rol, usuario.id_rol)
    return {"mensaje": "Login correcto", "codigo": usuario.codigo, "rol": rol.nombre_rol if rol else "Sin Rol"}

# --- NUEVAS RUTAS CON PERMISOS DE ROLES ---

@router.put("/salones/{id_salon}")
def modificar_salon(id_salon: int, nueva_capacidad: int, id_usuario_peticion: int, session: Session = Depends(get_session)):
    """Solo un Profesor puede modificar la capacidad de un salón."""
    usuario = session.get(Usuario, id_usuario_peticion)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    rol = session.get(Rol, usuario.id_rol)
    if not rol or rol.nombre_rol != "Profesor":
        raise HTTPException(status_code=403, detail="Permiso denegado. Solo profesores pueden modificar salones.")

    salon = session.get(Salon, id_salon)
    if not salon:
        raise HTTPException(status_code=404, detail="Salón no encontrado")

    salon.capacidad = nueva_capacidad
    session.add(salon)
    session.commit()
    return {"mensaje": "Salón modificado exitosamente", "salon": salon}

@router.put("/front/mensajes")
def modificar_mensaje_front(nuevo_mensaje: str, id_usuario_peticion: int, session: Session = Depends(get_session)):
    """Solo un Administrador puede modificar los mensajes del front."""
    usuario = session.get(Usuario, id_usuario_peticion)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    rol = session.get(Rol, usuario.id_rol)
    if not rol or rol.nombre_rol != "Administrador":
        raise HTTPException(status_code=403, detail="Permiso denegado. Solo administradores pueden modificar el front.")

    config = session.exec(select(ConfiguracionFront)).first()
    if not config:
        config = ConfiguracionFront(mensaje_bienvenida=nuevo_mensaje)
    else:
        config.mensaje_bienvenida = nuevo_mensaje

    session.add(config)
    session.commit()
    return {"mensaje": "Mensaje del front actualizado", "nuevo_mensaje": config.mensaje_bienvenida}