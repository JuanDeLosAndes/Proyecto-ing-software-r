from abc import ABC, abstractmethod
from typing import Dict
from sqlmodel import Session, select
from modelos.entidades import Usuario, Rol, Estudiante, Profesor, Administrador, Grupo


# ── Interface Segregation (I): cada interfaz tiene una sola responsabilidad ──

class IUsuarioFac(ABC):
    @abstractmethod
    def CrearPer(self, session: Session, usuarioId: int, datos: dict) -> None: pass


# ── Factory Method (Creacional): cada fábrica crea un tipo de perfil ──

class EstudianteFac(IUsuarioFac):
    def CrearPer(self, session: Session, usuarioId: int, datos: dict) -> None:
        perfil = Estudiante(nombre=datos.get("nombre", "Estudiante Nuevo"), id_usuario=usuarioId)
        session.add(perfil)

class ProfesorFac(IUsuarioFac):
    def CrearPer(self, session: Session, usuarioId: int, datos: dict) -> None:
        perfil = Profesor(
            nombre=datos.get("nombre", "Profesor Nuevo"),
            especialidad=datos.get("especialidad", "Ciencias Basicas"),
            id_usuario=usuarioId
        )
        session.add(perfil)

class AdminFac(IUsuarioFac):
    def CrearPer(self, session: Session, usuarioId: int, datos: dict) -> None:
        perfil = Administrador(
            nombre=datos.get("nombre", "Admin Nuevo"),
            codigo_admin=f"ADM-{usuarioId}",
            id_usuario=usuarioId
        )
        session.add(perfil)


# ── Abstract Factory (Creacional): agrupa todas las fábricas de usuario ──

class FabricaUs:
    _fabricas: Dict[str, IUsuarioFac] = {
        "Estudiante":     EstudianteFac(),
        "Profesor":       ProfesorFac(),
        "Administrador":  AdminFac()
    }

    @classmethod
    def ObtenerFab(cls, rolNombre: str) -> IUsuarioFac:
        fab = cls._fabricas.get(rolNombre)
        if not fab:
            raise ValueError(f"Rol '{rolNombre}' no registrado en la fabrica.")
        return fab


# ── Dependency Inversion (D): CreadorUs depende de IUsuarioFac, no de concretos ──

class CreadorUs:
    @staticmethod
    def RegistrarUs(session: Session, rolNombre: str, credenciales: dict, perfilDatos: dict) -> Usuario:
        rol = session.exec(select(Rol).where(Rol.nombre_rol == rolNombre)).first()
        if not rol:
            raise ValueError(f"El rol '{rolNombre}' no existe.")
        nuevoUs = Usuario(
            codigo=credenciales["codigo"],
            contrasena=credenciales["contrasena"],
            id_rol=rol.id
        )
        session.add(nuevoUs)
        session.commit()
        session.refresh(nuevoUs)
        fab = FabricaUs.ObtenerFab(rolNombre)
        fab.CrearPer(session, nuevoUs.id, perfilDatos)
        session.commit()
        return nuevoUs


# ── Builder (Creacional): construye objetos Grupo paso a paso ──

class ConstructorGrup:
    def __init__(self):
        self._numGrupo  = 1
        self._idMateria = None
        self._idSalon   = None
        self._idProfesor= None
        self._dia       = "Lunes"
        self._hora      = "7:00"

    def conNumero(self, n: int):       self._numGrupo   = n;  return self
    def conMateria(self, id: int):     self._idMateria  = id; return self
    def conSalon(self, id: int):       self._idSalon    = id; return self
    def conProfesor(self, id: int):    self._idProfesor = id; return self
    def conHorario(self, dia: str, hora: str):
        self._dia = dia; self._hora = hora; return self

    def construir(self) -> Grupo:
        return Grupo(
            num_grupo   = self._numGrupo,
            id_materia  = self._idMateria,
            id_salon    = self._idSalon,
            id_profesor = self._idProfesor,
            dia         = self._dia,
            hora        = self._hora
        )