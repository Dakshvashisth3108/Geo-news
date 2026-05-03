# GeoIntel Trade — Backend

FastAPI service powering GeoIntel Trade: a Geopolitical Intelligence SaaS for
algorithmic trading.

## Stack
- **FastAPI** (async)
- **SQLAlchemy 2.0** + `asyncpg` (PostgreSQL)
- **Pydantic v2** schemas, **pydantic-settings** config
- **Alembic** for migrations (async-aware)
- **TimescaleDB-ready** schema (works on plain Postgres too)
- WebSockets for real-time signal streaming

## Project structure
```
backend/
├── app/
│   ├── main.py                      # FastAPI app, CORS, /health, lifespan
│   ├── core/
│   │   ├── config.py                # pydantic-settings
│   │   └── database.py              # async engine + Render URL normalization
│   ├── api/v1/
│   │   ├── __init__.py              # api_router (aggregates endpoints)
│   │   └── endpoints/               # users, events, signals, alerts, websocket
│   ├── models/                      # User, GeopoliticalEvent, TradingSignal, AlertRule
│   ├── schemas/                     # Pydantic v2 DTOs
│   ├── repositories/                # Data-access layer (SignalRepository)
│   ├── services/                    # Orchestration (signal_service)
│   └── utils/                       # WebSocket connection manager
├── alembic/
│   ├── env.py                       # async-aware migration environment
│   └── versions/0001_initial.py     # baseline schema + optional hypertable
├── alembic.ini
├── requirements.txt
└── .env.example
```

## Domain model

| Entity | Purpose |
| --- | --- |
| `GeopoliticalEvent` | Raw geopolitical events ingested from news/feeds. |
| `TradingSignal` | GTI engine output. Composite PK `(id, timestamp)` — TimescaleDB-ready. Optional FK to `GeopoliticalEvent`. |
| `AlertRule` | User-defined thresholds on signal/GTI metrics. |
| `User` | Owns alert rules. |

### `TradingSignal` — multi-asset correlations
`correlated_assets` is a JSONB array. Each element is a `CorrelatedAsset`:

| field             | type    | range/notes                           |
| ----------------- | ------- | ------------------------------------- |
| `asset`           | string  | ticker / instrument                   |
| `correlation`     | float   | [-1, 1]                               |
| `expected_impact` | enum    | LONG / SHORT / NEUTRAL                |
| `magnitude`       | float?  | expected % move                       |
| `lag_minutes`     | int?    | expected lag from primary asset       |

## Quick start (local)
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                   # edit values
alembic upgrade head
uvicorn app.main:app --reload
```
- Swagger UI → http://localhost:8000/docs
- Health     → http://localhost:8000/health
- WS stream  → `ws://localhost:8000/api/v1/ws/signals`

## Deploy on Render.com

1. **Create a Postgres instance** on Render. Copy the *External Database URL*.
2. **Create a Web Service** pointing at this repo, root directory `backend`.
3. **Build command**:
   ```
   pip install -r requirements.txt && alembic upgrade head
   ```
4. **Start command**:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
5. **Environment variables** (in the Render dashboard):
   - `DATABASE_URL` — paste the External Database URL (`postgres://...?sslmode=require`).
     The app rewrites this to `postgresql+asyncpg://` and converts
     `sslmode=require` into the asyncpg-compatible SSL context automatically.
   - `ENVIRONMENT=production`
   - `SECRET_KEY=<long random string>`
   - `BACKEND_CORS_ORIGINS=https://your-frontend.onrender.com`
   - `DEBUG=false`

> **Note on TimescaleDB:** Render's managed Postgres does **not** ship the
> `timescaledb` extension. The migration's `create_hypertable` call is wrapped
> in a `DO` block guarded by `pg_extension`, so it is a no-op on Render and
> the table behaves like a regular Postgres table. To enable hypertable
> features, host on Timescale Cloud (or any Postgres with the extension
> installed) and re-run `alembic upgrade head` — the same migration will
> promote the table.

## Useful commands
```bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head

# Roll back one revision
alembic downgrade -1
```
