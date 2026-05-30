from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint
from typing import Optional, List


# ═══════════════════════════════════════════════
# ROL
# ═══════════════════════════════════════════════
class Rol(SQLModel, table=True):
    """
    1:N con Usuario
    Un rol (Estudiante, Profesor, Administrador) lo pueden tener N usuarios.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_rol: str

    # ← 1:N → un rol tiene MUCHOS usuarios
    usuarios: List["Usuario"] = Relationship(back_populates="rol")


# ═══════════════════════════════════════════════
# USUARIO
# ═══════════════════════════════════════════════
class Usuario(SQLModel, table=True):
    """
    N:1 con Rol (muchos usuarios tienen UN rol)
    1:1 con Estudiante / Profesor / Administrador
    1:N con SesionToken
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(index=True, unique=True)
    contrasena: str
    id_rol: Optional[int] = Field(default=None, foreign_key="rol.id")

    # ← N:1 → muchos usuarios tienen UN rol
    rol: Optional["Rol"] = Relationship(back_populates="usuarios")

    # ← 1:1 → un usuario tiene UN perfil (solo uno de los tres existirá)
    perfil_estudiante:    Optional["Estudiante"]     = Relationship(back_populates="usuario")
    perfil_profesor:      Optional["Profesor"]       = Relationship(back_populates="usuario")
    perfil_administrador: Optional["Administrador"]  = Relationship(back_populates="usuario")

    # ← 1:N → un usuario puede tener N sesiones (historial de accesos)
    sesiones: List["SesionToken"] = Relationship(back_populates="usuario")


# ═══════════════════════════════════════════════
# ESTUDIANTE
# ═══════════════════════════════════════════════
class Estudiante(SQLModel, table=True):
    """
    1:1 con Usuario
    1:N con Inscripcion
    N:M con Materia (a través de Inscripcion)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")

    # ← 1:1 inverso
    usuario: Optional["Usuario"] = Relationship(back_populates="perfil_estudiante")

    # ← 1:N → un estudiante tiene MUCHAS inscripciones (una por materia)
    inscripciones: List["Inscripcion"] = Relationship(back_populates="estudiante")


# ═══════════════════════════════════════════════
# ADMINISTRADOR
# ═══════════════════════════════════════════════
class Administrador(SQLModel, table=True):
    """1:1 con Usuario"""
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    codigo_admin: str
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")

    usuario: Optional["Usuario"] = Relationship(back_populates="perfil_administrador")


# ═══════════════════════════════════════════════
# PROFESOR
# ═══════════════════════════════════════════════
class Profesor(SQLModel, table=True):
    """
    1:1 con Usuario
    1:N con Grupo
    N:M INDIRECTO con Estudiante (a través de Grupo → Inscripcion)
    Regla: un profesor puede tener N estudiantes de la misma materia.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    especialidad: str
    id_usuario: Optional[int] = Field(default=None, foreign_key="usuario.id")

    # ← 1:1 inverso
    usuario: Optional["Usuario"] = Relationship(back_populates="perfil_profesor")

    # ← 1:N → un profesor dicta MUCHOS grupos
    grupos: List["Grupo"] = Relationship(back_populates="profesor")


# ═══════════════════════════════════════════════
# MATERIA
# ═══════════════════════════════════════════════
class Materia(SQLModel, table=True):
    """
    1:N con Grupo
    1:N con Inscripcion
    N:M con Estudiante (a través de Inscripcion)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    creditos: int
    facultad: str
    semestre: int

    # ← 1:N → una materia tiene MUCHOS grupos (secciones)
    grupos: List["Grupo"] = Relationship(back_populates="materia")

    # ← 1:N → una materia tiene MUCHAS inscripciones
    inscripciones: List["Inscripcion"] = Relationship(back_populates="materia")


# ═══════════════════════════════════════════════
# SALON
# ═══════════════════════════════════════════════
class Salon(SQLModel, table=True):
    """
    1:N con Grupo
    Un salón puede tener N grupos asignados en distintos horarios.
    El algoritmo genético garantiza que no haya dos grupos en el mismo salón
    al mismo tiempo (eso es lógica de negocio, no restricción de BD).
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    capacidad: int

    # ← 1:N → un salón es usado por MUCHOS grupos (en diferentes días/horas)
    grupos: List["Grupo"] = Relationship(back_populates="salon")


