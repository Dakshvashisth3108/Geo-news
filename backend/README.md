# GeoIntel Trade — Backend

FastAPI service that powers the GeoIntel Trade platform: a Geopolitical
Intelligence SaaS for algorithmic trading.

## Stack
- **FastAPI** (async)
- **SQLAlchemy 2.0** with `asyncpg` (PostgreSQL)
- **Pydantic v2** for schemas, `pydantic-settings` for config
- **Alembic** for migrations
- WebSockets for real-time signal streaming

## Project structure
```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, health, lifespan
│   ├── core/
│   │   ├── config.py        # pydantic-settings
│   │   └── database.py      # async engine + session
│   ├── api/v1/
│   │   ├── __init__.py      # api_router (aggregates endpoints)
│   │   └── endpoints/       # users, signals, alerts, websocket
│   ├── models/              # SQLAlchemy ORM
│   ├── schemas/             # Pydantic DTOs
│   ├── services/            # Business logic
│   └── utils/               # WebSocket connection manager
├── alembic/                 # Migration env (async-aware)
├── alembic.ini
├── requirements.txt
└── .env.example
```

## Quick start
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # then edit values
alembic revision --autogenerate -m "init"
alembic upgrade head
uvicorn app.main:app --reload
```

Then open:
- **Swagger UI** → http://localhost:8000/docs
- **Health**     → http://localhost:8000/health
- **WS stream**  → `ws://localhost:8000/api/v1/ws/signals`

## Data model — TradingSignal
| field              | type        | notes                                 |
| ------------------ | ----------- | ------------------------------------- |
| `asset`            | string      | ticker / instrument                   |
| `direction`        | enum        | LONG / SHORT / NEUTRAL                |
| `confidence`       | float       | [0, 1]                                |
| `uncertainty`      | float       | [0, 1]                                |
| `gti`              | float       | Geopolitical Tension Index, [0, 100]  |
| `explanation`      | text        | LLM-produced rationale                |
| `correlated_assets`| JSONB       | `[{asset, correlation}, ...]`         |
| `timestamp`        | timestamptz | server-generated                      |
