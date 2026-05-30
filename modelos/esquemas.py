from pydantic import BaseModel, field_validator, Field
from typing import Optional


class EsquemaLogin(BaseModel):
    codigo: str = Field(..., description="Código institucional universitario")
    contrasena: str = Field(..., description="Contraseña de acceso")

    @field_validator("codigo")
    @classmethod
    def val_codigo(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El código institucional es obligatorio.")
        if not v.isdigit():
            raise ValueError("El código solo puede contener números, no letras ni símbolos.")
        if len(v) < 8:
            raise ValueError("El código debe tener al menos 8 dígitos.")
        return v

    @field_validator("contrasena")
    @classmethod
    def val_contrasena(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La contraseña es obligatoria.")
        if len(v) < 4:
            raise ValueError("La contraseña debe tener al menos 4 caracteres.")
        return v


class EsquemaRegistro(BaseModel):
    rol_nombre: str = Field(..., description="Rol: Estudiante, Profesor o Administrador")
    codigo: str = Field(..., description="Código institucional")
    contrasena: str = Field(..., description="Contraseña")
    nombre: str = Field(..., description="Nombre completo")
    especialidad: Optional[str] = None

    @field_validator("rol_nombre")
    @classmethod
    def val_rol(cls, v: str) -> str:
        roles = ["Estudiante", "Profesor", "Administrador"]
        if v not in roles:
            raise ValueError(f"Rol inválido. Opciones: {', '.join(roles)}.")
        return v

    @field_validator("codigo")
    @classmethod
    def val_codigo(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El código es obligatorio.")
        if not v.isdigit():
            raise ValueError("El código solo puede contener números.")
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
            raise ValueError("La contraseña es obligatoria.")
        if len(v) < 4:
            raise ValueError("La contraseña debe tener al menos 4 caracteres.")
        return v


class EsquemaMatric(BaseModel):
    id_materia: int = Field(..., gt=0, description="ID de la materia a inscribir")
    id_grupo: Optional[int] = Field(None, gt=0, description="ID del grupo específico (opcional)")


class EsquemaConfigUp(BaseModel):
    codigo_admin: str = Field(..., description="Código del administrador")
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
            raise ValueError("El código de administrador es obligatorio.")
        if not v.isdigit():
            raise ValueError("El código solo puede contener números.")
        return v