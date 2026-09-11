import httpx
from settings import settings

class AuthServiceClient:
    def __init__(self):
        self.base_url = settings.AUTH_SERVICE_URL  # "http://localhost:8001"
    
    async def login(self, email: str, password: str) -> dict:
        async with httpx.AsyncClient() as client:
            # auth-service ожидает поле 'username', передаем туда email
            response = await client.post(
                f"{self.base_url}/login",  # Убрали префикс /auth/
                json={"username": email, "password": password}
            )
            response.raise_for_status()
            return response.json()
    
    async def register(self, email: str, password: str, name: str) -> dict:
        async with httpx.AsyncClient() as client:
            # Передаем name как username, чтобы соответствовать UserSchema в auth-service
            response = await client.post(
                f"{self.base_url}/register",  # Убрали префикс /auth/
                json={"username": name, "email": email, "password": password}
            )
            response.raise_for_status()
            return response.json()

class BillingServiceClient:
    def __init__(self):
        self.base_url = settings.BILLING_SERVICE_URL  # "http://localhost:8002"
    
    async def get_tariffs(self) -> list:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/tariffs")
            response.raise_for_status()
            return response.json()
    
    async def create_payment(self, user_id: int, tariff_id: int, promo_code: str = "") -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/payments",
                json={"user_id": user_id, "tariff_id": tariff_id, "promo_code": promo_code}
            )
            response.raise_for_status()
            return response.json()

class VpnServiceClient:
    def __init__(self):
        self.base_url = settings.VPN_SERVICE_URL
    
    async def create_user(self, username: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/users",
                json={"username": username, "data_limit": 0, "expire": 0}
            )
            response.raise_for_status()
            return response.json()

    async def delete_user(self, username: str):
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{self.base_url}/users/{username}")
            response.raise_for_status()
            return response.json()

vpn_client = VpnServiceClient()
auth_client = AuthServiceClient()
billing_client = BillingServiceClient()
