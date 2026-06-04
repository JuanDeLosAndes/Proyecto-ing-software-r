import os
import base64
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from database import ObtenerSes
from modelos.entidades import ConfigFront, Usuario, Rol
from modelos.esquemas import EsquemaConfigUp

router = APIRouter()

IMG_DIR = os.path.join("static", "img")


def _guardar_imagen_base64(data_url: str, slot: int) -> str:

    if not data_url or not data_url.strip():
        return data_url

    url = data_url.strip()

    if url.startswith("http://") or url.startswith("https://") or url.startswith("/static/"):
        return url

    if url.startswith("data:image/"):
        try:
            header, encoded = url.split(",", 1)
            ext = "jpg"
            if "png"  in header: ext = "png"
            elif "gif"  in header: ext = "gif"
            elif "webp" in header: ext = "webp"

            os.makedirs(IMG_DIR, exist_ok=True)
            nombre = f"config_img_{slot}.{ext}"
            ruta   = os.path.join(IMG_DIR, nombre)

            with open(ruta, "wb") as f:
                f.write(base64.b64decode(encoded))

            return f"/static/img/{nombre}"
        except Exception:
            return url

    return url


@router.get("/front/config", status_code=200, response_model=ConfigFront)
def ObtenerConf(session: Session = Depends(ObtenerSes)):
    conf = session.exec(select(ConfigFront)).first()
    if not conf:
        return ConfigFront(
            id=0,
            mensaje_1="Sistema de Asignación de Salones",
            mensaje_2="Universidad Católica de Colombia",
            mensaje_3="Acceso institucional seguro",
            mensaje_4="Conectando a base de datos...",
            url_img_1="", url_img_2="", url_img_3=""
        )
    return conf


@router.post("/front/config", status_code=200)
def GuardarConf(data: EsquemaConfigUp, session: Session = Depends(ObtenerSes)):
    us = session.exec(select(Usuario).where(Usuario.codigo == data.codigo_admin)).first()
    if not us:
        raise HTTPException(status_code=404, detail="Administrador no encontrado.")

    rol = session.get(Rol, us.id_rol)
    if not rol or rol.nombre_rol != "Administrador":
        raise HTTPException(status_code=403, detail="Operación exclusiva del Administrador.")

    img1 = _guardar_imagen_base64(data.img_1, 1) if data.img_1 is not None else None
    img2 = _guardar_imagen_base64(data.img_2, 2) if data.img_2 is not None else None
    img3 = _guardar_imagen_base64(data.img_3, 3) if data.img_3 is not None else None

    conf = session.exec(select(ConfigFront)).first()
    if not conf:
        conf = ConfigFront(
            mensaje_1=data.msg_1 or "", mensaje_2=data.msg_2 or "",
            mensaje_3=data.msg_3 or "", mensaje_4=data.msg_4 or "",
            url_img_1=img1 or "", url_img_2=img2 or "", url_img_3=img3 or ""
        )
    else:
        if data.msg_1 is not None: conf.mensaje_1 = data.msg_1
        if data.msg_2 is not None: conf.mensaje_2 = data.msg_2
        if data.msg_3 is not None: conf.mensaje_3 = data.msg_3
        if data.msg_4 is not None: conf.mensaje_4 = data.msg_4
        if img1 is not None: conf.url_img_1 = img1
        if img2 is not None: conf.url_img_2 = img2
        if img3 is not None: conf.url_img_3 = img3

    session.add(conf)
    session.commit()
    return {"mensaje": "Configuración actualizada correctamente."}