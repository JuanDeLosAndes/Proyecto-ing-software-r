from abc import ABC, abstractmethod
from sqlmodel import Session


# ── Open/Closed (O): abierto para extensión via herencia, cerrado para modificación ──

class IOptimizador(ABC):
    @abstractmethod
    def ejecutar(self, session: Session) -> dict: pass


class ComponenteAlg(IOptimizador):
    def ejecutar(self, session: Session) -> dict:
        from algoritmoGen import EjecutarAlg
        return EjecutarAlg(session)


# ── Decorator (Estructural): añade auditoría sin tocar el componente base ──

class OptimizadorDec(IOptimizador):
    def __init__(self, base: IOptimizador):
        self._base = base

    def ejecutar(self, session: Session) -> dict:
        return self._base.ejecutar(session)


class OptimizadorAud(OptimizadorDec):
    def ejecutar(self, session: Session) -> dict:
        resultado = super().ejecutar(session)
        return resultado