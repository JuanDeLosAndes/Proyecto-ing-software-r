from sqlmodel import SQLModel, create_engine, Session

# Importamos todos los modelos para que SQLModel sepa qué tablas crear en la base de datos
from models import Salon, Materia, Rol, Usuario, Estudiante, Profesor, Administrador, ConfiguracionFront, Grupo, Inscripcion

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

def create_db_and_tables():
    # Solo crea las tablas vacías en la base de datos sin inyectar datos de prueba
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session