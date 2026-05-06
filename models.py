from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from pydantic import field_validator

# --- ENTIDADES BASE DE USUARIOS ---

class Rol(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_rol: str  # Puede ser: "Estudiante", "Administrador", "Profesor"

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

# --- ENTIDADES ACADÉMICAS ---

class Materia(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    creditos: int
    facultad: str
    semestre: int

class Salon(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    capacidad: int

    @field_validator("capacidad")
    def validar_capacidad(cls, value):
        if value < 0:
            raise ValueError("La capacidad no puede ser negativa")
        if value > 35:
            raise ValueError("La capacidad no puede ser mayor a 35")
        return value

class Grupo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    num_grupo: int
    cupo_maximo: int
    id_materia: Optional[int] = Field(default=None, foreign_key="materia.id")
    id_salon: Optional[int] = Field(default=None, foreign_key="salon.id")

class Inscripcion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_estudiante: Optional[int] = Field(default=None, foreign_key="estudiante.id")
    id_materia: Optional[int] = Field(default=None, foreign_key="materia.id")
    estado: str

# Entidad para la configuración del Front (Administrador)
class ConfiguracionFront(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mensaje_bienvenida: str