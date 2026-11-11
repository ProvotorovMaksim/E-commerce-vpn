# E-commerce VPN — API личного кабинета

## Назначение проекта

Объединяет регистрацию, оплату и выдачу VPN-конфигураций для клиентского интерфейса.

## Функциональность

Регистрация и вход через сервис авторизации, тарифы и создание платежа через биллинг, профиль, создание, получение и удаление VPN-устройств.

## Архитектура

`routers/api.py` задаёт сценарии, `services.py` содержит HTTP-клиенты авторизации, биллинга и VPN-провайдера. PostgreSQL хранит клиентов, устройства и их связи. В коде создания устройства используется FastAPI BackgroundTasks. Внешнего брокера в репозитории нет.

### С чего начать чтение кода

- [`routers/api.py`](routers/api.py)
- [`services.py`](services.py)
- [`models.py`](models.py)

[Граф связей Graphify](graphify-out/graph.html) · [Отчёт Graphify](graphify-out/GRAPH_REPORT.md)

Для поиска по графу из корня репозитория выполните `graphify god-nodes --top 5` или `graphify query "имя функции или модуля"`.

## Технологический стек

Python 3.13, FastAPI, Pydantic, HTTPX, python-jose, SQLAlchemy, asyncpg, PostgreSQL, Alembic, Docker Compose.

## Технические решения

Защищённые маршруты извлекают `sub` из JWT. Поиск и удаление устройства учитывают связь с владельцем. Профиль возвращает демонстрационные данные подписки. Фоновая функция выдачи доступа только пишет в лог, а конфигурация устройства запрашивается у провайдера в основном сценарии.

## Запуск проекта

Задайте `DATABASE_URL`, `DATABASE_DRIVER`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `JWT_SECRET_KEY`, `ALGORITHM`, `AUTH_SERVICE_URL`, `BILLING_SERVICE_URL`, `VPN_SERVICE_URL`. Проверьте обязательные поля Settings и их передачу в `compose.yml`. Сеть `saas_network` и соседние сервисы должны быть доступны из контейнера. Запуск — `docker compose up --build`. `entrypoint.sh` выполняет `alembic upgrade head` до запуска приложения.

## Примеры API

`GET /health`, `POST /api/login`, `POST /api/register`, `GET /api/tariffs`, `POST /api/payments`, `GET /api/user/profile`, `GET /api/vpn/devices`, `POST /api/vpn/device`, `GET /api/vpn/device/{device_id}`, `DELETE /api/vpn/devices/{device_id}`.

```bash
curl -i http://localhost:8000/health
```

## Тестирование

В исходниках проекта отдельный набор автоматических тестов не обнаружен. Для ручной проверки используйте сценарий из раздела «Примеры API» на тестовой инфраструктуре.

## Ограничения и дальнейшее развитие

Нужны получение реального статуса подписки, контрактные тесты внешних клиентов и восстановление после частичного сбоя.

## Мой вклад

TODO — описать свою роль, реализованные компоненты и принятые технические решения.

[Технический обзор проекта](PROJECT_REVIEW.md)
