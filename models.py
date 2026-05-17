from sqlmodel import SQLModel, Field
from typing import Optional

class Rol(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_rol: str  # "Estudiante", "Administrador", "Profesor"

class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(index=True, unique=True)
    contrasena: str
    id_rol: Optional[int] = Field(default=None, foreign_key="rol.id")

class Estudiante(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")

class Administrador(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    codigo_admin: str
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")

class Profesor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    especialidad: str
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")

class Materia(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    creditos: int
    facultad: str  # "Sistemas" o "Ciencias Básicas"
    semestre: int

class Salon(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    capacidad: int

class Grupo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    num_grupo: int
    cupo_maximo: int = 35
    id_materia: Optional[int] = Field(default=None, foreign_key="materia.id")
    id_salon: Optional[int] = Field(default=None, foreign_key="salon.id")
    id_profesor: Optional[int] = Field(default=None, foreign_key="profesor.id")
    dia: Optional[str] = None   # "Lunes", "Martes", "Miercoles", "Jueves", "Viernes"
    hora: Optional[str] = None  # "7:00", "9:00", "11:00", etc.

class Inscripcion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_estudiante: Optional[int] = Field(default=None, foreign_key="estudiante.id")
    id_materia: Optional[int] = Field(default=None, foreign_key="materia.id")
    id_grupo: Optional[int] = Field(default=None, foreign_key="grupo.id")
    estado: str  # "Activo"

class ConfiguracionFront(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mensaje_superior: str
    mensaje_inferior: str
    url_imagen: str