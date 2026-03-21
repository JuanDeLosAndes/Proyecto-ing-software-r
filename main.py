from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class Clase(BaseModel):
    id: int
    nombre: str
    activa: bool
    duracion: float
    facultad: str

clases_db = []

@app.get("/")
def inicio():
    return {"mensaje": "API funcionando 🚀"}

#get
@app.get("/clases")
def obtener_clases():
    return clases_db

#post
@app.post("/clases")
def crear_clase(clase: Clase):
    clases_db.append(clase.dict())
    return {"mensaje": "Clase creada", "data": clase}

#get id
@app.get("/clases/{id}")
def obtener_clase(id: int):
    for clase in clases_db:
        if clase["id"] == id:
            return clase
    raise HTTPException(status_code=404, detail="Clase no encontrada")

#filtro
@app.get("/buscar")
def buscar_clases(facultad: Optional[str] = None, activa: Optional[bool] = None):
    
    resultados = clases_db

    if facultad:
        resultados = [c for c in resultados if c["facultad"] == facultad]

    if activa is not None:
        resultados = [c for c in resultados if c["activa"] == activa]

    return resultados