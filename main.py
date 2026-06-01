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
from modelos.entidades import ConfigFront, SesionToken, Rol, Salon, Materia
from servicios.sesiones import GestorSesion
from controladores import configCtrl, usuarioCtrl, horarioCtrl, inscripcionCtrl, salonCtrl, adminCtrl

app = FastAPI(title="Asignacion de Salones - Universidad Catolica de Colombia")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def ManejadorValidacion(request: Request, exc: RequestValidationError):
    msgs = []
    for err in exc.errors():
        msg = err.get("msg", "Error de validacion")
        if msg.startswith("Value error, "): msg = msg[13:]
        msgs.append(msg)
    return JSONResponse(status_code=422, content={"detail": " | ".join(msgs)})

app.include_router(configCtrl.router)
app.include_router(usuarioCtrl.router)
app.include_router(horarioCtrl.router)
app.include_router(inscripcionCtrl.router)
app.include_router(salonCtrl.router)
app.include_router(adminCtrl.router)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── Seeders ──────────────────────────────────────────────────────

def _seed_roles(session: Session):
    for nombre in ["Estudiante", "Profesor", "Administrador"]:
        if not session.exec(select(Rol).where(Rol.nombre_rol == nombre)).first():
            session.add(Rol(nombre_rol=nombre))
    session.commit()


def _seed_salones(session: Session):
    """Singleton de infraestructura: crea salones base si no existen."""
    base = [
        ("Sala de Computo 1", 30), ("Sala de Computo 2", 30),
        ("Sala de Computo 3", 30), ("Sala de Computo 4", 30),
        ("Sala de Computo 5", 30),
        ("AULA-101", 35), ("AULA-102", 35), ("AULA-201", 35),
        ("AULA-202", 35), ("AULA-301", 35),
    ]
    for nombre, cap in base:
        if not session.exec(select(Salon).where(Salon.nombre == nombre)).first():
            session.add(Salon(nombre=nombre, capacidad=cap))
    session.commit()


def _seed_materias(session: Session):
    """
    20 materias de los 3 primeros semestres del pensum de Ing. de Sistemas UCC.
    Builder implícito: lista declarativa construida en dos pasos
    (insercion → asignacion de prerequisitos).
    """
    materias = [
        # ── Semestre 1 (sin prerequisito) ────────────────────────
        dict(nombre="Calculo Diferencial",          creditos=4, facultad="Ciencias Básicas", semestre=1, prereq=None),
        dict(nombre="Algebra Lineal",               creditos=3, facultad="Ciencias Básicas", semestre=1, prereq=None),
        dict(nombre="Fundamentos de Programacion",  creditos=4, facultad="Sistemas",          semestre=1, prereq=None),
        dict(nombre="Introduccion a la Ingenieria", creditos=2, facultad="Sistemas",          semestre=1, prereq=None),
        dict(nombre="Fisica Mecanica",              creditos=4, facultad="Ciencias Básicas", semestre=1, prereq=None),
        dict(nombre="Comunicacion Oral y Escrita",  creditos=2, facultad="Ciencias Básicas", semestre=1, prereq=None),
        # ── Semestre 2 ───────────────────────────────────────────
        dict(nombre="Calculo Integral",                 creditos=4, facultad="Ciencias Básicas", semestre=2, prereq="Calculo Diferencial"),
        dict(nombre="Fisica Electricidad y Magnetismo", creditos=4, facultad="Ciencias Básicas", semestre=2, prereq="Fisica Mecanica"),
        dict(nombre="Programacion Orientada a Objetos", creditos=4, facultad="Sistemas",          semestre=2, prereq=None),
        dict(nombre="Matematica Discreta",              creditos=3, facultad="Sistemas",          semestre=2, prereq=None),
        dict(nombre="Estadistica y Probabilidad",       creditos=3, facultad="Ciencias Básicas", semestre=2, prereq=None),
        dict(nombre="Ingles I",                         creditos=2, facultad="Ciencias Básicas", semestre=2, prereq=None),
        dict(nombre="Logica y Argumentacion",           creditos=2, facultad="Ciencias Básicas", semestre=2, prereq=None),
        # ── Semestre 3 ───────────────────────────────────────────
        dict(nombre="Calculo Multivariable",          creditos=4, facultad="Ciencias Básicas", semestre=3, prereq="Calculo Integral"),
        dict(nombre="Ecuaciones Diferenciales",       creditos=3, facultad="Ciencias Básicas", semestre=3, prereq="Calculo Integral"),
        dict(nombre="Estructuras de Datos",           creditos=4, facultad="Sistemas",          semestre=3, prereq=None),
        dict(nombre="Bases de Datos I",               creditos=4, facultad="Sistemas",          semestre=3, prereq=None),
        dict(nombre="Analisis y Diseno de Sistemas",  creditos=3, facultad="Sistemas",          semestre=3, prereq=None),
        dict(nombre="Arquitectura de Computadores",   creditos=3, facultad="Sistemas",          semestre=3, prereq=None),
        dict(nombre="Ingles II",                      creditos=2, facultad="Ciencias Básicas", semestre=3, prereq="Ingles I"),
    ]

    # Paso 1: insertar sin prerequisito
    for m in materias:
        if not session.exec(select(Materia).where(Materia.nombre == m["nombre"])).first():
            session.add(Materia(
                nombre=m["nombre"], creditos=m["creditos"],
                facultad=m["facultad"], semestre=m["semestre"],
                id_prerequisito=None
            ))
    session.commit()

    # Paso 2: asignar prerequisitos (DIP: no hardcodeamos IDs, buscamos por nombre)
    for m in [x for x in materias if x["prereq"]]:
        mat    = session.exec(select(Materia).where(Materia.nombre == m["nombre"])).first()
        prereq = session.exec(select(Materia).where(Materia.nombre == m["prereq"])).first()
        if mat and prereq and mat.id_prerequisito is None:
            mat.id_prerequisito = prereq.id
            session.add(mat)
    session.commit()


