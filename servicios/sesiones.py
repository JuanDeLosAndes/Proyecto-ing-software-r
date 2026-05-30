import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends, Query
from sqlmodel import Session, select
from modelos.entidades import SesionToken
from database import ObtenerSes


class GestorSesion:
    DURACION_HORAS = 8

    @staticmethod
    def CrearSesion(session: Session, idUsuario: int, codigo: str, rol: str) -> str:
        token = str(uuid.uuid4())
        ahora = datetime.now(timezone.utc)
        ses = SesionToken(
            token=token,
            id_usuario=idUsuario,
            codigo_usuario=codigo,
            rol=rol,
            creado_en=ahora.isoformat(),
            expira_en=(ahora + timedelta(hours=GestorSesion.DURACION_HORAS)).isoformat(),
            activo=True
        )
        session.add(ses)
        session.commit()
        return token

    @staticmethod
    def ValidarToken(session: Session, token: str):
        ses = session.exec(
            select(SesionToken).where(SesionToken.token == token, SesionToken.activo == True)
        ).first()
        if not ses:
            return None
        try:
            expiry = datetime.fromisoformat(ses.expira_en)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expiry:
                ses.activo = False
                session.add(ses)
                session.commit()
                return None
        except Exception:
            return None
        return ses

    @staticmethod
    def CerrarSesion(session: Session, token: str):
        ses = session.exec(select(SesionToken).where(SesionToken.token == token)).first()
        if ses:
            ses.activo = False
            session.add(ses)
            session.commit()


def ObtenerSesAct(
    token: str = Query(..., description="Token UUID de sesión activa"),
    session: Session = Depends(ObtenerSes)
) -> SesionToken:
    ses = GestorSesion.ValidarToken(session, token)
    if not ses:
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida o expirada. Inicie sesión nuevamente."
        )
    return ses