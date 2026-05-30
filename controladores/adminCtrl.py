from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from database import ObtenerSes
from servicios.optimizador import OptimizadorAud, ComponenteAlg
from servicios.sesiones import ObtenerSesAct
from modelos.entidades import SesionToken

router = APIRouter()


@router.post("/admin/optimizar-horarios", status_code=200)
def OptimizarInf(
    sesion: SesionToken = Depends(ObtenerSesAct),
    session: Session = Depends(ObtenerSes)
):
    if sesion.rol != "Administrador":
        raise HTTPException(
            status_code=403,
            detail="Solo los administradores pueden ejecutar la optimización de horarios."
        )
    return OptimizadorAud(ComponenteAlg()).ejecutar(session)