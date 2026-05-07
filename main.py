import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import create_db_and_tables


app = FastAPI(title="Sistema de Asignación de Salones")


if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
def inicio(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
def pagina_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/asignacion")
def pagina_asignacion(request: Request):
    return templates.TemplateResponse("asignacion.html", {"request": request})