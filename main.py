from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

class Clase(BaseModel):
    id: int
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


clases_db = []

@app.get("/")
def inicio():
    return {"mensaje": "API funcionando 🚀"}

@app.get("/clases")
def obtener_clases():
    return clases_db

@app.post("/clases")
def crear_clase(clase: Clase):
    for c in clases_db:
        if c["id"] == clase.id:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe una clase con id {clase.id}"
            )

    clases_db.append(clase.dict())
    return {"mensaje": "Clase creada", "data": clase}

@app.get("/clases/{id}")
def obtener_clase(id: int):
    for clase in clases_db:
        if clase["id"] == id:
            return clase
    raise HTTPException(status_code=404, detail="Clase no encontrada")

@app.get("/buscar")
def buscar_clases(facultad: Optional[str] = None, activa: Optional[bool] = None):
    resultados = clases_db

    if facultad:
        resultados = [c for c in resultados if c["facultad"] == facultad]

    if activa is not None:
        resultados = [c for c in resultados if c["activa"] == activa]

    return resultados