from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint
from typing import Optional, List


class Rol(SQLModel, table=True):
    """1:N con Usuario"""
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_rol: str
    usuarios: List["Usuario"] = Relationship(back_populates="rol")


class Usuario(SQLModel, table=True):
    """N:1 Rol | 1:1 con Estudiante/Profesor/Admin | 1:N SesionToken"""
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
    """1:1 Usuario | 1:N Inscripcion | N:M Materia via Inscripcion"""
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    # NUEVO: semestre académico actual del estudiante
    semestre: int = Field(default=1, ge=1, le=10)
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")

    usuario: Optional["Usuario"] = Relationship(back_populates="perfil_estudiante")
    inscripciones: List["Inscripcion"] = Relationship(back_populates="estudiante")


class Administrador(SQLModel, table=True):
    """1:1 con Usuario"""
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    codigo_admin: str
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")
    usuario: Optional["Usuario"] = Relationship(back_populates="perfil_administrador")


class Profesor(SQLModel, table=True):
    """1:1 Usuario | 1:N Grupo | N:M Estudiante via Grupo->Inscripcion"""
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    especialidad: str
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")

    usuario: Optional["Usuario"] = Relationship(back_populates="perfil_profesor")
    grupos: List["Grupo"] = Relationship(back_populates="profesor")


class Materia(SQLModel, table=True):
    """
    1:N Grupo | 1:N Inscripcion | N:M Estudiante via Inscripcion
    id_prerequisito: FK self-referencial (cadena de materias de Ciencias Basicas).
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    creditos: int
    facultad: str      # "Sistemas" | "Ciencias Básicas"
    semestre: int      # 1, 2 o 3 — controla qué semestre puede inscribirla
    # NUEVO: prerequisito directo. None = sin prerequisito.
    id_prerequisito: Optional[int] = Field(default=None, foreign_key="materia.id")

    grupos: List["Grupo"] = Relationship(back_populates="materia")
    inscripciones: List["Inscripcion"] = Relationship(back_populates="materia")


class Salon(SQLModel, table=True):
    """1:N Grupo (distintos horarios)"""
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    capacidad: int
    grupos: List["Grupo"] = Relationship(back_populates="salon")


class Grupo(SQLModel, table=True):
    """
    N:1 Materia | N:1 Salon | N:1 Profesor | 1:N Inscripcion
    Sesion 1: dia  + hora  + id_salon  (ya existia)
    Sesion 2: dia2 + hora2 + id_salon2 (NUEVO — 2 veces por semana)
    Franjas validas: "07:00","09:00","11:00" (manana) | "18:00","20:00" (noche)
    Cada franja dura 2 horas.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    num_grupo: int
    cupo_maximo: int = 30
    id_materia:  Optional[int] = Field(default=None, foreign_key="materia.id")
    id_salon:    Optional[int] = Field(default=None, foreign_key="salon.id")
    id_profesor: Optional[int] = Field(default=None, foreign_key="profesor.id")
    # Sesion 1
    dia:  Optional[str] = None
    hora: Optional[str] = None   # "07:00" | "09:00" | "11:00" | "18:00" | "20:00"
    # Sesion 2 — misma hora, dia diferente, salon puede ser diferente
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
    """
    Tabla puente N:M Estudiante <-> Materia.
    Constraint unico: un estudiante solo se inscribe UNA vez por materia.
    aprobada: None=en curso, True=aprobada, False=reprobada
              Controla el sistema de prerequisitos de Ciencias Basicas.
    """
    __table_args__ = (
        UniqueConstraint("id_estudiante", "id_materia", name="uq_estudiante_por_materia"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    id_estudiante: Optional[int] = Field(default=None, foreign_key="estudiante.id")
    id_materia:    Optional[int] = Field(default=None, foreign_key="materia.id")
    id_grupo:      Optional[int] = Field(default=None, foreign_key="grupo.id")
    estado: str    # "Activo" | "Aprobado" | "Reprobado"
    # NUEVO: para el sistema de prerequisitos
    aprobada: Optional[bool] = Field(default=None)

    estudiante: Optional["Estudiante"] = Relationship(back_populates="inscripciones")
    materia:    Optional["Materia"]    = Relationship(back_populates="inscripciones")
    grupo:      Optional["Grupo"]      = Relationship(back_populates="inscripciones")


class ConfigFront(SQLModel, table=True):
    """Sin relaciones. Configuracion global del frontend."""
    id: Optional[int] = Field(default=None, primary_key=True)
    mensaje_1: str
    mensaje_2: str
    mensaje_3: str
    mensaje_4: str
    url_img_1: str
    url_img_2: str
    url_img_3: str


class SesionToken(SQLModel, table=True):
    """N:1 Usuario. activo=False significa sesion cerrada o expirada."""
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    id_usuario: int = Field(foreign_key="usuario.id")
    codigo_usuario: str
    rol: str
    creado_en: str
    expira_en: str
    activo: bool = Field(default=True)
    usuario: Optional["Usuario"] = Relationship(back_populates="sesiones")