# ═══════════════════════════════════════════════
# GRUPO
# ═══════════════════════════════════════════════
class Grupo(SQLModel, table=True):
    """
    N:1 con Materia  (muchos grupos pertenecen a UNA materia)
    N:1 con Salon    (muchos grupos usan UN salón, en distintos horarios)
    N:1 con Profesor (muchos grupos son dictados por UN profesor)
    1:N con Inscripcion
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    num_grupo: int
    cupo_maximo: int = 30
    id_materia:  Optional[int] = Field(default=None, foreign_key="materia.id")
    id_salon:    Optional[int] = Field(default=None, foreign_key="salon.id")
    id_profesor: Optional[int] = Field(default=None, foreign_key="profesor.id")
    dia:  Optional[str] = None
    hora: Optional[str] = None

    # ← N:1 → muchos grupos son de UNA materia
    materia:  Optional["Materia"]  = Relationship(back_populates="grupos")
    # ← N:1 → muchos grupos usan UN salón
    salon:    Optional["Salon"]    = Relationship(back_populates="grupos")
    # ← N:1 → muchos grupos son dictados por UN profesor
    profesor: Optional["Profesor"] = Relationship(back_populates="grupos")

    # ← 1:N → un grupo tiene MUCHAS inscripciones (un registro por estudiante)
    inscripciones: List["Inscripcion"] = Relationship(back_populates="grupo")


# ═══════════════════════════════════════════════
# INSCRIPCION  (tabla puente N:M entre Estudiante y Materia)
# ═══════════════════════════════════════════════
class Inscripcion(SQLModel, table=True):
    """
    TABLA PUENTE N:M entre Estudiante y Materia.

    Relaciones:
      N:1 con Estudiante  (muchas inscripciones de UN estudiante)
      N:1 con Materia     (muchas inscripciones de UNA materia)
      N:1 con Grupo       (muchas inscripciones en UN grupo)

    Constraint único (id_estudiante, id_materia):
      → Un estudiante solo puede inscribirse UNA VEZ por materia.
      → Al estar en un único grupo de esa materia, tiene UN SOLO profesor.
      → Esto garantiza: estudiante → 1 grupo → 1 profesor por materia.
    """
    __table_args__ = (
        UniqueConstraint(
            "id_estudiante", "id_materia",
            name="uq_estudiante_por_materia"
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    id_estudiante: Optional[int] = Field(default=None, foreign_key="estudiante.id")
    id_materia:    Optional[int] = Field(default=None, foreign_key="materia.id")
    id_grupo:      Optional[int] = Field(default=None, foreign_key="grupo.id")
    estado: str

    # ← N:1 → muchas inscripciones pertenecen a UN estudiante
    estudiante: Optional["Estudiante"] = Relationship(back_populates="inscripciones")
    # ← N:1 → muchas inscripciones son de UNA materia
    materia:    Optional["Materia"]    = Relationship(back_populates="inscripciones")
    # ← N:1 → muchas inscripciones pertenecen a UN grupo
    grupo:      Optional["Grupo"]      = Relationship(back_populates="inscripciones")


# ═══════════════════════════════════════════════
# CONFIG FRONT
# ═══════════════════════════════════════════════
class ConfigFront(SQLModel, table=True):
    """Sin relaciones. Tabla de configuración global del sistema."""
    id: Optional[int] = Field(default=None, primary_key=True)
    mensaje_1: str
    mensaje_2: str
    mensaje_3: str
    mensaje_4: str
    url_img_1: str
    url_img_2: str
    url_img_3: str


# ═══════════════════════════════════════════════
# SESION TOKEN
# ═══════════════════════════════════════════════
class SesionToken(SQLModel, table=True):
    """
    N:1 con Usuario
    Un usuario puede tener N sesiones (histórico de accesos / dispositivos).
    Activo=False significa sesión cerrada o expirada.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    id_usuario: int = Field(foreign_key="usuario.id")
    codigo_usuario: str
    rol: str
    creado_en: str
    expira_en: str
    activo: bool = Field(default=True)

    # ← N:1 → muchas sesiones pertenecen a UN usuario
    usuario: Optional["Usuario"] = Relationship(back_populates="sesiones")