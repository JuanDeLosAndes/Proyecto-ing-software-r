from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint
from typing import Optional, List


class Rol(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_rol: str
    usuarios: List["Usuario"] = Relationship(back_populates="rol")


class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(index=True, unique=True)
    contrasena: str
    id_rol: Optional[int] = Field(default=None, foreign_key="rol.id")

    rol: Optional["Rol"] = Relationship(back_populates="usuarios")
    perfil_estudiante:    Optional["Estudiante"]    = Relationship(back_populates="usuario")
    perfil_profesor:      Optional["Profesor"]      = Relationship(back_populates="usuario")
    perfil_administrador: Optional["Administrador"] = Relationship(back_populates="usuario")
    sesiones: List["SesionToken"] = Relationship(back_populates="usuario")


class Estudiante(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    semestre: int = Field(default=1, ge=1, le=10)
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")

    usuario: Optional["Usuario"] = Relationship(back_populates="perfil_estudiante")
    inscripciones: List["Inscripcion"] = Relationship(back_populates="estudiante")


class Administrador(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    codigo_admin: str
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")
    usuario: Optional["Usuario"] = Relationship(back_populates="perfil_administrador")


class Profesor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    especialidad: str
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")

    usuario: Optional["Usuario"] = Relationship(back_populates="perfil_profesor")
    grupos: List["Grupo"] = Relationship(back_populates="profesor")


class Materia(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    creditos: int
    facultad: str
    semestre: int
    id_prerequisito: Optional[int] = Field(default=None, foreign_key="materia.id")

    grupos: List["Grupo"] = Relationship(back_populates="materia")
    inscripciones: List["Inscripcion"] = Relationship(back_populates="materia")


class Salon(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    capacidad: int
    grupos: List["Grupo"] = Relationship(
        back_populates="salon",
        sa_relationship_kwargs={"foreign_keys": "[Grupo.id_salon]"}
    )


class Grupo(SQLModel, table=True):
   
    id: Optional[int] = Field(default=None, primary_key=True)
    num_grupo: int
    cupo_maximo: int = 30
    id_materia:  Optional[int] = Field(default=None, foreign_key="materia.id")
    id_salon:    Optional[int] = Field(default=None, foreign_key="salon.id")
    id_profesor: Optional[int] = Field(default=None, foreign_key="profesor.id")
    dia:   Optional[str] = None
    hora:  Optional[str] = None
    dia2:      Optional[str] = None
    hora2:     Optional[str] = None
    id_salon2: Optional[int] = Field(default=None, foreign_key="salon.id")

    materia:  Optional["Materia"]  = Relationship(back_populates="grupos")
    salon:    Optional["Salon"]    = Relationship(
        back_populates="grupos",
        sa_relationship_kwargs={"foreign_keys": "[Grupo.id_salon]"}
    )
    profesor: Optional["Profesor"] = Relationship(back_populates="grupos")
    inscripciones: List["Inscripcion"] = Relationship(back_populates="grupo")


class Inscripcion(SQLModel, table=True):
    
    __table_args__ = (
        UniqueConstraint("id_estudiante", "id_materia", name="uq_estudiante_por_materia"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    id_estudiante: Optional[int] = Field(default=None, foreign_key="estudiante.id")
    id_materia:    Optional[int] = Field(default=None, foreign_key="materia.id")
    id_grupo:      Optional[int] = Field(default=None, foreign_key="grupo.id")
    estado: str
    aprobada: Optional[bool] = Field(default=None)

    estudiante: Optional["Estudiante"] = Relationship(back_populates="inscripciones")
    materia:    Optional["Materia"]    = Relationship(back_populates="inscripciones")
    grupo:      Optional["Grupo"]      = Relationship(back_populates="inscripciones")


class ConfigFront(SQLModel, table=True):
    """Sin relaciones."""
    id: Optional[int] = Field(default=None, primary_key=True)
    mensaje_1: str
    mensaje_2: str
    mensaje_3: str
    mensaje_4: str
    url_img_1: str
    url_img_2: str
    url_img_3: str


class SesionToken(SQLModel, table=True):
    """N:1 Usuario."""
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    id_usuario: int = Field(foreign_key="usuario.id")
    codigo_usuario: str
    rol: str
    creado_en: str
    expira_en: str
    activo: bool = Field(default=True)
    usuario: Optional["Usuario"] = Relationship(back_populates="sesiones")