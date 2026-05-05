from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import SQLModel, Field, Session, select
from typing import Optional, List
from fastapi.staticfiles import StaticFiles
from pydantic import field_validator
from database import engine, create_db_and_tables, get_session

app = FastAPI()

# Montar archivos estáticos
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# --- MODELOS DE DATOS (SQLModel) ---

class Clase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    activa: bool
    horario: float
    facultad: str
    capacidad: int

    @field_validator("horario")
    def validar_horario(cls, value):
        if value < 0:
            raise ValueError("El horario no puede ser negativo")
        return value

    @field_validator("capacidad")
    def validar_capacidad(cls, value):
        if value < 0:
            raise ValueError("La capacidad no puede ser negativa")
        if value > 35:
            raise ValueError("La capacidad no puede ser mayor a 35")
        return value

class Estudiante(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario: str = Field(index=True, unique=True)
    password: str
    nombre: str
    # Nota: SQLite no soporta listas directamente. 
    # Para este nivel, guardaremos materias como un string simple o tabla aparte luego.
    materias: Optional[str] = None 

# --- EVENTOS DE INICIO ---

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# --- RUTAS DE LA API ---

@app.get("/")
def inicio():
    return {"mensaje": "API con Persistencia SQLModel funcionando 🚀"}

@app.get("/clases", response_model=List[Clase])
def obtener_clases(session: Session = Depends(get_session)):
    clases = session.exec(select(Clase)).all()
    return clases

@app.post("/clases")
def crear_clase(clase: Clase, session: Session = Depends(get_session)):
    # Verificar si el ID ya existe manualmente si se envía uno
    db_clase = session.get(Clase, clase.id)
    if db_clase:
        raise HTTPException(status_code=400, detail="ID de clase ya existe")
    
    session.add(clase)
    session.commit()
    session.refresh(clase)
    return {"mensaje": "Clase creada", "data": clase}

@app.get("/clases/{id}", response_model=Clase)
def obtener_clase(id: int, session: Session = Depends(get_session)):
    clase = session.get(Clase, id)
    if not clase:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    return clase

@app.get("/buscar", response_model=List[Clase])
def buscar_clases(
    facultad: Optional[str] = None, 
    activa: Optional[bool] = None, 
    session: Session = Depends(get_session)
):
    statement = select(Clase)
    if facultad:
        statement = statement.where(Clase.facultad == facultad)
    if activa is not None:
        statement = statement.where(Clase.activa == activa)
    
    resultados = session.exec(statement).all()
    return resultados

@app.post("/estudiantes")
def crear_estudiante(est: Estudiante, session: Session = Depends(get_session)):
    # Verificar duplicados por ID o Usuario
    statement = select(Estudiante).where((Estudiante.id == est.id) | (Estudiante.usuario == est.usuario))
    existe = session.exec(statement).first()
    
    if existe:
        raise HTTPException(status_code=400, detail="ID o Usuario ya existe")

    session.add(est)
    session.commit()
    session.refresh(est)
    return {"mensaje": "Estudiante creado", "data": est}

@app.post("/login")
def login(usuario: str, password: str, session: Session = Depends(get_session)):
    statement = select(Estudiante).where(Estudiante.usuario == usuario, Estudiante.password == password)
    estudiante = session.exec(statement).first()
    
    if estudiante:
        return {"mensaje": "Login correcto", "usuario": estudiante.nombre}

    raise HTTPException(status_code=401, detail="Credenciales incorrectas")