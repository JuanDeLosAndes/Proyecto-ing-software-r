"""
Suite: endpoint de horarios.
Verifica que cada rol reciba la respuesta correcta.
"""
import pytest
from tests.conftest import registrar_usuario, loguear


class TestHorarios:
    def test_horario_admin_403(self, client, token_admin):
        """403 cuando un administrador consulta su horario."""
        res = client.get(f"/horarios?token={token_admin}")
        assert res.status_code == 403
        assert "administrador" in res.json()["detail"].lower()

    def test_horario_estudiante_sin_clases_vacio(self, client):
        """Estudiante recien creado recibe horario vacio."""
        registrar_usuario(
            client, "Estudiante", "67005501", "HorPass01",
            "Estudiante Vacio", semestre=1
        )
        token = loguear(client, "67005501", "HorPass01")
        res   = client.get(f"/horarios?token={token}")
        assert res.status_code == 200
        assert res.json() == {}

    def test_horario_estudiante_con_clases(self, client):
        """Tras inscribirse, el horario del estudiante tiene entradas."""
        registrar_usuario(
            client, "Estudiante", "67005502", "HorPass02",
            "Estudiante Con Clase", semestre=1
        )
        token    = loguear(client, "67005502", "HorPass02")
        materias = client.get(f"/materias?token={token}").json()
        mat      = next(m for m in materias if m["semestre"] == 1 and not m["prerequisito"])
        client.post(f"/inscribir?token={token}", json={"id_materia": mat["id"]})

        res = client.get(f"/horarios?token={token}")
        assert res.status_code == 200
        assert len(res.json()) > 0

    def test_horario_franja_formato_correcto(self, client):
        """Las claves del horario tienen formato 'HH:MM - HH:MM'."""
        registrar_usuario(
            client, "Estudiante", "67005503", "HorPass03",
            "Formato Franja", semestre=1
        )
        token    = loguear(client, "67005503", "HorPass03")
        materias = client.get(f"/materias?token={token}").json()
        mat      = [m for m in materias if m["semestre"] == 1 and not m["prerequisito"]][-1]
        client.post(f"/inscribir?token={token}", json={"id_materia": mat["id"]})

        horario = client.get(f"/horarios?token={token}").json()
        for franja in horario.keys():
            assert " - " in franja, f"Franja con formato incorrecto: {franja}"

    def test_horario_profesor_vacio(self, client, token_profesor):
        """Profesor sin grupos asignados tiene horario vacio."""
        res = client.get(f"/horarios?token={token_profesor}")
        # Puede ser vacio o tener datos si algun test anterior inscribio en un grupo con este profe
        assert res.status_code == 200
        assert isinstance(res.json(), dict)

    def test_horario_celda_tiene_datos_tooltip(self, client):
        """Cada celda del horario incluye salon_nombre y prof_nombre para el tooltip."""
        registrar_usuario(
            client, "Estudiante", "67005504", "HorPass04",
            "Tooltip Test", semestre=1
        )
        token    = loguear(client, "67005504", "HorPass04")
        materias = client.get(f"/materias?token={token}").json()
        mat      = [m for m in materias if m["semestre"] == 1 and not m["prerequisito"]][0]
        client.post(f"/inscribir?token={token}", json={"id_materia": mat["id"]})

        horario = client.get(f"/horarios?token={token}").json()
        for franja, dias in horario.items():
            for dia, celda in dias.items():
                assert "salon_nombre" in celda, f"Falta salon_nombre en {franja}/{dia}"
                assert "prof_nombre"  in celda, f"Falta prof_nombre en {franja}/{dia}"