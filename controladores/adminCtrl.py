from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from database import ObtenerSes
from servicios.optimizador import OptimizadorAud, ComponenteAlg
from servicios.sesiones import ObtenerSesAct
from modelos.entidades import SesionToken

router = APIRouter()


