import os
from fastapi import FastAPI, Request
from fastapi.responses import Response, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from database import CrearTa, ConexionBD
from sqlmodel import Session
from servicios.sesiones import GestorSesion
from controladores import configCtrl, usuarioCtrl, horarioCtrl, inscripcionCtrl, salonCtrl, adminCtrl

app = FastAPI(title="Asignacion de Salones - Universidad Católica de Colombia")

# ── CORS: necesario para Azure y llamadas entre dominios ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Manejador de errores de validación Pydantic (422) ──
@app.exception_handler(RequestValidationError)
async def ManejadorValidacion(request: Request, exc: RequestValidationError):
    msgs = []
    for err in exc.errors():
        msg = err.get("msg", "Error de validación")
        if msg.startswith("Value error, "):
            msg = msg[13:]
        msgs.append(msg)
    return JSONResponse(status_code=422, content={"detail": " | ".join(msgs)})


app.include_router(configCtrl.router)
app.include_router(usuarioCtrl.router)
app.include_router(horarioCtrl.router)
app.include_router(inscripcionCtrl.router)
app.include_router(salonCtrl.router)
app.include_router(adminCtrl.router)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def IniciarApp():
    CrearTa()


@app.get("/")
def PaginaIn(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/index")
def PaginaIndex(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(content=b"", media_type="image/x-icon")


@app.get("/login")
def PaginaLog(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/sesion/{token}")
def PaginaSesion(token: str, request: Request):
    with Session(ConexionBD.ObtenerMotor()) as session:
        ses = GestorSesion.ValidarToken(session, token)
        if not ses:
            return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "asignacion.html",
        {"request": request, "token": token, "rol": ses.rol, "codigo": ses.codigo_usuario}
    )


@app.get("/asignacion")
def PaginaAsig():
    return RedirectResponse(url="/login")