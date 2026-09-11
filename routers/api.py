import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db_provider import get_db
from models import Device, Client, client_device_association
from schemas import (
    DeviceCreateResponse as DeviceConfigResponse, 
    AuthResponse, TariffResponse, PaymentResponse, 
    ProfileResponse, DevicesResponse, DeviceCreateRequest,
    LoginRequest, RegisterRequest, PaymentRequest # Добавлен PaymentRequest
)
from settings import settings
from logging import getLogger
from jose import jwt, JWTError, ExpiredSignatureError
from services import auth_client, billing_client, vpn_client

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

# --- AUTH SERVICE ---

@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. Получаем ответ от auth-service (он содержит только access_token)
    auth_response = await auth_client.login(req.email, req.password)
    access_token = auth_response.get("access_token")
    
    if not access_token:
        raise HTTPException(status_code=500, detail="Auth-service не вернул токен")

    # 2. Декодируем токен прямо здесь, на шлюзе, чтобы извлечь ID
    try:
        payload = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Извлекаем 'sub' (который там строка) и конвертируем в int
        user_id = int(payload.get("sub")) # type: ignore
    except Exception as e:
        logger.error(f"Не удалось декодировать токен от auth-service: {e}")
        raise HTTPException(status_code=500, detail="Ошибка валидации токена")

    # 3. Синхронизируем БД шлюза. Если клиента нет, создаем его.
    client = await db.get(Client, user_id)
    if not client:
        client = Client(client_id=user_id, email=req.email)
        db.add(client)
        await db.commit()

    # 4. Возвращаем фронтенду токен и его собственный ID
    return AuthResponse(
        access_token=access_token,
        expired_in=auth_response.get("expired_in", 3600),
        user_id=user_id
    )

@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # 1. Отправляем данные на регистрацию
    auth_response = await auth_client.register(req.email, req.password, req.name)
    access_token = auth_response.get("access_token")
    user_id = -1
    
    if not access_token:
        raise HTTPException(status_code=500, detail="Auth-service не вернул токен")

    # 2. Декодируем токен и извлекаем int(user_id) из строкового 'sub'
    try:
        payload = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub")) # type: ignore
    except Exception as e:
        logger.error(f"Не удалось декодировать токен от auth-service: {e}")
        raise HTTPException(status_code=500, detail="Ошибка валидации токена")

    # 3. Создаем запись в БД шлюза, используя извлеченный ID
    new_client = Client(client_id=user_id, email=req.email)
    db.add(new_client)
    await db.commit()
    
    # 4. Возвращаем ответ
    return AuthResponse(
        access_token=access_token,
        expired_in=auth_response.get("expired_in", 3600),
        user_id=user_id
    )

# --- BILLING SERVICE ---

@router.get("/tariffs", response_model=list[TariffResponse])
async def get_tariffs():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.BILLING_SERVICE_URL}/tariffs")
        response.raise_for_status()
        return response.json()

@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    req: PaymentRequest, 
    user_id: int = Depends(verify_token_optional)
):
    # Передаем user_id из токена, чтобы биллинг знал, кто платит
    payload = req.model_dump()
    payload["user_id"] = user_id 
    
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{settings.BILLING_SERVICE_URL}/payments", json=payload)
        response.raise_for_status()
        return response.json()

# --- USER PROFILE ---

@router.get("/user/profile", response_model=ProfileResponse)
async def show_user_profile(user_id: int = Depends(verify_token_optional), db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # В реальном проекте здесь будет запрос к billing_service.get_subscription(user_id)
    subscription = {"status": "active", "tariff_name": "1 Месяц"} 
    
    return ProfileResponse(email=client.email, subscription=subscription)

# --- VPN DEVICES ---

@router.get("/vpn/devices", response_model=DevicesResponse)
async def get_devices(user_id: int = Depends(verify_token_optional), db: AsyncSession = Depends(get_db)):
    query = select(Client).options(selectinload(Client.devices)).where(Client.client_id == user_id)
    result = await db.execute(query)
    client = result.scalar_one_or_none()
    
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Точечное исправление: явно преобразуем объекты SQLAlchemy в словари для корректной сериализации Pydantic
    devices_data = [
        {
            "id": d.id,
            "name": d.name,
            "config_text": d.config_text,
            "status": d.status,
            "country_code": d.country_code
        }
        for d in client.devices
    ]
    
    return DevicesResponse(devices_list=devices_data)

async def grant_vpn_access_task(device_id: int, config_text: str):
    logger.info(f"Фоновая задача: Предоставление доступа для устройства {device_id}")
    # Здесь будет вызов воркера или скрипта настройки WireGuard

@router.post("/vpn/device", response_model=DeviceConfigResponse)
async def create_device(
    req: DeviceCreateRequest,
    user_id: int = Depends(verify_token_optional), 
    db: AsyncSession = Depends(get_db)
):
    client = await db.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    # 1. Генерируем уникальное имя пользователя для Marzban (например, user_1_device_5)
    marzban_username = f"user_{user_id}_dev_{req.name.replace(' ', '_')}"

    try:
        # 2. Создаем пользователя в Marzban через наш новый сервис
        vpn_response = await vpn_client.create_user(username=marzban_username)
        config_text = vpn_response["subscription_url"] # Используем ссылку на подписку Marzban как конфиг
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка при создании пользователя в VPN сервисе: {e.response.text}")
        raise HTTPException(status_code=500, detail="Не удалось выделить ресурсы VPN")

    # 3. Создаем запись в БД шлюза
    new_device = Device(
        name=req.name,
        country_code=req.country_code,
        config_text=config_text, # Здесь теперь лежит реальная ссылка на подписку
        status="active"
    )
    
    client.devices.append(new_device)
    await db.commit()
    await db.refresh(new_device)

    return {
        "id": new_device.id,
        "name": new_device.name,
        "config_text": new_device.config_text,
        "status": new_device.status,
        "country_code": new_device.country_code
    }

@router.delete("/vpn/devices/{device_id}")
async def delete_device(
    device_id: int, 
    user_id: int = Depends(verify_token_optional), 
    db: AsyncSession = Depends(get_db)
):
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

    # 1. Пытаемся удалить пользователя из Marzban (даже если устройство в БД битое, чистим Marzban)
    # Извлекаем username из config_text, если там сохранена ссылка, или формируем его заново
    # Для простоты, если config_text - это URL, мы можем просто передать device.name, но лучше хранить marzban_username в модели Device.
    # Если marzban_username не хранится отдельно, можно пропустить этот шаг или распарсить URL.
    # Допустим, мы храним его, или передаем имя устройства как часть имени:
    marzban_username = f"user_{user_id}_dev_{device.name.replace(' ', '_')}"
    
    try:
        await vpn_client.delete_user(username=marzban_username)
    except Exception as e:
        logger.warning(f"Не удалось удалить пользователя {marzban_username} из Marzban: {e}")

    # 2. Удаляем из нашей БД
    await db.delete(device)
    await db.commit()

    return {"status": "success", "message": f"Device {device_id} successfully deleted"}

@router.get("/vpn/device/{device_id}", response_model=DeviceConfigResponse)
async def get_device_config(
    device_id: int, 
    user_id: int = Depends(verify_token_optional), 
    db: AsyncSession = Depends(get_db)
):
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
    
    return {
        "id": device.id,
        "name": device.name,
        "config_text": device.config_text,
        "status": device.status,
        "country_code": device.country_code
    }
