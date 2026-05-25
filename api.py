from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, func
from typing import List, Optional, Dict, Any
from database import get_session
from models import Usuario, Rol, Estudiante, Profesor, Materia, Salon, Grupo, Inscripcion, ConfiguracionFront
from pydantic import BaseModel

from services import (
    CreadorUsuario, GestorEventosUniversidad, IAOptimizationTriggerObserver, 
    ObservadorConsola, ContextoInscripcion, EstrategiaGrupoMasVacio
)

router = APIRouter()

# Schemas de Validacion para Pydantic y Swagger
class UsuarioRegistro(BaseModel):
    rol_nombre: str
    codigo: str
    contrasena: str
    nombre: str
    especialidad: Optional[str] = None

class ConfiguracionUpdate(BaseModel):
    codigo_admin: str
    mensaje_sup: Optional[str] = None
    mensaje_inf: Optional[str] = None
    url_img: Optional[str] = None

class MatricularReq(BaseModel):
    codigo_usuario: str
    id_materia: int

@router.get("/front/config", response_model=ConfiguracionFront)
def obtener_configuracion_global(session: Session = Depends(get_session)):
    config = session.exec(select(ConfiguracionFront)).first()
    if not config: raise HTTPException(status_code=404, detail="Configuracion no encontrada")
    return config

@router.post("/front/config")
def guardar_configuracion_global(data: ConfiguracionUpdate, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == data.codigo_admin)).first()
    if not user or session.get(Rol, user.id_rol).nombre_rol != "Administrador":
        raise HTTPException(status_code=403, detail="Operacion exclusiva del Administrador")
    
    config = session.exec(select(ConfiguracionFront)).first()
    if not config:
        config = ConfiguracionFront(mensaje_superior=data.mensaje_sup or "", mensaje_inferior=data.mensaje_inf or "", url_imagen=data.url_img or "")
    else:
        if data.mensaje_sup: config.mensaje_superior = data.mensaje_sup
        if data.mensaje_inf: config.mensaje_inferior = data.mensaje_inf
        if data.url_img: config.url_imagen = data.url_img
        
    session.add(config)
    session.commit()
    return {"mensaje": "Configuracion actualizada correctamente"}

@router.post("/login")
def login(codigo: str, contrasena: str, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == codigo, Usuario.contrasena == contrasena)).first()
    if not user: raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    rol = session.get(Rol, user.id_rol)
    return {"codigo": user.codigo, "rol": rol.nombre_rol if rol else "Sin Rol"}

@router.post("/usuarios/registrar")
def registrar_usuario(data: UsuarioRegistro, session: Session = Depends(get_session)):
    try:
        credenciales = {"codigo": data.codigo, "contrasena": data.contrasena}
        perfil_datos = {"nombre": data.nombre, "especialidad": data.especialidad}
        nuevo_user = CreadorUsuario.registrar_nuevo_usuario(session, data.rol_nombre, credenciales, perfil_datos)
        return {"mensaje": f"Usuario [{data.rol_nombre}] creado con exito. ID: {nuevo_user.id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/horarios/{codigo}", response_model=Dict[str, Any])
def obtener_horario_real(codigo: str, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == codigo)).first()
    if not user: raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    rol = session.get(Rol, user.id_rol).nombre_rol
    horario_formateado = {}

    if rol == "Estudiante":
        estudiante = session.exec(select(Estudiante).where(Estudiante.id_usuario == user.id)).first()
        if estudiante:
            inscripciones = session.exec(select(Inscripcion).where(Inscripcion.id_estudiante == estudiante.id)).all()
            for insc in list(inscripciones):
                grupo = session.get(Grupo, insc.id_grupo)
                if grupo and grupo.hora and grupo.dia:
                    materia = session.get(Materia, grupo.id_materia)
                    salon = session.get(Salon, grupo.id_salon)
                    if grupo.hora not in horario_formateado: horario_formateado[grupo.hora] = {}
                    horario_formateado[grupo.hora][grupo.dia] = {"materia": materia.nombre, "salon": salon.nombre}

    elif rol == "Profesor":
        profesor = session.exec(select(Profesor).where(Profesor.id_usuario == user.id)).first()
        if profesor:
            grupos = session.exec(select(Grupo).where(Grupo.id_profesor == profesor.id)).all()
            for g in list(grupos):
                if g.hora and g.dia:
                    materia = session.get(Materia, g.id_materia)
                    salon = session.get(Salon, g.id_salon)
                    if g.hora not in horario_formateado: horario_formateado[g.hora] = {}
                    horario_formateado[g.hora][g.dia] = {"materia": materia.nombre, "salon": salon.nombre, "id_grupo": g.id}

    return horario_formateado

