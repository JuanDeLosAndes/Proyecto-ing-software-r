import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import Response, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlmodel import Session, select
from database import CrearTa, ConexionBD
from modelos.entidades import ConfigFront, SesionToken, Rol
from servicios.sesiones import GestorSesion
from controladores import configCtrl, usuarioCtrl, horarioCtrl, inscripcionCtrl, salonCtrl, adminCtrl

app = FastAPI(title="Asignacion de Salones - Universidad Católica de Colombia")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def ManejadorValidacion(request: Request, exc: RequestValidationError):
    msgs = []
    for err in exc.errors():
        msg = err.get("msg", "Error de validación")
        if msg.startswith("Value error, "): msg = msg[13:]
        msgs.append(msg)
    return JSONResponse(status_code=422, content={"detail": " | ".join(msgs)})

app.include_router(configCtrl.router)
app.include_router(usuarioCtrl.router)
app.include_router(horarioCtrl.router)
app.include_router(inscripcionCtrl.router)
app.include_router(salonCtrl.router)
app.include_router(adminCtrl.router)

# Singleton (OCP): siempre montamos static aunque esté vacío
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def _ctx_base(request: Request) -> dict:
    """
    DIP: todos los templates dependen de este contexto abstracto.
    SRP: función con una sola responsabilidad — construir contexto base.
    """
    return {"request": request, "anio": datetime.now().year}


def _obtener_config(session: Session):
    """Factory Method: centraliza la obtención de configuración."""
    try:
        return session.exec(select(ConfigFront)).first()
    except Exception:
        return None


@app.on_event("startup")
def IniciarApp():
    CrearTa() # Esto crea las tablas
    
    # --- SEEDER DE ROLES ---
    with Session(ConexionBD.ObtenerMotor()) as session:
        roles_necesarios = ["Estudiante", "Profesor", "Administrador"]
        for nombre in roles_necesarios:
            # Buscamos si el rol ya existe
            rol_db = session.exec(select(Rol).where(Rol.nombre_rol == nombre)).first()
            if not rol_db:
                # Si no existe, lo insertamos
                session.add(Rol(nombre_rol=nombre))
        session.commit()


# ── SERVICIOS para el index (pasados a Jinja2 como contexto) ──
# Builder implícito: la lista se construye de forma declarativa.
SERVICIOS_INDEX = [
    {
        "icono": "🏫",
        "titulo": "Asignación de Salones",
        "desc": "Sistema inteligente de gestión de espacios físicos con algoritmos genéticos.",
        "url": "/login",
        "externo": False
    },
    {
        "icono": "📧",
        "titulo": "Correo Institucional",
        "desc": "Accede a tu correo @ucatolica.edu.co con tu cuenta Microsoft.",
        "url": "https://login.microsoftonline.com",
        "externo": True
    },
    {
        "icono": "📚",
        "titulo": "Campus AVA",
        "desc": "Plataforma de aulas virtuales, actividades y comunicaciones académicas.",
        "url": "https://newava.ucatolica.edu.co/ava2/login/index.php",
        "externo": True
    },
    {
        "icono": "🎓",
        "titulo": "PAW 2.0",
        "desc": "Portal académico web: calificaciones, inscripciones y trámites estudiantiles.",
        "url": "https://portalweb.ucatolica.edu.co/paw/",
        "externo": True
    },
]


@app.get("/")
def PaginaIn(request: Request):
    ctx = _ctx_base(request)
    ctx["servicios"] = SERVICIOS_INDEX
    with Session(ConexionBD.ObtenerMotor()) as ses:
        ctx["config"] = _obtener_config(ses)
        
    # 👇 CAMBIA ESTA LÍNEA
    return templates.TemplateResponse(request=request, name="index.html", context=ctx)


@app.get("/index")
def PaginaIndex(request: Request):
    return RedirectResponse(url="/")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(content=b"", media_type="image/x-icon")


@app.get("/login")
def PaginaLog(request: Request):
    ctx = _ctx_base(request)
    
    # 👇 CAMBIA ESTA LÍNEA
    return templates.TemplateResponse(request=request, name="login.html", context=ctx)


@app.get("/sesion/{token}")
def PaginaSesion(token: str, request: Request):
    with Session(ConexionBD.ObtenerMotor()) as ses:
        sesion = GestorSesion.ValidarToken(ses, token)
        if not sesion:
            return RedirectResponse(url="/login")
    ctx = _ctx_base(request)
    ctx.update({"token": token, "rol": sesion.rol, "codigo": sesion.codigo_usuario})
    
    # 👇 CAMBIA ESTA LÍNEA
    return templates.TemplateResponse(request=request, name="asignacion.html", context=ctx)


@app.get("/asignacion")
def PaginaAsig():
    return RedirectResponse(url="/login")