"""
Configuracion de pruebas de integracion.

DIP: se inyecta un motor SQLite en memoria ANTES de importar el app,
     para que todas las dependencias usen la BD de test y no la real.
SRP: cada fixture tiene una sola responsabilidad.
"""
import sys
import os

# ── Agregar raiz del proyecto al path ──────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── Configurar motor de TEST antes de importar el app ─────────────
# Esto garantiza que el Singleton ConexionBD use la BD en memoria.
import database as _db_module
from sqlmodel import create_engine
from sqlmodel.pool import StaticPool

_MOTOR_TEST = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_db_module.ConexionBD._instancia = _MOTOR_TEST

# ── Ahora si importar el app ──────────────────────────────────────
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from main import app
from modelos.entidades import (
    Rol, Salon, Materia, Usuario, Estudiante,
    Profesor, Administrador, SesionToken, Grupo, Inscripcion
)


# ═══════════════════════════════════════════════════════════════════
# CLIENTE DE SESION — se crea UNA sola vez para todos los tests.
# El startup del app siembra roles, salones y materias en la BD test.
# ═══════════════════════════════════════════════════════════════════
@pytest.fixture(scope="session")
def client():
    """TestClient que dispara el startup del app (seeder de datos)."""
    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════════════
# HELPERS — funciones que usan los tests
# ═══════════════════════════════════════════════════════════════════
def registrar_usuario(client, rol, codigo, contrasena, nombre,
                      especialidad=None, semestre=None):
    """Factory helper: registra un usuario via API."""
    payload = {
        "rol_nombre":   rol,
        "codigo":       codigo,
        "contrasena":   contrasena,
        "nombre":       nombre,
        "especialidad": especialidad,
        "semestre":     semestre
    }
    return client.post("/usuarios/registrar", json=payload)


def loguear(client, codigo, contrasena):
    """Helper: hace login y devuelve el token."""
    res = client.post("/login", json={"codigo": codigo, "contrasena": contrasena})
    if res.status_code == 200:
        return res.json().get("token")
    return None


# ═══════════════════════════════════════════════════════════════════
# FIXTURES DE SESION — usuarios creados una sola vez por sesion de tests
# ═══════════════════════════════════════════════════════════════════
@pytest.fixture(scope="session")
def token_admin(client):
    """Crea y loguea un admin. Reutilizado en toda la sesion de tests."""
    registrar_usuario(
        client, "Administrador", "99001001", "AdminPass1",
        "Administrador de Prueba"
    )
    return loguear(client, "99001001", "AdminPass1")


@pytest.fixture(scope="session")
def token_profesor(client):
    """Crea y loguea un profesor de Sistemas. Reutilizado en toda la sesion."""
    registrar_usuario(
        client, "Profesor", "1122334455", "ProfPass1",
        "Profesor de Prueba", especialidad="Ingeniería de Sistemas"
    )
    return loguear(client, "1122334455", "ProfPass1")


@pytest.fixture(scope="session")
def token_profesor_cb(client):
    """Crea y loguea un profesor de Ciencias Basicas."""
    registrar_usuario(
        client, "Profesor", "5544332211", "ProfPass2",
        "Profesor CB", especialidad="Ciencias Básicas"
    )
    return loguear(client, "5544332211", "ProfPass2")


@pytest.fixture(scope="session")
def token_estudiante_s1(client):
    """Crea y loguea un estudiante de semestre 1."""
    registrar_usuario(
        client, "Estudiante", "67001001", "EstPass01",
        "Estudiante Sem1", semestre=1
    )
    return loguear(client, "67001001", "EstPass01")


@pytest.fixture(scope="session")
def token_estudiante_s2(client):
    """Crea y loguea un estudiante de semestre 2."""
    registrar_usuario(
        client, "Estudiante", "67001002", "EstPass02",
        "Estudiante Sem2", semestre=2
    )
    return loguear(client, "67001002", "EstPass02")