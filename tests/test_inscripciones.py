"""
Suite: inscripcion de materias, prerequisitos y semestres.
"""
import pytest
from tests.conftest import registrar_usuario, loguear


def _crear_estudiante_fresco(client, codigo, semestre):
    """Helper: crea y loguea un estudiante con codigo unico."""
    registrar_usuario(
        client, "Estudiante", codigo, "FreshPass1",
        f"Estudiante {codigo}", semestre=semestre
    )
    return loguear(client, codigo, "FreshPass1")


class TestListarMaterias:
    def test_lista_20_materias(self, client, token_estudiante_s1):
        """200 y exactamente 20 materias en el catalogo."""
        res = client.get(f"/materias?token={token_estudiante_s1}")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 20

    def test_materias_tienen_semestre(self, client, token_estudiante_s1):
        """Todas las materias tienen campo semestre entre 1 y 3."""
        res = client.get(f"/materias?token={token_estudiante_s1}")
        for mat in res.json():
            assert 1 <= mat["semestre"] <= 3

    def test_sin_token_401(self, client):
        """401 al acceder sin token."""
        res = client.get("/materias?token=invalido")
        assert res.status_code == 401


class TestInscripcion:
    def test_inscripcion_semestre_1_exitosa(self, client, token_profesor):
        """201 al inscribir una materia de semestre 1 siendo estudiante de semestre 1."""
        token_est = _crear_estudiante_fresco(client, "67007701", 1)

        # Obtener id de una materia de semestre 1 sin prerequisito
        materias = client.get(f"/materias?token={token_est}").json()
        mat_s1   = next(m for m in materias if m["semestre"] == 1 and not m["prerequisito"])

        res = client.post(
            f"/inscribir?token={token_est}",
            json={"id_materia": mat_s1["id"]}
        )
        assert res.status_code == 201
        assert "Matricula exitosa" in res.json()["mensaje"]

    def test_grupo_tiene_salon_y_profesor_asignados(self, client):
        """Al inscribirse, el grupo creado tiene salon y dia asignados automaticamente."""
        token_est = _crear_estudiante_fresco(client, "67007702", 1)
        materias  = client.get(f"/materias?token={token_est}").json()
        mat_s1    = next(m for m in materias if m["semestre"] == 1 and not m["prerequisito"])

        # Inscribir
        client.post(f"/inscribir?token={token_est}", json={"id_materia": mat_s1["id"]})

        # Verificar que el grupo tiene sesiones asignadas
        grupos = client.get(
            f"/materias/{mat_s1['id']}/grupos?token={token_est}"
        ).json()
        assert len(grupos) >= 1
        g = grupos[0]
        assert g["sesion_1"] != "Sin asignar"
        assert g["sesion_2"] != "Sin asignar"

    def test_grupo_tiene_2_sesiones_semanales(self, client):
        """El horario del estudiante muestra la materia 2 veces en la semana."""
        token_est = _crear_estudiante_fresco(client, "67007703", 1)
        materias  = client.get(f"/materias?token={token_est}").json()
        # Usar materia diferente a la de los tests anteriores
        mat_s1    = [m for m in materias if m["semestre"] == 1 and not m["prerequisito"]][1]

        client.post(f"/inscribir?token={token_est}", json={"id_materia": mat_s1["id"]})

        horario = client.get(f"/horarios?token={token_est}").json()
        # Contar apariciones de la materia
        apariciones = sum(
            1 for franja in horario.values()
            for celda in franja.values()
            if celda.get("materia") == mat_s1["nombre"]
        )
        assert apariciones == 2, f"La materia debe aparecer 2 veces, aparecio {apariciones}"

    def test_inscripcion_semestre_insuficiente_400(self, client):
        """400 al intentar inscribir materia de semestre 2 siendo de semestre 1."""
        token_est = _crear_estudiante_fresco(client, "67007704", 1)
        materias  = client.get(f"/materias?token={token_est}").json()
        mat_s2    = next(m for m in materias if m["semestre"] == 2)

        res = client.post(
            f"/inscribir?token={token_est}",
            json={"id_materia": mat_s2["id"]}
        )
        assert res.status_code == 400
        assert "semestre" in res.json()["detail"].lower()

    def test_inscripcion_duplicada_409(self, client):
        """409 al intentar inscribir la misma materia dos veces."""
        token_est = _crear_estudiante_fresco(client, "67007705", 1)
        materias  = client.get(f"/materias?token={token_est}").json()
        mat_s1    = [m for m in materias if m["semestre"] == 1 and not m["prerequisito"]][2]

        client.post(f"/inscribir?token={token_est}", json={"id_materia": mat_s1["id"]})
        res = client.post(f"/inscribir?token={token_est}", json={"id_materia": mat_s1["id"]})
        assert res.status_code == 409

    def test_inscripcion_rol_incorrecto_403(self, client, token_profesor):
        """403 cuando un profesor intenta inscribirse en una materia."""
        materias = client.get(f"/materias?token={token_profesor}").json()
        mat      = materias[0]
        res = client.post(
            f"/inscribir?token={token_profesor}",
            json={"id_materia": mat["id"]}
        )
        assert res.status_code == 403

    def test_prerequisito_no_cumplido_400(self, client):
        """400 al intentar inscribir Calculo Integral sin aprobar Calculo Diferencial."""
        token_est = _crear_estudiante_fresco(client, "67007706", 2)
        materias  = client.get(f"/materias?token={token_est}").json()
        mat_ci    = next(m for m in materias if m["nombre"] == "Calculo Integral")

        res = client.post(
            f"/inscribir?token={token_est}",
            json={"id_materia": mat_ci["id"]}
        )
        assert res.status_code == 400
        assert "prerequisito" in res.json()["detail"].lower()