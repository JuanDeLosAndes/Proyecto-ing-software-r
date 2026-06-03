from abc import ABC, abstractmethod
from typing import Dict
from sqlmodel import Session, select
from modelos.entidades import Usuario, Rol, Estudiante, Profesor, Administrador, Grupo


class IUsuarioFac(ABC):
    """ISP: interfaz con un solo metodo."""
    @abstractmethod
    def CrearPer(self, session: Session, usuarioId: int, datos: dict) -> None: pass


# Factory Method: cada fabrica crea un tipo de perfil concreto
class EstudianteFac(IUsuarioFac):
    def CrearPer(self, session: Session, usuarioId: int, datos: dict) -> None:
        session.add(Estudiante(
            nombre=datos.get("nombre", "Estudiante Nuevo"),
            semestre=datos.get("semestre", 1),
            id_usuario=usuarioId
        ))

class ProfesorFac(IUsuarioFac):
    def CrearPer(self, session: Session, usuarioId: int, datos: dict) -> None:
        session.add(Profesor(
            nombre=datos.get("nombre", "Profesor Nuevo"),
            especialidad=datos.get("especialidad", "Ciencias Basicas"),
            id_usuario=usuarioId
        ))

class AdminFac(IUsuarioFac):
    def CrearPer(self, session: Session, usuarioId: int, datos: dict) -> None:
        session.add(Administrador(
            nombre=datos.get("nombre", "Admin Nuevo"),
            codigo_admin=f"ADM-{usuarioId}",
            id_usuario=usuarioId
        ))


class FabricaUs:
    """
    Abstract Factory: agrupa las fabricas de usuario en un registro.
    OCP: para agregar un nuevo rol solo se registra aqui, sin modificar logica existente.
    """
    _fabricas: Dict[str, IUsuarioFac] = {
        "Estudiante":    EstudianteFac(),
        "Profesor":      ProfesorFac(),
        "Administrador": AdminFac(),
    }

    @classmethod
    def ObtenerFab(cls, rolNombre: str) -> IUsuarioFac:
        fab = cls._fabricas.get(rolNombre)
        if not fab:
            raise ValueError(f"Rol '{rolNombre}' no registrado en la fabrica.")
        return fab


class CreadorUs:
    """
    DIP: depende de IUsuarioFac (abstraccion), no de concretos.
    SRP: solo orquesta la creacion de usuario + perfil.
    """
    @staticmethod
    def RegistrarUs(session: Session, rolNombre: str,
                    credenciales: dict, perfilDatos: dict) -> Usuario:
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
        FabricaUs.ObtenerFab(rolNombre).CrearPer(session, nuevoUs.id, perfilDatos)
        session.commit()
        return nuevoUs


class ConstructorGrup:
    """
    Builder: construye Grupo paso a paso.
    SRP: encapsula toda la construccion, incluyendo la sesion 2.
    LSP corregido: conSesion2 es parte del builder; no se asigna fuera de construir().
    """
    def __init__(self):
        self._numGrupo   = 1
        self._idMateria  = None
        self._idSalon    = None
        self._idProfesor = None
        self._dia        = "Lunes"
        self._hora       = "07:00"
        self._dia2       = None
        self._hora2      = None
        self._idSalon2   = None

    def conNumero(self, n: int):               self._numGrupo   = n;  return self
    def conMateria(self, id: int):             self._idMateria  = id; return self
    def conSalon(self, id: int):               self._idSalon    = id; return self
    def conProfesor(self, id: int):            self._idProfesor = id; return self
    def conHorario(self, dia: str, hora: str): self._dia = dia; self._hora = hora; return self

    def conSesion2(self, dia: str, hora: str, id_salon: int):
        """Sesion 2 encapsulada en el Builder. No requiere asignacion externa."""
        self._dia2 = dia; self._hora2 = hora; self._idSalon2 = id_salon
        return self

    def construir(self) -> Grupo:
        return Grupo(
            num_grupo    = self._numGrupo,
            id_materia   = self._idMateria,
            id_salon     = self._idSalon,
            id_profesor  = self._idProfesor,
            dia          = self._dia,
            hora         = self._hora,
            dia2         = self._dia2,
            hora2        = self._hora2,
            id_salon2    = self._idSalon2,
        )