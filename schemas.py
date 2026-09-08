from pydantic import BaseModel, Field
from datetime import datetime

class AuthRequest(BaseModel):
    email: str
    password: str 
    
class AuthResponse(BaseModel):
    access_token: str
    expired_in: int
    user_id: int

class TariffResponse(BaseModel):
    tariff_id: int
    name: str
    price: float
    currency: str
    duration_months: int
    max_devices: int
    features: str

class PaymentRequest(BaseModel):
    tariff_id: int
    promo_code: str

class PaymentResponse(BaseModel):
    payment_id: str
    amount: float
    redirect_url: str

class ProfileResponse(BaseModel):
    email: str
    subscription: dict

class DevicesResponse(BaseModel):
    devices_list: list

class DevicesCreateRequest(BaseModel):
    name: str
    country_code: str

class DeviceCreateResponse(BaseModel):
    id: int
    name: str
    config_text: str
    qr_code_url: str
