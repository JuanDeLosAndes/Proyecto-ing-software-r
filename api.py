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

class UsuarioRegistro(BaseModel):
    rol_nombre: str
    codigo: str
    contrasena: str
    nombre: str
    especialidad: Optional[str] = None

class ConfiguracionUpdate(BaseModel):
    codigo_admin: str
    msg_1: Optional[str] = None
    msg_2: Optional[str] = None
    msg_3: Optional[str] = None
    msg_4: Optional[str] = None
    img_1: Optional[str] = None
    img_2: Optional[str] = None
    img_3: Optional[str] = None

class MatricularReq(BaseModel):
    codigo_usuario: str
    id_materia: int
    id_grupo: Optional[int] = None

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
        config = ConfiguracionFront(
            mensaje_1=data.msg_1 or "", mensaje_2=data.msg_2 or "", 
            mensaje_3=data.msg_3 or "", mensaje_4=data.msg_4 or "", 
            url_img_1=data.img_1 or "", url_img_2=data.img_2 or "", url_img_3=data.img_3 or ""
        )
    else:
        if data.msg_1 is not None: config.mensaje_1 = data.msg_1
        if data.msg_2 is not None: config.mensaje_2 = data.msg_2
        if data.msg_3 is not None: config.mensaje_3 = data.msg_3
        if data.msg_4 is not None: config.mensaje_4 = data.msg_4
        if data.img_1 is not None: config.url_img_1 = data.img_1
        if data.img_2 is not None: config.url_img_2 = data.img_2
        if data.img_3 is not None: config.url_img_3 = data.img_3
        
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
    # Validaciones de Seguridad de Código Institucional
    if not data.codigo.isdigit():
        raise HTTPException(status_code=400, detail="El código debe contener unicamente números.")
        
    if data.rol_nombre == "Estudiante":
        if len(data.codigo) != 8 or not data.codigo.startswith("6700"):
            raise HTTPException(status_code=400, detail="El código de Estudiante debe tener 8 digitos y empezar por 6700.")
    elif data.rol_nombre == "Administrador":
        if len(data.codigo) != 8 or not data.codigo.startswith("9900"):
            raise HTTPException(status_code=400, detail="El código de Administrador debe tener 8 digitos y empezar por 9900.")
    elif data.rol_nombre == "Profesor":
        if len(data.codigo) != 10 or data.codigo.startswith("6700") or data.codigo.startswith("9900"):
            raise HTTPException(status_code=400, detail="El código de Profesor debe tener 10 digitos y NO puede empezar por 6700 ni 9900.")

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
                    profesor = session.get(Profesor, grupo.id_profesor)
                    
                    if grupo.hora not in horario_formateado: horario_formateado[grupo.hora] = {}
                    
                    horario_formateado[grupo.hora][grupo.dia] = {
                        "materia": materia.nombre, 
                        "salon": salon.nombre,
                        "num_grupo": grupo.num_grupo,
                        "info_extra": f"Profesor(a): {profesor.nombre}" if profesor else "Profesor: N/A"
                    }

    elif rol == "Profesor":
        profesor = session.exec(select(Profesor).where(Profesor.id_usuario == user.id)).first()
        if profesor:
            grupos = session.exec(select(Grupo).where(Grupo.id_profesor == profesor.id)).all()
            for g in list(grupos):
                if g.hora and g.dia:
                    materia = session.get(Materia, g.id_materia)
                    salon = session.get(Salon, g.id_salon)
                    inscritos_count = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)).one()
                    
                    if g.hora not in horario_formateado: horario_formateado[g.hora] = {}
                    
                    horario_formateado[g.hora][g.dia] = {
                        "materia": materia.nombre, 
                        "salon": salon.nombre, 
                        "id_grupo": g.id,
                        "num_grupo": g.num_grupo,
                        "info_extra": f"Estudiantes Matriculados: {inscritos_count}"
                    }

    return horario_formateado

