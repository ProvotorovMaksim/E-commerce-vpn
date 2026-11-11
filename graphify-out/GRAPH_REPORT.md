# Graph Report - E-commerce-vpn  (2026-11-12)

## Corpus Check
- В структурный анализ включено файлов исходного кода: 12. Сторонние зависимости, документация и файлы окружения исключены.

## Summary
- 98 nodes · 177 edges · 8 communities (5 shown, 3 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 17 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- env.py
- api.py
- models.py
- services.py
- main.py
- sqlalchemy
- verify_token_optional

## God Nodes (most connected - your core abstractions)
1. `Client` - 8 edges
2. `create_device()` - 7 edges
3. `Device` - 6 edges
4. `login()` - 6 edges
5. `register()` - 6 edges
6. `AuthResponse` - 5 edges
7. `Base` - 5 edges
8. `delete_device()` - 5 edges
9. `get_devices()` - 5 edges
10. `show_user_profile()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `login()` --uses--> `AuthResponse`  [INFERRED]
  routers/api.py → schemas.py
- `register()` --uses--> `AuthResponse`  [INFERRED]
  routers/api.py → schemas.py
- `create_device()` --uses--> `DeviceCreateRequest`  [INFERRED]
  routers/api.py → schemas.py
- `get_devices()` --uses--> `DevicesResponse`  [INFERRED]
  routers/api.py → schemas.py
- `login()` --uses--> `LoginRequest`  [INFERRED]
  routers/api.py → schemas.py

## Import Cycles
- None detected.

## Communities (8 total, 3 thin omitted)

### Community 0 - "env.py"
Cohesion: 0.12
Nodes (6): do_run_migrations(), run_async_migrations(), run_migrations_online(), get_db(), Settings, Config

### Community 1 - "api.py"
Cohesion: 0.22
Nodes (12): create_payment(), get_tariffs(), AuthResponse, DeviceCreateRequest, DeviceCreateResponse, DevicesResponse, LoginRequest, PaymentRequest (+4 more)

### Community 2 - "models.py"
Cohesion: 0.19
Nodes (10): Base, Client, Device, create_device(), delete_device(), get_device_config(), get_devices(), login() (+2 more)

### Community 3 - "services.py"
Cohesion: 0.15
Nodes (3): AuthServiceClient, BillingServiceClient, VpnServiceClient

### Community 5 - "sqlalchemy"
Cohesion: 0.31
Nodes (3): upgrade(), downgrade(), upgrade()

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Are the 5 inferred relationships involving `Client` (e.g. with `create_device()` and `get_devices()`) actually correct?**
  _`Client` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `env.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11904761904761904 - nodes in this community are weakly interconnected._
- **Are the 3 inferred relationships involving `create_device()` (e.g. with `Client` and `Device`) actually correct?**
  _`create_device()` has 3 INFERRED edges - model-reasoned connections that need verification._