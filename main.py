from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from routers import api
from logging import getLogger

logger = getLogger(__name__)
logger.setLevel("INFO")

app = FastAPI(
    title="NetShield VPN API",
    version="1.0.0",
)

# CORS: разрешаем запросы с фронтенда. В проде указать конкретный домен.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Заменить на ["http://localhost:5500"] в проде
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем основной роутер API
app.include_router(api.router)

#healthcheck для мониторинга
@app.get("/health")
async def healthcheck():
    return {"status": "ok"}

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Отдаём папку static как статику
app.mount("/static", StaticFiles(directory="static"), name="static")

# Корневой путь отдаёт dashboard.html
@app.get("/")
async def serve_frontend():
    return FileResponse("static/dashboard.html")
