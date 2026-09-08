from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from db_provider import async_session, get_db
from models import Device, Client
from schemas import DeviceCreateResponse as DeviceConfigResponse, AuthResponse, TariffResponse, PaymentResponse, ProfileResponse, DevicesResponse
from settings import settings
from logging import getLogger
from jose import jwt, JWTError, ExpiredSignatureError
import json
from datetime import datetime

logger = getLogger(__name__)
logger.setLevel("INFO")

security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/api", tags=["api"])

async def verify_token_optional(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Проверяет токен, но только если путь не начинается с auth/"""
    path = request.url.path
    logger.info(f"Проверка токена для пути: {path}")
    
    # Для auth-эндпоинтов токен не требуется
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
        return str(user_id)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Срок действия токена истек")
    except JWTError as e:
        logger.error(f"Ошибка валидации JWT: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Недействительный токен: {str(e)}")

@router.post("/login", response_model=AuthResponse)
async def login(email: str, password: str):
    #Авторизация через auth-service
    pass

@router.get("/tariffs", response_model=TariffResponse)
async def get_tariffs():
    #Получение тарифов в Billing
    pass

@router.post("/payments", response_model=PaymentResponse)
async def create_payment(tariff_id: int, promo_code: str):
    #Создание платежа в Billing
    pass

@router.get("/user/profile", response_model=ProfileResponse)
async def show_user_profile(user_id: str = Depends(verify_token_optional), db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=401, detail="Client not found")
    return
    subscription #Обращаемся в Billing
    Response = ProfileResponse(
        email = client.email,
        subscription=subscription
    )
    return Response

@router.get("/vpn/devices", response_model=DevicesResponse)
async def get_devices(user_id: str = Depends(verify_token_optional), db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=401, detail="Client not found")
    
    device_ids = json.loads(client.device_ids)
    if not device_ids:
        return DevicesResponse(devices_list=[])

    query = select(Device).where(Device.id.in_(device_ids))
    result = await db.execute(query)
    devices = result.scalars().all()

    Response = DevicesResponse(devices_list=list(devices))

    return Response

# Заглушка функции для фоновой задачи (например, отправка конфига на VPN-сервер / Bash-скрипт)
async def grant_vpn_access_task(device_id: int, config_text: str):
    logger.info(f"Фоновая задача: Предоставление доступа для устройства {device_id}")
    # Здесь логика взаимодействия с вашим WireGuard/Xray сервером
    pass

@router.post("/vpn/device", response_model=DeviceConfigResponse)
async def create_device(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_token_optional), 
    db: AsyncSession = Depends(get_db)
):
    # 1. Проверяем существование клиента
    client = await db.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=401, detail="Client not found")

    # 2. Генерируем данные для нового устройства (заглушка WireGuard конфига)
    # В реальном коде здесь должна быть ваша функция генерации ключей
    fake_config = f"[Interface]\nPrivateKey=generated_key_for_user_{user_id}...\nAddress=10.0.0.x/32"
    
    # 3. Создаем запись в таблице devices
    new_device = Device(
        name="New Device",  # Можно принимать имя из схемы запроса (например, DeviceCreate schema)
        config_text=fake_config,
        qr_code_url=""  # Заполнится динамически или останется пустой, если эндпоинт QR внешний
    )
    db.add(new_device)
    await db.flush()  # Получаем автоматически сгенерированный new_device.id из БД до коммита
    
    # Заполняем qr_code_url на основе полученного ID
    new_device.qr_code_url = f"https://api.netshield.com/qr/{new_device.id}.png"

    # 4. Обновляем список device_ids у Client
    try:
        current_ids = json.loads(client.device_ids)
        if not isinstance(current_ids, list):
            current_ids = []
    except (json.JSONDecodeError, TypeError):
        current_ids = []

    current_ids.append(new_device.id)
    client.device_ids = json.dumps(current_ids)
    client.changed_at = datetime.now()  # Обновляем время изменения

    # Сохраняем всё в БД одной транзакцией
    await db.commit()
    await db.refresh(new_device)

    # 5. Добавляем фоновую задачу (Background Task)
    background_tasks.add_task(grant_vpn_access_task, new_device.id, new_device.config_text)

    # Возвращаем созданное устройство фронтенду
    return {
        "id": new_device.id,
        "name": new_device.name,
        "config_text": new_device.config_text,
        "qr_code_url": new_device.qr_code_url
    }


@router.delete("/vpn/devices/{device_id}")
async def delete_device(
    device_id: int, 
    user_id: str = Depends(verify_token_optional), 
    db: AsyncSession = Depends(get_db)
):
    # 1. Проверяем существование клиента
    client = await db.get(Client, user_id)
    if client is None:
        raise HTTPException(status_code=401, detail="Client not found")

    # 2. Парсим его устройства и проверяем, принадлежит ли ему удаляемый device_id
    try:
        current_ids = json.loads(client.device_ids)
    except (json.JSONDecodeError, TypeError):
        current_ids = []

    if device_id not in current_ids:
        raise HTTPException(status_code=403, detail="У вас нет прав на удаление этого устройства")

    # 3. Удаляем устройство из таблицы devices
    device = await db.get(Device, device_id)
    if device:
        await db.delete(device)

    # 4. Удаляем ID из списка пользователя и сохраняем изменения
    current_ids.remove(device_id)
    client.device_ids = json.dumps(current_ids)
    client.changed_at = datetime.now()

    await db.commit()

    return {"status": "success", "message": f"Device {device_id} successfully deleted"}

@router.get("/device/{device_id}", response_model=DeviceConfigResponse)
async def get_device_config(device_id: int, db: AsyncSession = Depends(get_db)):
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Формируем динамическую ссылку на эндпоинт генерации QR-кода
    qr_url = f"https://api.netshield.com/qr/{device_id}.png"
    
    return {
        "id": device.id,
        "name": device.name,
        "config_text": device.config_text,
        "qr_code_url": qr_url
    }
