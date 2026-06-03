from pydantic import BaseModel, field_validator, Field
from typing import Optional, Literal


class EsquemaLogin(BaseModel):
    codigo: str = Field(..., description="Codigo institucional", example="67001234")
    contrasena: str = Field(..., description="Contrasena de acceso", example="MiClave12")

    @field_validator("codigo")
    @classmethod
    def val_codigo(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El codigo institucional es obligatorio.")
        if not v.isdigit():
            raise ValueError("El codigo solo puede contener numeros, no letras ni simbolos.")
        if len(v) < 8:
            raise ValueError("El codigo debe tener al menos 8 digitos.")
        return v

    @field_validator("contrasena")
    @classmethod
    def val_contrasena(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La contrasena es obligatoria.")
        return v


class EsquemaCambioContrasena(BaseModel):
    """Esquema para cambio de contraseña sin sesion activa."""
    codigo: str = Field(..., description="Codigo institucional del usuario", example="67001234")
    nueva_contrasena: str = Field(..., description="Nueva contraseña (min 8 chars, 1 mayuscula, 1 minuscula)", example="NuevaClave1")

    @field_validator("codigo")
    @classmethod
    def val_codigo(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El codigo es obligatorio.")
        if not v.isdigit():
            raise ValueError("El codigo solo puede contener numeros.")
        if len(v) < 8:
            raise ValueError("El codigo debe tener al menos 8 digitos.")
        return v

    @field_validator("nueva_contrasena")
    @classmethod
    def val_nueva_contrasena(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La nueva contraseña es obligatoria.")
        if len(v) < 8:
            raise ValueError("La contraseña debe tener minimo 8 caracteres.")
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra mayuscula.")
        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe contener al menos una letra minuscula.")
        return v


class EsquemaRegistro(BaseModel):
    rol_nombre: Literal["Estudiante", "Profesor", "Administrador"] = Field(
        ..., description="Rol del usuario en el sistema"
    )
    codigo: str = Field(
        ...,
        description="Solo numeros. Estudiante: 8 dig. inicia 6700. Profesor: 10 dig. Admin: 8 dig. inicia 9900.",
        example="67001234"
    )
    contrasena: str = Field(
        ...,
        description="Minimo 8 caracteres, al menos una mayuscula y una minuscula.",
        example="MiClave12"
    )
    nombre: str = Field(..., description="Nombre completo del usuario", example="Juan Perez")
    especialidad: Optional[str] = Field(
        None,
        description="Solo Profesores: 'Ingenieria de Sistemas' o 'Ciencias Basicas'",
        example="Ingenieria de Sistemas"
    )
    semestre: Optional[int] = Field(
        None, ge=1, le=10,
        description="Solo Estudiantes: semestre academico actual (1 a 10)",
        example=1
    )

    @field_validator("codigo")
    @classmethod
    def val_codigo(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El codigo es obligatorio.")
        if not v.isdigit():
            raise ValueError("El codigo solo puede contener numeros.")
        return v

    @field_validator("nombre")
    @classmethod
    def val_nombre(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre es obligatorio.")
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres.")
        return v

    @field_validator("contrasena")
    @classmethod
    def val_contrasena(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La contrasena es obligatoria.")
        if len(v) < 8:
            raise ValueError("La contrasena debe tener minimo 8 caracteres.")
        if not any(c.isupper() for c in v):
            raise ValueError("La contrasena debe contener al menos una letra mayuscula.")
        if not any(c.islower() for c in v):
            raise ValueError("La contrasena debe contener al menos una letra minuscula del abecedario.")
        return v


class EsquemaMatric(BaseModel):
    id_materia: int = Field(..., gt=0, description="ID de la materia a inscribir")
    id_grupo: Optional[int] = Field(None, gt=0, description="ID del grupo especifico (opcional)")
    jornada: Literal["manana", "noche", "sabado"] = Field(
        "manana",
        description="Jornada preferida: 'manana' (07-13h), 'noche' (18-22h) o 'sabado' (07-13h + 15-17h)"
    )


class EsquemaConfigUp(BaseModel):
    codigo_admin: str = Field(..., description="Codigo del administrador")
    msg_1: Optional[str] = None
    msg_2: Optional[str] = None
    msg_3: Optional[str] = None
    msg_4: Optional[str] = None
    img_1: Optional[str] = None
    img_2: Optional[str] = None
    img_3: Optional[str] = None

    @field_validator("codigo_admin")
    @classmethod
    def val_admin(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El codigo de administrador es obligatorio.")
        if not v.isdigit():
            raise ValueError("El codigo solo puede contener numeros.")
        return v