@router.get("/materias/{id_materia}/grupos")
def obtener_grupos_materia(id_materia: int, session: Session = Depends(get_session)):
    grupos = session.exec(select(Grupo).where(Grupo.id_materia == id_materia)).all()
    materia = session.get(Materia, id_materia)
    limite = 30 if materia and materia.facultad == "Sistemas" else 35
    
    resultado = []
    for g in grupos:
        inscritos = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)).one()
        resultado.append({
            "id_grupo": g.id,
            "num_grupo": g.num_grupo,
            "dia": g.dia,
            "hora": g.hora,
            "inscritos": inscritos,
            "limite": limite
        })
    return resultado

@router.post("/inscribir")
def inscribir_estudiante(data: MatricularReq, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == data.codigo_usuario)).first()
    estudiante = session.exec(select(Estudiante).where(Estudiante.id_usuario == user.id)).first()
    materia = session.get(Materia, data.id_materia)
    
    inscripcion_previa = session.exec(select(Inscripcion).where(Inscripcion.id_estudiante == estudiante.id, Inscripcion.id_materia == data.id_materia)).first()
    if inscripcion_previa:
        raise HTTPException(status_code=400, detail="Ya estas matriculado en esta materia.")

    especialidad_req = "Ingeniería de Sistemas" if materia.facultad == "Sistemas" else "Ciencias Básicas"
    profesor_asignado = session.exec(select(Profesor).where(Profesor.especialidad == especialidad_req)).first()
    if not profesor_asignado: 
        raise HTTPException(status_code=400, detail="No hay profesores con la especialidad requerida.")

    grupos = session.exec(select(Grupo).where(Grupo.id_materia == data.id_materia)).all()
    
    if not grupos:
        salon = session.exec(select(Salon).where(Salon.nombre.like("Sala de Computo%" if materia.facultad == "Sistemas" else "AULA-%"))).first()
        grupo_elegido = Grupo(num_grupo=1, id_materia=data.id_materia, id_salon=salon.id, id_profesor=profesor_asignado.id, dia="Lunes", hora="7:00")
        session.add(grupo_elegido)
        session.commit(); session.refresh(grupo_elegido)
        inscritos = 0
    else:
        if data.id_grupo:
            grupo_elegido = session.get(Grupo, data.id_grupo)
            if not grupo_elegido or grupo_elegido.id_materia != data.id_materia:
                raise HTTPException(status_code=400, detail="Grupo seleccionado no es valido.")
        else:
            contexto = ContextoInscripcion(EstrategiaGrupoMasVacio())
            grupo_elegido = contexto.seleccionar(list(grupos), session)
            
        inscritos = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == grupo_elegido.id)).one()

    limite_capacidad = 30 if materia.facultad == "Sistemas" else 35

    if inscritos >= limite_capacidad:
        prefix_salon = "Sala de Computo%" if materia.facultad == "Sistemas" else "AULA-%"
        salones_ocupados = session.exec(select(Grupo.id_salon).where(Grupo.dia == grupo_elegido.dia, Grupo.hora == grupo_elegido.hora)).all()
        
        nuevo_salon = session.exec(
            select(Salon).where(Salon.nombre.like(prefix_salon))
            .where(Salon.id.not_in(salones_ocupados) if salones_ocupados else True)
        ).first()
        
        if not nuevo_salon and materia.facultad == "Sistemas":
            nuevo_salon = session.exec(
                select(Salon).where(Salon.nombre.like("AULA-%"))
                .where(Salon.id.not_in(salones_ocupados) if salones_ocupados else True)
            ).first()
            
        if not nuevo_salon:
            raise HTTPException(status_code=400, detail="No hay salones disponibles en la universidad para aperturar un nuevo grupo.")
            
        nuevo_grupo = Grupo(
            num_grupo=len(grupos) + 1,
            id_materia=data.id_materia,
            id_salon=nuevo_salon.id,
            id_profesor=profesor_asignado.id,
            dia=grupo_elegido.dia,
            hora=grupo_elegido.hora
        )
        session.add(nuevo_grupo)
        session.commit(); session.refresh(nuevo_grupo)
        
        estudiantes_a_mover = session.exec(select(Inscripcion).where(Inscripcion.id_grupo == grupo_elegido.id).limit(4)).all()
        for est_inscrito in estudiantes_a_mover:
            est_inscrito.id_grupo = nuevo_grupo.id
            session.add(est_inscrito)
            
        insc = Inscripcion(id_estudiante=estudiante.id, id_materia=data.id_materia, id_grupo=nuevo_grupo.id, estado="Activo")
        session.add(insc)
        session.commit()
        return {"alerta": False, "mensaje": f"Matricula exitosa. Se aperturó la seccion {nuevo_grupo.num_grupo} asegurando alumnos minimos."}
    else:
        insc = Inscripcion(id_estudiante=estudiante.id, id_materia=data.id_materia, id_grupo=grupo_elegido.id, estado="Activo")
        session.add(insc)
        session.commit()
        return {"alerta": False, "mensaje": f"Matricula exitosa en el Grupo {grupo_elegido.num_grupo}."}

