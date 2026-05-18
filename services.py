import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from sqlmodel import Session, select, func
from models import Usuario, Rol, Estudiante, Profesor, Materia, Salon, Grupo, Inscripcion

# =========================================================================
# 1. PATRÓN CREACIONAL: FACTORY METHOD
# =========================================================================
# <<interface>> Target para la creación de perfiles dinámicos según el Rol
class IUsuarioFactory(ABC):
    @abstractmethod
    def crear_perfil(self, session: Session, usuario_id: int, datos: dict) -> None:
        pass

class EstudianteFactory(IUsuarioFactory):
    def crear_perfil(self, session: Session, usuario_id: int, datos: dict) -> None:
        perfil = Estudiante(nombre=datos.get("nombre", "Estudiante Nuevo"), id_usuario=usuario_id)
        session.add(perfil)

class ProfesorFactory(IUsuarioFactory):
    def crear_perfil(self, session: Session, usuario_id: int, datos: dict) -> None:
        perfil = Profesor(
            nombre=datos.get("nombre", "Profesor Nuevo"), 
            especialidad=datos.get("especialidad", "Ciencias Básicas"), 
            id_usuario=usuario_id
        )
        session.add(perfil)

# Clase Creadora / Orquestadora
class CreadorUsuario:
    _fabricas: Dict[str, IUsuarioFactory] = {
        "Estudiante": EstudianteFactory(),
        "Profesor": ProfesorFactory()
    }

    @staticmethod
    def registrar_nuevo_usuario(session: Session, rol_nombre: str, credenciales: dict, perfil_datos: dict) -> Usuario:
        rol = session.exec(select(Rol).where(Rol.nombre_rol == rol_nombre)).first()
        if not rol:
            raise ValueError(f"El rol {rol_nombre} no existe en el sistema.")
        
        nuevo_usuario = Usuario(codigo=credenciales["codigo"], contrasena=credenciales["contrasena"], id_rol=rol.id)
        session.add(nuevo_usuario)
        session.commit()
        session.refresh(nuevo_usuario)
        
        fabrica = CreadorUsuario._fabricas.get(rol_nombre)
        if fabrica:
            fabrica.crear_perfil(session, nuevo_usuario.id, perfil_datos)
            session.commit()
            
        return nuevo_usuario


# =========================================================================
# 2. PATRÓN ESTRUCTURAL: ADAPTER
# =========================================================================
# Servicio Externo de Terceros (Simulado)
class AWS_SES_EmailService:
    def send_raw_email(self, destination: str, body: str):
        print(f"[AWS SES SUB-SYSTEM] Conectando... Enviando a {destination}: {body}")

# <<interface>> Target
class INotificador(ABC):
    @abstractmethod
    def notificar(self, destinatario: str, mensaje: str) -> None:
        pass

# Adaptador de Estructura
class EmailAdapter(INotificador):
    def __init__(self):
        self._servicio_externo = AWS_SES_EmailService()

    def notificar(self, destinatario: str, mensaje: str) -> None:
        # Adaptamos la llamada común al método nativo de la API de AWS
        self._servicio_externo.send_raw_email(destination=destinatario, body=mensaje)


# =========================================================================
# 3. PATRÓN ESTRUCTURAL: DECORATOR
# =========================================================================
# <<interface>> Component
class IOptimizador(ABC):
    @abstractmethod
    def ejecutar(self, session: Session) -> dict: 
        pass

# Concrete Component (Envoltura del Algoritmo Genético Real)
class ComponenteAlgoritmoGenetico(IOptimizador):
    def ejecutar(self, session: Session) -> dict:
        from algoritmo_genetico import ejecutar_algoritmo_universitario
        return ejecutar_algoritmo_universitario(session)

# Base Decorator
class OptimizadorDecorator(IOptimizador):
    def __init__(self, optimizador_base: IOptimizador):
        self._optimizador_base = optimizador_base
        
    def ejecutar(self, session: Session) -> dict:
        return self._optimizador_base.ejecutar(session)

