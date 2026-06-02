from abc import ABC, abstractmethod
from typing import List
from sqlmodel import Session, select, func
from modelos.entidades import Grupo, Inscripcion


class IObservador(ABC):
    @abstractmethod
    def actualizar(self, evento: str, datos: dict) -> None: pass


class GestorEv:
    def __init__(self):
        self._obs: List[IObservador] = []

    def suscribir(self, obs: IObservador):
        if obs not in self._obs:
            self._obs.append(obs)

    def NotificarTod(self, evento: str, datos: dict):
        for obs in self._obs:
            obs.actualizar(evento, datos)


class ObservadorCon(IObservador):

    def actualizar(self, evento: str, datos: dict) -> None:
        pass


class IEstrategiaAs(ABC):
    @abstractmethod
    def SeleccionarGrup(self, grupos: list, session: Session) -> Grupo: pass


class EstrategiaVac(IEstrategiaAs):
    def SeleccionarGrup(self, grupos: list, session: Session) -> Grupo:
        return min(
            grupos,
            key=lambda g: session.exec(
                select(func.count(Inscripcion.id)).where(Inscripcion.id_grupo == g.id)
            ).one()
        )


class ContextoIns:
    def __init__(self, estrategia: IEstrategiaAs):
        self._estrategia = estrategia

    def seleccionar(self, grupos: list, session: Session) -> Grupo:
        return self._estrategia.SeleccionarGrup(grupos, session)