# ── Contexto base para templates (DIP: abstraccion de contexto) ──

def _ctx_base(request: Request) -> dict:
    return {"request": request, "anio": datetime.now().year}

def _obtener_config(session: Session):
    try:
        return session.exec(select(ConfigFront)).first()
    except Exception:
        return None


@app.on_event("startup")
def IniciarApp():
    CrearTa()
    with Session(ConexionBD.ObtenerMotor()) as session:
        _seed_roles(session)
        _seed_salones(session)
        _seed_materias(session)


# Sin emojis en los servicios del index
SERVICIOS_INDEX = [
    {
        "icono": "",
        "titulo": "Asignacion de Salones",
        "desc": "Sistema institucional de gestion de espacios fisicos con optimizacion genetica.",
        "url": "/login",
        "externo": False
    },
    {
        "icono": "",
        "titulo": "Correo Institucional",
        "desc": "Accede a tu correo @ucatolica.edu.co con tu cuenta Microsoft.",
        "url": "https://login.microsoftonline.com",
        "externo": True
    },
    {
        "icono": "",
        "titulo": "Campus AVA",
        "desc": "Plataforma de aulas virtuales, actividades y comunicaciones academicas.",
        "url": "https://newava.ucatolica.edu.co/ava2/login/index.php",
        "externo": True
    },
    {
        "icono": "",
        "titulo": "PAW 2.0",
        "desc": "Portal academico web: calificaciones, inscripciones y tramites estudiantiles.",
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
    return templates.TemplateResponse(request=request, name="index.html", context=ctx)

@app.get("/index")
def PaginaIndex(request: Request):
    return RedirectResponse(url="/")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(content=b"", media_type="image/x-icon")

@app.get("/login")
def PaginaLog(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context=_ctx_base(request))

@app.get("/sesion/{token}")
def PaginaSesion(token: str, request: Request):
    with Session(ConexionBD.ObtenerMotor()) as ses:
        sesion = GestorSesion.ValidarToken(ses, token)
        if not sesion:
            return RedirectResponse(url="/login")
    ctx = _ctx_base(request)
    ctx.update({"token": token, "rol": sesion.rol, "codigo": sesion.codigo_usuario})
    return templates.TemplateResponse(request=request, name="asignacion.html", context=ctx)

@app.get("/asignacion")
def PaginaAsig():
    return RedirectResponse(url="/login")