@router.get("/profesor/salones-disponibles/{id_grupo}")
def obtener_salones_disponibles(id_grupo: int, session: Session = Depends(get_session)):
    grupo = session.get(Grupo, id_grupo)
    if not grupo: raise HTTPException(status_code=404, detail="Grupo no encontrado")
    materia = session.get(Materia, grupo.id_materia)

    salones_ocupados = session.exec(
        select(Grupo.id_salon)
        .where(Grupo.dia == grupo.dia, Grupo.hora == grupo.hora, Grupo.id != grupo.id)
    ).all()

    query = select(Salon)
    if salones_ocupados:
        query = query.where(Salon.id.not_in(salones_ocupados))

    todos_salones = session.exec(query).all()
    salones_filtrados = []

    for s in todos_salones:
        if materia.facultad == "Ciencias Básicas" and "Sala" in s.nombre:
            continue
        salones_filtrados.append({"id": s.id, "nombre": s.nombre, "capacidad": s.capacidad})

    return salones_filtrados

@router.put("/profesor/cambiar-salon")
def profesor_cambiar_salon(codigo_profesor: str, id_grupo: int, id_nuevo_salon: int, session: Session = Depends(get_session)):
    user = session.exec(select(Usuario).where(Usuario.codigo == codigo_profesor)).first()
    profesor = session.exec(select(Profesor).where(Profesor.id_usuario == user.id)).first()
    
    grupo = session.get(Grupo, id_grupo)
    materia = session.get(Materia, grupo.id_materia)
    nuevo_salon = session.get(Salon, id_nuevo_salon)
    
    if profesor.especialidad == "Ciencias Básicas" and "Sala" in nuevo_salon.nombre:
        raise HTTPException(status_code=400, detail="Los profesores de ciencias basicas no pueden usar salas de computo.")

    if materia.facultad == "Ciencias Básicas" and "AULA" not in nuevo_salon.nombre:
        raise HTTPException(status_code=400, detail="Incompatibilidad tecnica: Matematicas no se dicta en laboratorios.")
        
    inscritos = session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == id_grupo)).one()
    if inscritos > nuevo_salon.capacidad:
        raise HTTPException(status_code=400, detail=f"Aforo excedido: Capacidad de {nuevo_salon.capacidad} para {inscritos} alumnos.")
        
    grupo.id_salon = nuevo_salon.id
    session.add(grupo)
    session.commit()

    publicador = GestorEventosUniversidad()
    publicador.suscribir(IAOptimizationTriggerObserver()) 
    publicador.suscribir(ObservadorConsola())             
    
    publicador.notificar_todos("CAMBIO_SALON", {"grupo_id": id_grupo, "nuevo_salon_id": id_nuevo_salon, "session": session})
    return {"mensaje": "Validacion Genetica completada y salon actualizado en tiempo real."}

@router.post("/admin/optimizar-horarios")
def optimizar_infraestructura(codigo_admin: str, session: Session = Depends(get_session)):
    from services import OptimizadorAuditoria, ComponenteAlgoritmoGenetico
    motor = OptimizadorAuditoria(ComponenteAlgoritmoGenetico())
    return motor.ejecutar(session)