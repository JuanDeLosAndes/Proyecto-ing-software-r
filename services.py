import random
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from sqlmodel import Session, select, func
from models import Usuario, Rol, Estudiante, Profesor, Administrador, Materia, Salon, Grupo, Inscripcion

class IUsuarioFactory(ABC):
    @abstractmethod
    def crear_perfil(self, session: Session, usuario_id: int, datos: dict) -> None: pass

class EstudianteFactory(IUsuarioFactory):
    def crear_perfil(self, session: Session, usuario_id: int, datos: dict) -> None:
        perfil = Estudiante(nombre=datos.get("nombre", "Estudiante Nuevo"), id_usuario=usuario_id)
        session.add(perfil)

class ProfesorFactory(IUsuarioFactory):
    def crear_perfil(self, session: Session, usuario_id: int, datos: dict) -> None:
        perfil = Profesor(
            nombre=datos.get("nombre", "Profesor Nuevo"), 
            especialidad=datos.get("especialidad", "Ciencias Basicas"), 
            id_usuario=usuario_id
        )
        session.add(perfil)

class AdministradorFactory(IUsuarioFactory):
    def crear_perfil(self, session: Session, usuario_id: int, datos: dict) -> None:
        perfil = Administrador(
            nombre=datos.get("nombre", "Admin Nuevo"), 
            codigo_admin=f"ADM-{usuario_id}", 
            id_usuario=usuario_id
        )
        session.add(perfil)

class CreadorUsuario:
    _fabricas: Dict[str, IUsuarioFactory] = {
        "Estudiante": EstudianteFactory(),
        "Profesor": ProfesorFactory(),
        "Administrador": AdministradorFactory()
    }

    @staticmethod
    def registrar_nuevo_usuario(session: Session, rol_nombre: str, credenciales: dict, perfil_datos: dict) -> Usuario:
        rol = session.exec(select(Rol).where(Rol.nombre_rol == rol_nombre)).first()
        if not rol: raise ValueError(f"El rol '{rol_nombre}' no existe. Usa mayuscula inicial.")
        
        nuevo_usuario = Usuario(codigo=credenciales["codigo"], contrasena=credenciales["contrasena"], id_rol=rol.id)
        session.add(nuevo_usuario)
        session.commit()
        session.refresh(nuevo_usuario)
        
        fabrica = CreadorUsuario._fabricas.get(rol_nombre)
        if fabrica:
            fabrica.crear_perfil(session, nuevo_usuario.id, perfil_datos)
            session.commit()
        return nuevo_usuario


class IRegistroAuditoria(ABC):
    @abstractmethod
    def registrar_evento(self, accion: str, modulo: str) -> None: pass

class AdaptadorConsola(IRegistroAuditoria):
    def registrar_evento(self, accion: str, modulo: str) -> None:
        print(f"\n[ALERTA DE SISTEMA - {modulo}] {accion}\n")


class IOptimizador(ABC):
    @abstractmethod
    def ejecutar(self, session: Session) -> dict: pass

class ComponenteAlgoritmoGenetico(IOptimizador):
    def ejecutar(self, session: Session) -> dict:
        from algoritmo_genetico import ejecutar_algoritmo_universitario
        return ejecutar_algoritmo_universitario(session)

class OptimizadorDecorator(IOptimizador):
    def __init__(self, optimizador_base: IOptimizador):
        self._optimizador_base = optimizador_base
    def ejecutar(self, session: Session) -> dict:
        return self._optimizador_base.ejecutar(session)

class OptimizadorAuditoria(OptimizadorDecorator):
    def ejecutar(self, session: Session) -> dict:
        print("\n=======================================================")
        print("[AUDITORIA - DECORATOR] Iniciando Inteligencia Artificial...")
        print("=======================================================\n")
        resultado = super().ejecutar(session)
        print(f"\n[AUDITORIA - DECORATOR] IA Finalizada. Estado: {resultado}\n")
        return resultado


class IObserver(ABC):
    @abstractmethod
    def update(self, evento: str, datos: dict) -> None: pass

class GestorEventosUniversidad:
    def __init__(self):
        self._observadores: List[IObserver] = []
    def suscribir(self, observador: IObserver):
        if observador not in self._observadores: self._observadores.append(observador)
    def notificar_todos(self, evento: str, datos: dict):
        for obs in self._observadores: obs.update(evento, datos)

class IAOptimizationTriggerObserver(IObserver):
    def update(self, evento: str, datos: dict) -> None:
        if evento == "CAMBIO_SALON":
            session = datos.get("session")
            if session:
                motor_decorado = OptimizadorAuditoria(ComponenteAlgoritmoGenetico())
                motor_decorado.ejecutar(session)

class ObservadorConsola(IObserver):
    def update(self, evento: str, datos: dict) -> None:
        if evento == "CAMBIO_SALON":
            adaptador = AdaptadorConsola()
            adaptador.registrar_evento(
                accion=f"El grupo ID {datos.get('grupo_id')} fue movido al salon ID {datos.get('nuevo_salon_id')}.",
                modulo="INFRAESTRUCTURA"
            )

class IEstrategiaAsignacion(ABC):
    @abstractmethod
    def seleccionar_grupo_optimo(self, grupos: list, session: Session) -> Grupo: pass

class EstrategiaGrupoMasVacio(IEstrategiaAsignacion):
    def seleccionar_grupo_optimo(self, grupos: list, session: Session) -> Grupo:
        return min(grupos, key=lambda g: session.exec(select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)).one())

class ContextoInscripcion:
    def __init__(self, estrategia: IEstrategiaAsignacion):
        self._estrategia = estrategia
    def seleccionar(self, grupos: list, session: Session) -> Grupo:
        return self._estrategia.seleccionar_grupo_optimo(grupos, session)