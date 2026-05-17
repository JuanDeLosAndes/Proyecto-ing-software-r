import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import create_db_and_tables
from api import router as api_router


app = FastAPI(title="Sistema de Asignación de Salones")

# ¡ESTA ES LA LÍNEA CLAVE QUE FALTABA CONECTAR!
app.include_router(api_router)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
def inicio(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

@app.get("/login")
def pagina_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request})

@app.get("/asignacion")
def pagina_asignacion(request: Request):
    return templates.TemplateResponse(request=request, name="asignacion.html", context={"request": request})