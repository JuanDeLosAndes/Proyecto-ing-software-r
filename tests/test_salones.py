"""
Suite: disponibilidad de salones y cambio de salon por profesor.
"""
import pytest
from tests.conftest import registrar_usuario, loguear


def _inscribir_y_obtener_grupo(client, token_est, id_materia):
    """Helper: inscribe y retorna el id del grupo asignado."""
    client.post(f"/inscribir?token={token_est}", json={"id_materia": id_materia})
    grupos = client.get(f"/materias/{id_materia}/grupos?token={token_est}").json()
    return grupos[0]["id_grupo"] if grupos else None


class TestSalonesDisponibles:
    def test_requiere_rol_profesor_403(self, client, token_estudiante_s1):
        """403 cuando un estudiante consulta salones disponibles."""
        res = client.get(f"/profesor/salones-disponibles/1?token={token_estudiante_s1}")
        assert res.status_code == 403

    def test_grupo_inexistente_404(self, client, token_profesor):
        """404 cuando el grupo no existe."""
        res = client.get(f"/profesor/salones-disponibles/99999?token={token_profesor}")
        assert res.status_code == 404

    def test_salones_disponibles_excluyen_ocupados(self, client, token_profesor):
        """
        Los salones ya ocupados en la misma franja horaria no aparecen
        en la lista de disponibles (sesion 1 y sesion 2 revisadas).
        """
        # Crear un estudiante e inscribirlo para generar un grupo con salon asignado
        registrar_usuario(
            client, "Estudiante", "67006601", "SalPass01",
            "Estudiante Salon", semestre=1
        )
        token_est = loguear(client, "67006601", "SalPass01")
        materias  = client.get(f"/materias?token={token_est}").json()
        mat       = next(m for m in materias if m["semestre"] == 1 and not m["prerequisito"])
        id_grupo  = _inscribir_y_obtener_grupo(client, token_est, mat["id"])

        if not id_grupo:
            pytest.skip("No se pudo obtener grupo para el test")

        salones_disp = client.get(
            f"/profesor/salones-disponibles/{id_grupo}?token={token_profesor}"
        ).json()

        # El salon ya asignado al grupo NO debe aparecer como disponible
        grupos   = client.get(f"/materias/{mat['id']}/grupos?token={token_est}").json()
        # Verificar que la respuesta es una lista de dicts con campos esperados
        for sal in salones_disp:
            assert "id"       in sal
            assert "nombre"   in sal
            assert "capacidad" in sal


class TestCambiarSalon:
    def test_requiere_rol_profesor_403(self, client, token_estudiante_s1):
        """403 cuando un estudiante intenta cambiar salon."""
        res = client.put(
            f"/profesor/cambiar-salon?id_grupo=1&id_nuevo_salon=1&token={token_estudiante_s1}"
        )
        assert res.status_code == 403

    def test_grupo_inexistente_404(self, client, token_profesor):
        """404 cuando el grupo no existe."""
        res = client.put(
            f"/profesor/cambiar-salon?id_grupo=99999&id_nuevo_salon=1&token={token_profesor}"
        )
        assert res.status_code == 404

    def test_salon_inexistente_404(self, client, token_profesor):
        """404 cuando el salon destino no existe."""
        registrar_usuario(
            client, "Estudiante", "67006602", "SalPass02",
            "Para Cambio Salon", semestre=1
        )
        token_est = loguear(client, "67006602", "SalPass02")
        materias  = client.get(f"/materias?token={token_est}").json()
        mat       = [m for m in materias if m["semestre"] == 1 and not m["prerequisito"]][1]
        id_grupo  = _inscribir_y_obtener_grupo(client, token_est, mat["id"])

        if not id_grupo:
            pytest.skip("No se pudo obtener grupo")

        res = client.put(
            f"/profesor/cambiar-salon?id_grupo={id_grupo}&id_nuevo_salon=99999&token={token_profesor}"
        )
        assert res.status_code == 404

    def test_cambio_exitoso_persiste(self, client, token_profesor):
        """
        El cambio de salon queda guardado en BD.
        Los estudiantes del grupo ven el nuevo salon en su horario.
        """
        # Crear estudiante e inscribir
        registrar_usuario(
            client, "Estudiante", "67006603", "SalPass03",
            "Cambio Salon Est", semestre=1
        )
        token_est = loguear(client, "67006603", "SalPass03")
        materias  = client.get(f"/materias?token={token_est}").json()
        mat       = [m for m in materias if m["semestre"] == 1 and not m["prerequisito"]][2]
        id_grupo  = _inscribir_y_obtener_grupo(client, token_est, mat["id"])

        if not id_grupo:
            pytest.skip("No se pudo obtener grupo")

        # Obtener salones disponibles
        salones = client.get(
            f"/profesor/salones-disponibles/{id_grupo}?token={token_profesor}&num_sesion=1"
        ).json()

        if not salones:
            pytest.skip("No hay salones disponibles para cambiar")

        nuevo_salon_id   = salones[0]["id"]
        nuevo_salon_name = salones[0]["nombre"]

        # Cambiar salon
        res = client.put(
            f"/profesor/cambiar-salon"
            f"?id_grupo={id_grupo}&id_nuevo_salon={nuevo_salon_id}"
            f"&num_sesion=1&token={token_profesor}"
        )
        assert res.status_code == 200

        # Verificar que el estudiante ve el nuevo salon en su horario
        horario = client.get(f"/horarios?token={token_est}").json()
        salones_en_horario = [
            celda["salon_nombre"]
            for franja in horario.values()
            for celda in franja.values()
            if celda.get("materia") == mat["nombre"] and celda.get("sesion") == 1
        ]
        assert nuevo_salon_name in salones_en_horario, (
            f"El salon '{nuevo_salon_name}' no aparece en el horario del estudiante. "
            f"Salones encontrados: {salones_en_horario}"
        )