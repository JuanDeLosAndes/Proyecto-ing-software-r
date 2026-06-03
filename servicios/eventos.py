from abc import ABC, abstractmethod
from typing import List
from sqlmodel import Session, select, func
from modelos.entidades import Grupo, Inscripcion

import logging

logger = logging.getLogger(__name__)
class IObservador(ABC):
    """Interfaz minima: un solo metodo. ISP cumplido."""
    @abstractmethod
    def actualizar(self, evento: str, datos: dict) -> None: pass


class GestorEv:
    """
    SRP: solo gestiona suscripciones y notificaciones.
    OCP: se extiende agregando observadores, sin modificar esta clase.
    """
    def __init__(self):
        self._obs: List[IObservador] = []

    def suscribir(self, obs: IObservador) -> None:
        if obs not in self._obs:
            self._obs.append(obs)

    def NotificarTod(self, evento: str, datos: dict) -> None:
        for obs in self._obs:
            obs.actualizar(evento, datos)


class ObservadorCon(IObservador):
    """
    LSP corregido: implementa el contrato del observador registrando el evento.
    Antes estaba vacio (pass), lo que violaba el contrato implicito.
    """
    def actualizar(self, evento: str, datos: dict) -> None:
        logger.info(
            "[ObservadorCon] evento=%s grupo_id=%s nuevo_salon=%s sesion=%s",
            evento,
            datos.get("grupo_id"),
            datos.get("nuevo_salon_id"),
            datos.get("num_sesion"),
        )


class IEstrategiaAs(ABC):
    """ISP: interfaz minima con un solo metodo."""
    @abstractmethod
    def SeleccionarGrup(self, grupos: list, session: Session) -> Grupo: pass


class EstrategiaVac(IEstrategiaAs):
    """Estrategia: elige el grupo con menos inscritos."""
    def SeleccionarGrup(self, grupos: list, session: Session) -> Grupo:
        return min(
            grupos,
            key=lambda g: session.exec(
                select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)
            ).one()
        )


class ContextoIns:
    """
    DIP: depende de IEstrategiaAs (abstraccion), no de EstrategiaVac (concreto).
    """
    def __init__(self, estrategia: IEstrategiaAs):
        self._estrategia = estrategia

    def seleccionar(self, grupos: list, session: Session) -> Grupo:
        return self._estrategia.SeleccionarGrup(grupos, session)


_gestor_global = GestorEv()
_gestor_global.suscribir(ObservadorCon())


def obtener_gestor() -> GestorEv:
    """
    DIP: los controladores dependen de esta funcion (abstraccion),
    no de GestorEv ni ObservadorCon directamente.
    """
    return _gestor_global