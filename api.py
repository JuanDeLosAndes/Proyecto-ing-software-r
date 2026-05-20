from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, func
from typing import List, Optional, Dict, Any
from database import get_session
from models import Usuario, Rol, Estudiante, Profesor, Materia, Salon, Grupo, Inscripcion, ConfiguracionFront

# Importaciones de nuestra capa de arquitectura de software desacoplada (services.py)
from services import (
    CreadorUsuario, 
    GestorEventosUniversidad, 
    IAOptimizationTriggerObserver, 
    EmailNotificationObserver,
    ContextoInscripcion, 
    EstrategiaGrupoMasVacio
)

router = APIRouter()

# --- CONFIGURACIÓN GLOBAL DEL FRONTEND (ADMINISTRADOR) ---

@router.get("/front/config", response_model=ConfiguracionFront)
def obtener_configuracion_global(session: Session = Depends(get_session)):
    config = session.exec(select(ConfiguracionFront)).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    return config

@router.post("/front/config")
def guardar_configuracion_global(mensaje_sup: str, mensaje_inf: str, url_img: str, codigo_admin: str, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == codigo_admin)).first()
    if not user or session.get(Rol, user.id_rol).nombre_rol != "Administrador":
        raise HTTPException(status_code=403, detail="Operación exclusiva del Administrador")
    
    config = session.exec(select(ConfiguracionFront)).first()
    if not config:
        config = ConfiguracionFront(mensaje_superior=mensaje_sup, mensaje_inferior=mensaje_inf, url_imagen=url_img)
    else:
        config.mensaje_superior = mensaje_sup
        config.mensaje_inferior = mensaje_inf
        config.url_imagen = url_img
    session.add(config)
    session.commit()
    return {"mensaje": "Configuración guardada de manera persistente"}


# --- AUTENTICACIÓN ---

@router.post("/login")
def login(codigo: str, contrasena: str, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == codigo, Usuario.contrasena == contrasena)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    rol = session.get(Rol, user.id_rol)
    return {"codigo": user.codigo, "rol": rol.nombre_rol if rol else "Sin Rol"}


# --- PATRÓN 1 (CREACIONAL): REGISTRO DE USUARIOS POR FACTORY METHOD ---

@router.post("/usuarios/registrar")
def registrar_usuario(rol_nombre: str, codigo: str, contrasena: str, nombre: str, especialidad: Optional[str] = None, session: Session = Depends(get_session)):
    try:
        credenciales = {"codigo": codigo, "contrasena": contrasena}
        perfil_datos = {"nombre": nombre, "especialidad": especialidad}
        
        # Consumimos la fábrica polimórfica encapsulada en servicios
        nuevo_user = CreadorUsuario.registrar_nuevo_usuario(session, rol_nombre, credenciales, perfil_datos)
        return {"mensaje": f"Perfil [{rol_nombre}] creado exitosamente vía Factory Method con ID: {nuevo_user.id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- HORARIOS DINÁMICOS POR ROL ---

@router.get("/horarios/{codigo}", response_model=Dict[str, Any])
def obtener_horario_real(codigo: str, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == codigo)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
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
                    if grupo.hora not in horario_formateado:
                        horario_formateado[grupo.hora] = {}
                    horario_formateado[grupo.hora][grupo.dia] = {"materia": materia.nombre, "salon": salon.nombre}

    elif rol == "Profesor":
        profesor = session.exec(select(Profesor).where(Profesor.id_usuario == user.id)).first()
        if profesor:
            grupos = session.exec(select(Grupo).where(Grupo.id_profesor == profesor.id)).all()
            for g in list(grupos):
                if g.hora and g.dia:
                    materia = session.get(Materia, g.id_materia)
                    salon = session.get(Salon, g.id_salon)
                    if g.hora not in horario_formateado:
                        horario_formateado[g.hora] = {}
                    horario_formateado[g.hora][g.dia] = {"materia": materia.nombre, "salon": salon.nombre, "id_grupo": g.id}

    return horario_formateado


# --- PATRÓN 5 (COMPORTAMIENTO): MATRÍCULA BALANCEADA POR PATRÓN STRATEGY ---

@router.post("/inscribir")
def inscribir_estudiante(codigo_usuario: str, id_materia: int, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == codigo_usuario)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    estudiante = session.exec(select(Estudiante).where(Estudiante.id_usuario == user.id)).first()
    materia = session.get(Materia, id_materia)
    if not materia:
        raise HTTPException(status_code=404, detail="Materia no encontrada")

    # 1. Identificamos qué tipo de profesor necesita la materia
    especialidad_requerida = "Ingeniería de Sistemas" if materia.facultad == "Sistemas" else "Ciencias Básicas"
    
    # 2. Buscamos si existe ALGÚN profesor disponible con esa especialidad
    profesor_asignado = session.exec(select(Profesor).where(Profesor.especialidad == especialidad_requerida)).first()
    
    # 3. NUEVA VALIDACIÓN: Si no hay profesor, detenemos todo y mandamos el mensaje
    if not profesor_asignado:
        return {
            "alerta": True,
            "mensaje": f"Lo sentimos, en este momento no hay profesores disponibles con la especialidad de '{especialidad_requerida}' para abrir la materia de {materia.nombre}."
        }

    grupos = session.exec(select(Grupo).where(Grupo.id_materia == id_materia)).all()
    
    if not grupos:
        salon = session.exec(select(Salon).where(Salon.nombre.like("Sala de Cómputo%" if materia.facultad == "Sistemas" else "AULA-%"))).first()
        grupo_elegido = Grupo(num_grupo=1, cupo_maximo=35, id_materia=id_materia, id_salon=salon.id, id_profesor=profesor_asignado.id, dia="Lunes", hora="7:00")
        session.add(grupo_elegido)
        session.commit()
        session.refresh(grupo_elegido)
        inscritos = 0
    else:
        # =====================================================================
        # ASIGNACIÓN DE GRUPOS MEDIANTE EL PATRÓN STRATEGY
        # =====================================================================
        contexto_balanceo = ContextoInscripcion(EstrategiaGrupoMasVacio())
        grupo_elegido = contexto_balanceo.seleccionar(list(grupos), session)
        inscritos = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == grupo_elegido.id)).one()
    
    # Algoritmo de división automática por aforo límite de 35 alumnos
    if inscritos + 1 > 35:
        salon = session.exec(select(Salon).where(Salon.nombre.like("Sala de Cómputo%" if materia.facultad == "Sistemas" else "AULA-%"))).first()
        nuevo_grupo = Grupo(num_grupo=len(grupos)+1, cupo_maximo=35, id_materia=id_materia, id_salon=salon.id, id_profesor=profesor_asignado.id, dia="Viernes", hora="11:00")
        session.add(nuevo_grupo)
        session.commit()
        session.refresh(nuevo_grupo)
        
        alumnos_mover = session.exec(select(Inscripcion).where(Inscripcion.id_grupo == grupo_elegido.id).limit(5)).all()
        for a in list(alumnos_mover):
            a.id_grupo = nuevo_grupo.id
            session.add(a)
            
        insc = Inscripcion(id_estudiante=estudiante.id, id_materia=id_materia, id_grupo=nuevo_grupo.id, estado="Activo")
    else:
        insc = Inscripcion(id_estudiante=estudiante.id, id_materia=id_materia, id_grupo=grupo_elegido.id, estado="Activo")
        
    session.add(insc)
    session.commit()
    
    return {"alerta": False, "mensaje": f"Matrícula procesada. Profesor asignado: {profesor_asignado.nombre}."}


