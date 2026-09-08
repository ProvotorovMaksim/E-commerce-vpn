from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db_provider import get_db
# ВАЖНО: Импортируем таблицу ассоциации для Many-to-Many запросов
from models import Device, Client, client_device_association
from schemas import (
    DeviceCreateResponse as DeviceConfigResponse, 
    AuthResponse, TariffResponse, PaymentResponse, 
    ProfileResponse, DevicesResponse, DeviceCreateRequest
)
from settings import settings
from logging import getLogger
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime

logger = getLogger(__name__)
logger.setLevel("INFO")

security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/api", tags=["api"])

async def verify_token_optional(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    path = request.url.path
    if any(path.startswith(ncp) for ncp in settings.NO_CREDENTIALS_PATHS):
        return None
    
    if not credentials:
        raise HTTPException(status_code=401, detail="Отсутствует заголовок авторизации")
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Некорректный токен: отсутствует 'sub'")
        return int(user_id)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Срок действия токена истек")
    except JWTError as e:
        logger.error(f"Ошибка валидации JWT: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Недействительный токен: {str(e)}")

@router.post("/login", response_model=AuthResponse)
async def login(email: str, password: str):
    pass

@router.get("/tariffs", response_model=TariffResponse)
async def get_tariffs():
    pass

@router.post("/payments", response_model=PaymentResponse)
async def create_payment(tariff_id: int, promo_code: str):
    pass

@router.get("/user/profile", response_model=ProfileResponse)
async def show_user_profile(user_id: int = Depends(verify_token_optional), db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    
    subscription = {"status": "active", "tariff_name": "1 Месяц"} 
    
    return ProfileResponse(
        email=client.email,
        subscription=subscription
    )

@router.get("/vpn/devices", response_model=DevicesResponse)
async def get_devices(user_id: int = Depends(verify_token_optional), db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # SQLAlchemy автоматически подгрузит устройства через relationship
    return DevicesResponse(devices_list=client.devices)

async def grant_vpn_access_task(device_id: int, config_text: str):
    logger.info(f"Фоновая задача: Предоставление доступа для устройства {device_id}")
    pass

@router.post("/vpn/device", response_model=DeviceConfigResponse)
async def create_device(
    req: DeviceCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(verify_token_optional), 
    db: AsyncSession = Depends(get_db)
):
    client = await db.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    fake_config = f"[Interface]\nPrivateKey=generated_key_for_user_{user_id}...\nAddress=10.0.0.x/32"
    
    # Создаем устройство
    new_device = Device(
        name=req.name,
        country_code=req.country_code,
        config_text=fake_config,
        status="pending"
    )
    
    # Привязываем устройство к клиенту через relationship (Many-to-Many)
    # SQLAlchemy сама запишет связь в таблицу client_devices при коммите
    client.devices.append(new_device)
    
    await db.commit()
    await db.refresh(new_device)

    background_tasks.add_task(grant_vpn_access_task, new_device.id, new_device.config_text)

    qr_url = f"https://api.netshield.com/qr/{new_device.id}.png"
    
    return {
        "id": new_device.id,
        "name": new_device.name,
        "config_text": new_device.config_text,
    }

@router.delete("/vpn/devices/{device_id}")
async def delete_device(
    device_id: int, 
    user_id: int = Depends(verify_token_optional), 
    db: AsyncSession = Depends(get_db)
):
    # Безопасный запрос: ищем устройство ТОЛЬКО если оно связано с этим client_id в таблице ассоциации
    query = (
        select(Device)
        .join(client_device_association)
        .where(
            Device.id == device_id,
            client_device_association.c.client_id == user_id
        )
    )
    result = await db.execute(query)
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=403, detail="У вас нет прав на удаление этого устройства или оно не найдено")

    await db.delete(device)
    await db.commit()

    return {"status": "success", "message": f"Device {device_id} successfully deleted"}

@router.get("/vpn/device/{device_id}", response_model=DeviceConfigResponse)
async def get_device_config(
    device_id: int, 
    user_id: int = Depends(verify_token_optional), 
    db: AsyncSession = Depends(get_db)
):
    # Безопасный запрос: проверяем принадлежность через таблицу ассоциации
    query = (
        select(Device)
        .join(client_device_association)
        .where(
            Device.id == device_id,
            client_device_association.c.client_id == user_id
        )
    )
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    qr_url = f"https://api.netshield.com/qr/{device_id}.png"
    
    return {
        "id": device.id,
        "name": device.name,
        "config_text": device.config_text,
    }
