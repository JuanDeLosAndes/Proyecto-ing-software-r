"""
Suite: rutas de usuarios y autenticacion.
Cubre: registro, login, logout, validaciones de codigo y contrasena.
"""
import pytest
from tests.conftest import registrar_usuario, loguear


class TestRegistro:
    """Pruebas del endpoint POST /usuarios/registrar"""

    def test_registro_estudiante_valido(self, client):
        """201 al registrar un estudiante con datos correctos."""
        res = registrar_usuario(
            client, "Estudiante", "67009901", "Secure01",
            "Estudiante Valido", semestre=1
        )
        assert res.status_code == 201
        assert "id" in res.json()

    def test_registro_admin_valido(self, client):
        """201 al registrar un administrador con datos correctos."""
        res = registrar_usuario(
            client, "Administrador", "99009901", "AdminSec1",
            "Admin Valido"
        )
        assert res.status_code == 201

    def test_registro_profesor_valido(self, client):
        """201 al registrar un profesor con especialidad."""
        res = registrar_usuario(
            client, "Profesor", "1199009901", "ProfSec01",
            "Prof Valido", especialidad="Ingeniería de Sistemas"
        )
        assert res.status_code == 201

    def test_codigo_duplicado_409(self, client):
        """409 al intentar registrar un codigo ya existente."""
        registrar_usuario(
            client, "Estudiante", "67009902", "Secure02",
            "Duplicado Base", semestre=1
        )
        res = registrar_usuario(
            client, "Estudiante", "67009902", "Secure02",
            "Duplicado Intento", semestre=1
        )
        assert res.status_code == 409
        assert "67009902" in res.json()["detail"]

    def test_contrasena_corta_422(self, client):
        """422 cuando la contrasena tiene menos de 8 caracteres."""
        res = registrar_usuario(
            client, "Estudiante", "67009903", "Abc1",
            "Contrasena Corta", semestre=1
        )
        assert res.status_code == 422
        assert "8" in res.json()["detail"]

    def test_contrasena_sin_mayuscula_422(self, client):
        """422 cuando la contrasena no tiene mayusculas."""
        res = registrar_usuario(
            client, "Estudiante", "67009904", "sinmayusc1",
            "Sin Mayuscula", semestre=1
        )
        assert res.status_code == 422
        assert "mayuscula" in res.json()["detail"].lower()

    def test_contrasena_sin_minuscula_422(self, client):
        """422 cuando la contrasena no tiene minusculas."""
        res = registrar_usuario(
            client, "Estudiante", "67009905", "SINMINUS1",
            "Sin Minuscula", semestre=1
        )
        assert res.status_code == 422
        assert "minuscula" in res.json()["detail"].lower()

    def test_codigo_con_letras_422(self, client):
        """422 cuando el codigo contiene letras (solo se permiten numeros)."""
        res = registrar_usuario(
            client, "Estudiante", "670ABC01", "Secure01",
            "Codigo Con Letras", semestre=1
        )
        assert res.status_code == 422
        assert "numero" in res.json()["detail"].lower()

    def test_codigo_estudiante_prefijo_invalido_400(self, client):
        """400 cuando el codigo de estudiante no empieza con 6700."""
        res = registrar_usuario(
            client, "Estudiante", "12345678", "Secure01",
            "Prefijo Invalido", semestre=1
        )
        assert res.status_code == 400

    def test_estudiante_sin_semestre_400(self, client):
        """400 cuando se registra un estudiante sin indicar el semestre."""
        res = registrar_usuario(
            client, "Estudiante", "67009999", "Secure01",
            "Sin Semestre"
            # semestre=None por defecto
        )
        assert res.status_code == 400
        assert "semestre" in res.json()["detail"].lower()

    def test_profesor_sin_especialidad_400(self, client):
        """400 cuando se registra un profesor sin especialidad."""
        res = registrar_usuario(
            client, "Profesor", "9911009901", "ProfSec01",
            "Prof Sin Especialidad"
        )
        assert res.status_code == 400
        assert "especialidad" in res.json()["detail"].lower()


class TestLogin:
    """Pruebas del endpoint POST /login"""

    def test_login_exitoso_200(self, client):
        """200 y token al hacer login con credenciales correctas."""
        registrar_usuario(
            client, "Estudiante", "67008801", "LoginPass1",
            "Login OK", semestre=1
        )
        res = client.post("/login", json={"codigo": "67008801", "contrasena": "LoginPass1"})
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["rol"] == "Estudiante"

    def test_login_credenciales_incorrectas_401(self, client):
        """401 al usar contrasena incorrecta."""
        res = client.post("/login", json={"codigo": "67008801", "contrasena": "WrongPass9"})
        assert res.status_code == 401

    def test_login_codigo_vacio_422(self, client):
        """422 al enviar codigo vacio."""
        res = client.post("/login", json={"codigo": "", "contrasena": "LoginPass1"})
        assert res.status_code == 422

    def test_logout_200(self, client, token_estudiante_s1):
        """200 al cerrar una sesion valida."""
        res = client.post(f"/logout?token={token_estudiante_s1}")
        assert res.status_code == 200

    def test_token_invalido_401(self, client):
        """401 al usar un token que no existe."""
        res = client.get("/horarios?token=token-que-no-existe-jamas")
        assert res.status_code == 401