# --- PATRÓN 4 (DE COMPORTAMIENTO): ORQUESTACIÓN MEDIANTE EL PATRÓN OBSERVER ---

@router.put("/profesor/cambiar-salon")
def profesor_cambiar_salon(codigo_profesor: str, id_grupo: int, id_nuevo_salon: int, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == codigo_profesor)).first()
    profesor = session.exec(select(Profesor).where(Profesor.id_usuario == user.id)).first()
    
    grupo = session.get(Grupo, id_grupo)
    if not grupo or grupo.id_profesor != profesor.id:
        raise HTTPException(status_code=403, detail="Acceso denegado. Este grupo no pertenece a su carga docente académica.")
        
    materia = session.get(Materia, grupo.id_materia)
    nuevo_salon = session.get(Salon, id_nuevo_salon)
    
    if materia.facultad == "Sistemas" and "Sala" not in nuevo_salon.nombre:
        raise HTTPException(status_code=400, detail="Incompatibilidad técnica: Sistemas exige Sala de Cómputo.")
    if materia.facultad == "Ciencias Básicas" and "AULA" not in nuevo_salon.nombre:
        raise HTTPException(status_code=400, detail="Incompatibilidad técnica: Matemáticas no se dicta en laboratorios.")
        
    inscritos = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == id_grupo)).one()
    if inscritos > nuevo_salon.capacidad:
        raise HTTPException(status_code=400, detail=f"Aforo excedido: El salón aloja {nuevo_salon.capacidad} estudiantes y el grupo tiene {inscritos}.")
        
    # Guardamos de forma inmediata la actualización manual solicitada por el docente
    grupo.id_salon = nuevo_salon.id
    session.add(grupo)
    session.commit()

    # =====================================================================
    # ARQUITECTURA BASADA EN EVENTOS: EJECUCIÓN CON OBSERVER
    # =====================================================================
    publicador = GestorEventosUniversidad()
    publicador.suscribir(IAOptimizationTriggerObserver()) # Gatilla IA y Logs
    publicador.suscribir(EmailNotificationObserver())       # Gatilla Adapter de Email
    publicador.notificar_todos("CAMBIO_SALON", {"grupo_id": id_grupo, "session": session})
    # =====================================================================

    return {"mensaje": "Salón reasignado. El evento disparó la IA (Decorada) y Notificaciones (Adaptadas) automáticamente."}