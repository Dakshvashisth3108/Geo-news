"""Aggregates every v1 router under a single APIRouter."""

from fastapi import APIRouter

from app.api.v1.endpoints import alerts, events, signals, users, websocket

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(signals.router, prefix="/signals", tags=["signals"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(websocket.router, tags=["websocket"])
