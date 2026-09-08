from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from db_provider import get_db
from models import Device
#from schemas import 
from settings import settings
from logging import getLogger
import qrcode
import io

logger = getLogger(__name__)
logger.setLevel("INFO")

router = APIRouter(prefix="/qr", tags=["qr"])

@router.get("/qr/{device_id}.png")
async def get_qr_image(device_id: int, db: AsyncSession = Depends(get_db)):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="QR Code not found")
    
    # Кодируем текст конфигурации (config_text) в QR-код
    img = qrcode.make(device.config_text)
    
    # Сохраняем в буфер памяти
    buffer = io.BytesIO()
    img.save(stream=buffer, kind="PNG")
    buffer.seek(0)
    
    # Отдаем чистый PNG-файл
    return StreamingResponse(buffer, media_type="image/png")
