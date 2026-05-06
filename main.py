from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import create_db_and_tables
from routes.api import router as api_router

app = FastAPI(title="Sistema de Asignación de Salones")

# Unir las rutas del módulo api.py
app.include_router(api_router)

# Montar archivos estáticos del frontend
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.on_event("startup")
def on_startup():
    # Esto crea automáticamente todas las tablas del diagrama ER en database.db
    create_db_and_tables()

@app.get("/")
def inicio():
    return {"mensaje": "API con Persistencia SQLModel y Roles funcionando 🚀"}