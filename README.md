# Leads Backend - два мікросервіси для обробки лідів

## Архітектура

```
┌─────────────┐   POST /lead    ┌──────────────┐
│   Landing   │ ──────────────► │   landings   │ :8001
│   (client)  │                 │   service    │
└─────────────┘                 └──────┬───────┘
                                       │ LPUSH
                                       ▼
                                  ┌─────────┐
                                  │  Redis  │
                                  │  Queue  │
                                  └────┬────┘
                                       │ BRPOP
                                       ▼
┌─────────────┐   GET /leads    ┌──────────────┐
│   Admin /   │ ◄────────────── │     core     │ :8002
│   Dashboard │                 │   service    │
└─────────────┘                 └──────┬───────┘
                                       │
                                       ▼
                                ┌─────────────┐
                                │ PostgreSQL  │
                                └─────────────┘
```

Два незалежні FastAPI-сервіси спілкуються **тільки через Redis**.  
Спільний код (моделі, JWT, БД, Redis) - в пакеті `shared/`.

---

## Структура проєкту

```
.
├── shared/                  # Спільний код
│   ├── models.py            # SQLAlchemy моделі: leads, offers, affiliates
│   ├── database.py          # Async engine + сесія
│   ├── jwt_helper.py        # JWT encode/decode/dependency
│   ├── redis_client.py      # Redis клієнт, константи черги
│   └── alembic/             # Міграції БД
│       └── versions/
│           └── 0001_initial.py
├── landings/                # Сервіс 1 — прийом лідів
│   ├── main.py
│   ├── Dockerfile
│   └── app/
│       ├── schemas.py       # LeadIn, LeadResponse (Pydantic)
│       └── api/
│           └── routes.py    # POST /lead
├── core/                    # Сервіс 2 — обробка + аналітика
│   ├── main.py
│   ├── Dockerfile
│   └── app/
│       ├── schemas.py       # LeadsResponse, GroupByDate/Offer
│       ├── worker.py        # Фоновий воркер Redis → PostgreSQL
│       └── api/
│           └── routes.py    # GET /leads
├── tests/
│   ├── test_jwt.py
│   ├── test_landings.py
│   ├── test_worker.py
│   └── test_core_leads.py
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
└── pytest.ini
```

---

## Швидкий старт

### 1. Клонуємо та налаштовуємо оточення

```bash
git clone <repo>
cd <repo>
```

### 2. Запуск через Docker Compose

```bash
docker-compose up --build
```

Після запуску:
- **landings** → http://localhost:8001/docs
- **core** → http://localhost:8002/docs
- PostgreSQL → `localhost:5432`
- Redis → `localhost:6379`

### 3. Застосування міграцій

Міграції застосовуються **вручну** після першого запуску БД:

```bash
# З хоста (потрібен asyncpg локально)
DATABASE_URL=postgresql+asyncpg://leads_user:leads_pass@localhost:5432/leads_db \
  alembic upgrade head

# Або через docker exec
docker-compose exec landings sh -c \
  "DATABASE_URL=postgresql+asyncpg://leads_user:leads_pass@postgres:5432/leads_db \
   alembic upgrade head"
```

Міграція також створює seed-дані:
- affiliates: id=1 "Affiliate One", id=2 "Affiliate Two"
- offers: id=1 "Offer Alpha", id=2 "Offer Beta"

---

## Локальна розробка (без Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Запустити PostgreSQL та Redis локально, потім:
export DATABASE_URL=postgresql+asyncpg://leads_user:leads_pass@localhost:5432/leads_db
export REDIS_URL=redis://localhost:6379
export JWT_SECRET=dev-secret

# landings
uvicorn landings.main:app --port 8001 --reload

# core (в іншому терміналі)
uvicorn core.main:app --port 8002 --reload
```

---

## Використання API

### Отримати Bearer токен

Через Docker (після `docker-compose up`):
```bash
docker-compose exec landings python -c \
  "from shared.jwt_helper import create_token; print(create_token(1))"
```

Локально:
```bash
python -c "from shared.jwt_helper import create_token; print(create_token(1))"
```

Для affiliate_id=2:
```bash
docker-compose exec landings python -c \
  "from shared.jwt_helper import create_token; print(create_token(2))"
```

### POST /lead (landings :8001)

```bash
curl -X POST http://localhost:8001/lead \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Олексій",
    "phone": "+380982342123",
    "country": "UA",
    "offer_id": 1,
    "affiliate_id": 1
  }'
```

Відповідь:
```json
{"status": "queued", "message": "Лід прийнято та поставлено в чергу"}
```

### GET /leads (core :8002)

```bash
# Групування по датах
curl "http://localhost:8002/leads?date_from=2024-06-01&date_to=2024-06-30&group=date" \
  -H "Authorization: Bearer <TOKEN>"

# Групування по офферах
curl "http://localhost:8002/leads?date_from=2024-06-01&date_to=2024-06-30&group=offer" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Запуск тестів

```bash
pytest -v
```

---

## Відхилення від стека та рішення

| Питання | Рішення | Причина |
|---------|---------|---------|
| `offer_id`, `affiliate_id` тип | `int` (FK до таблиць) | Простіший JOIN, природніший PK для seed-даних |
| Воркер у тому ж процесі | `asyncio.create_task` в lifespan | Не потрібен окремий контейнер/процес; легко замінити на Celery/ARQ |
| Seed-дані | В міграції `0001_initial` | Зручно для старту без окремого скрипту |
| Дедуплікація | Redis `SET NX EX 600` | Атомарна операція, TTL 10 хв, не потребує Lua |

---

## Змінні оточення

| Змінна | За замовчуванням | Опис |
|--------|-----------------|------|
| `DATABASE_URL` | `postgresql+asyncpg://leads_user:leads_pass@localhost:5432/leads_db` | PostgreSQL URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis URL |
| `JWT_SECRET` | `change-me-in-production` | Секрет для підпису JWT |