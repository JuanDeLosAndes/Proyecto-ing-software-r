import os
from sqlmodel import SQLModel, create_engine, Session
from modelos.entidades import (
    Salon, Materia, Rol, Usuario, Estudiante,
    Profesor, Administrador, ConfigFront, Grupo, Inscripcion, SesionToken
)


class ConexionBD:
    _instancia = None

    @classmethod
    def ObtenerMotor(cls):
        if cls._instancia is None:
            url = os.getenv("DATABASE_URL", "sqlite:///database.db")
            args = {"check_same_thread": False} if url.startswith("sqlite") else {}
            cls._instancia = create_engine(url, connect_args=args)
        return cls._instancia


def CrearTa():
    SQLModel.metadata.create_all(ConexionBD.ObtenerMotor(), checkfirst=True)


def ObtenerSes():
    with Session(ConexionBD.ObtenerMotor()) as ses:
        yield ses