# Concrete Decorator (Responsabilidad adicional: Logs e informes de Auditoría)
class OptimizadorAuditoria(OptimizadorDecorator):
    def ejecutar(self, session: Session) -> dict:
        print("[AUDITORÍA - DECORATOR] Iniciando recalculo genético de la infraestructura universitaria...")
        resultado = super().ejecutar(session)
        print(f"[AUDITORÍA - DECORATOR] Sincronización finalizada en la DB. Estado IA: {resultado}")
        return resultado


# =========================================================================
# 4. PATRÓN DE COMPORTAMIENTO: OBSERVER
# =========================================================================
# <<interface>> Observer
class IObserver(ABC):
    @abstractmethod
    def update(self, evento: str, datos: dict) -> None: 
        pass

# Subject / Publisher (Orquestador Basado en Eventos)
class GestorEventosUniversidad:
    def __init__(self):
        self._observadores: List[IObserver] = []

    def suscribir(self, observador: IObserver):
        if observador not in self._observadores:
            self._observadores.append(observador)

    def notificar_todos(self, evento: str, datos: dict):
        for obs in self._observadores:
            obs.update(evento, datos)

# Observador Concreto 1: Disparador automático de la Inteligencia Artificial
class IAOptimizationTriggerObserver(IObserver):
    def update(self, evento: str, datos: dict) -> None:
        if evento == "CAMBIO_SALON":
            session = datos.get("session")
            if session:
                # Usamos el Optimizador base envuelto por el Decorator de Auditoría
                motor_decorado = OptimizadorAuditoria(ComponenteAlgoritmoGenetico())
                motor_decorado.ejecutar(session)

# Observador Concreto 2: Alertas automáticas desatendidas vía Adapter
class EmailNotificationObserver(IObserver):
    def update(self, evento: str, datos: dict) -> None:
        if evento == "CAMBIO_SALON":
            try:
                notificador = EmailAdapter()
                notificador.notificar(
                    destinatario="comunidad_universitaria@catolica.edu.co",
                    mensaje=f"Notificación de Infraestructura: El grupo con ID {datos.get('grupo_id')} ha actualizado su salón de clases."
                )
            except Exception as e:
                print(f"[OBSERVER ERROR] No se pudo enviar el correo: {e}")


# =========================================================================
# 5. PATRÓN DE COMPORTAMIENTO: STRATEGY
# =========================================================================
# <<interface>> Strategy para la asignación/balanceo de estudiantes
class IEstrategiaAsignacion(ABC):
    @abstractmethod
    def seleccionar_grupo_optimo(self, grupos: list, session: Session) -> Grupo:
        pass

# Estrategia 1: El estudiante entra al grupo que tenga menos personas matriculadas (Tu lógica original)
class EstrategiaGrupoMasVacio(IEstrategiaAsignacion):
    def seleccionar_grupo_optimo(self, grupos: list, session: Session) -> Grupo:
        print("[STRATEGY] Ejecutando algoritmo de balanceo: Grupo más vacío.")
        return min(grupos, key=lambda g: session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)).one())

# Estrategia 2: Carga Secuencial (Llena estrictamente por número de grupo)
class EstrategiaSecuencial(IEstrategiaAsignacion):
    def seleccionar_grupo_optimo(self, grupos: list, session: Session) -> Grupo:
        print("[STRATEGY] Ejecutando algoritmo alterno: Asignación secuencial.")
        return sorted(grupos, key=lambda g: g.num_grupo)[0]

# Contexto de Ejecución
class ContextoInscripcion:
    def __init__(self, estrategia: IEstrategiaAsignacion):
        self._estrategia = estrategia

    def cambiar_estrategia(self, estrategia: IEstrategiaAsignacion):
        self._estrategia = estrategia

    def seleccionar(self, grupos: list, session: Session) -> Grupo:
        return self._estrategia.seleccionar_grupo_optimo(grupos, session)