@router.post("/inscribir")
def inscribir_estudiante(data: MatricularReq, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == data.codigo_usuario)).first()
    estudiante = session.exec(select(Estudiante).where(Estudiante.id_usuario == user.id)).first()
    materia = session.get(Materia, data.id_materia)
    
    especialidad_req = "Ingeniería de Sistemas" if materia.facultad == "Sistemas" else "Ciencias Básicas"
    profesor_asignado = session.exec(select(Profesor).where(Profesor.especialidad == especialidad_req)).first()
    if not profesor_asignado: return {"alerta": True, "mensaje": "No hay profesores con la especialidad requerida."}

    grupos = session.exec(select(Grupo).where(Grupo.id_materia == data.id_materia)).all()
    
    limite_cupo = 30 if materia.facultad == "Sistemas" else 35
    
    if not grupos:
        salon = session.exec(select(Salon).where(Salon.nombre.like("Sala de Computo%" if materia.facultad == "Sistemas" else "AULA-%"))).first()
        grupo_elegido = Grupo(num_grupo=1, id_materia=data.id_materia, id_salon=salon.id, id_profesor=profesor_asignado.id, dia="Lunes", hora="7:00")
        session.add(grupo_elegido)
        session.commit(); session.refresh(grupo_elegido)
        inscritos = 0
    else:
        contexto = ContextoInscripcion(EstrategiaGrupoMasVacio())
        grupo_elegido = contexto.seleccionar(list(grupos), session)
        inscritos = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == grupo_elegido.id)).one()

    if inscritos + 1 > limite_cupo:
        prefix_salon = "Sala de Computo%" if materia.facultad == "Sistemas" else "AULA-%"
        
        # Consultamos que salones de la universidad estan ocupados en ese dia y hora especifica
        salones_ocupados = session.exec(
            select(Grupo.id_salon).where(Grupo.dia == grupo_elegido.dia, Grupo.hora == grupo_elegido.hora)
        ).all()
        
        # Buscamos un nuevo salon del mismo tipo, que no sea el actual y que este desocupado en ese horario
        nuevo_salon = session.exec(
            select(Salon)
            .where(Salon.nombre.like(prefix_salon))
            .where(Salon.id != grupo_elegido.id_salon)
            .where(Salon.id.not_in(salones_ocupados) if salones_ocupados else True)
        ).first()
        
        if not nuevo_salon:
            nuevo_salon = session.exec(
                select(Salon)
                .where(Salon.nombre.like(prefix_salon))
                .where(Salon.id != grupo_elegido.id_salon)
            ).first()
            
        nuevo_grupo = Grupo(
            num_grupo=len(grupos) + 1,
            id_materia=data.id_materia,
            id_salon=nuevo_salon.id if nuevo_salon else grupo_elegido.id_salon,
            id_profesor=profesor_asignado.id,
            dia=grupo_elegido.dia,  # Mismo dia
            hora=grupo_elegido.hora # Misma hora exacta
        )
        session.add(nuevo_grupo)
        session.commit(); session.refresh(nuevo_grupo)
        
        insc = Inscripcion(id_estudiante=estudiante.id, id_materia=data.id_materia, id_grupo=nuevo_grupo.id, estado="Activo")
    else:
        insc = Inscripcion(id_estudiante=estudiante.id, id_materia=data.id_materia, id_grupo=grupo_elegido.id, estado="Activo")
        
    session.add(insc)
    session.commit()
    return {"alerta": False, "mensaje": "Matricula exitosa en seccion distribuida."}

@router.put("/profesor/cambiar-salon")
def profesor_cambiar_salon(codigo_profesor: str, id_grupo: int, id_nuevo_salon: int, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == codigo_profesor)).first()
    profesor = session.exec(select(Profesor).where(Profesor.id_usuario == user.id)).first()
    
    grupo = session.get(Grupo, id_grupo)
    materia = session.get(Materia, grupo.id_materia)
    nuevo_salon = session.get(Salon, id_nuevo_salon)
    
    if profesor.especialidad == "Ciencias Básicas" and "Sala" in nuevo_salon.nombre:
        raise HTTPException(status_code=400, detail="Los profesores de ciencias basicas no pueden usar salas de computo.")

    if materia.facultad == "Sistemas" and "Sala" not in nuevo_salon.nombre:
        raise HTTPException(status_code=400, detail="Incompatibilidad tecnica: Sistemas exige Sala de Computo.")
    if materia.facultad == "Ciencias Básicas" and "AULA" not in nuevo_salon.nombre:
        raise HTTPException(status_code=400, detail="Incompatibilidad tecnica: Matematicas no se dicta en laboratorios.")
        
    inscritos = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == id_grupo)).one()
    if list(grupos) and inscritos > nuevo_salon.capacidad:
        raise HTTPException(status_code=400, detail=f"Aforo excedido: Capacidad de {nuevo_salon.capacidad} para {inscritos} alumnos.")
        
    grupo.id_salon = nuevo_salon.id
    session.add(grupo)
    session.commit()

    publicador = GestorEventosUniversidad()
    publicador.suscribir(IAOptimizationTriggerObserver()) 
    publicador.suscribir(ObservadorConsola())             
    
    publicador.notificar_todos("CAMBIO_SALON", {"grupo_id": id_grupo, "nuevo_salon_id": id_nuevo_salon, "session": session})
    return {"mensaje": "El evento disparo la IA y genero la alerta en la consola."}

@router.post("/admin/optimizar-horarios")
def optimizar_infraestructura(codigo_admin: str, session: Session = Depends(get_session)):
    from services import OptimizadorAuditoria, ComponenteAlgoritmoGenetico
    motor = OptimizadorAuditoria(ComponenteAlgoritmoGenetico())
    return motor.ejecutar(session)