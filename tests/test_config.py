"""
Suite: configuracion del frontend (mensajes e imagenes del carrusel).
"""
import pytest


class TestConfig:
    def test_get_config_default_200(self, client):
        """200 y campos presentes en /front/config aunque no haya config en BD."""
        res = client.get("/front/config")
        assert res.status_code == 200
        data = res.json()
        for campo in ["mensaje_1", "mensaje_2", "mensaje_3", "mensaje_4",
                      "url_img_1", "url_img_2", "url_img_3"]:
            assert campo in data

    def test_guardar_config_admin_200(self, client, token_admin):
        """200 al guardar configuracion como administrador."""
        res = client.post("/front/config", json={
            "codigo_admin": "99001001",
            "msg_1": "Sistema UCC",
            "msg_2": "Semestre 2026-2",
            "msg_3": "Bienvenidos",
            "msg_4": "Sistema activo",
            "img_1": "https://www.ucatolica.edu.co/campus.jpg",
            "img_2": "",
            "img_3": ""
        })
        assert res.status_code == 200
        assert "actualizada" in res.json()["mensaje"].lower()

    def test_config_se_persiste(self, client, token_admin):
        """Los cambios guardados persisten al hacer GET nuevamente."""
        client.post("/front/config", json={
            "codigo_admin": "99001001",
            "msg_1": "Mensaje Persistente"
        })
        res = client.get("/front/config")
        assert res.status_code == 200
        assert res.json()["mensaje_1"] == "Mensaje Persistente"

    def test_guardar_config_no_admin_403(self, client, token_estudiante_s1):
        """403 cuando un estudiante intenta guardar la configuracion."""
        res = client.post("/front/config", json={
            "codigo_admin": "67001001",
            "msg_1": "Intento Ilegal"
        })
        assert res.status_code in (403, 404)

    def test_guardar_config_codigo_invalido_422(self, client):
        """422 cuando el codigo del admin contiene letras."""
        res = client.post("/front/config", json={
            "codigo_admin": "ADMIN",
            "msg_1": "Test"
        })
        assert res.status_code == 422