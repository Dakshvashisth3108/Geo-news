"""Pydantic v2 schemas — request/response shapes for the HTTP API."""

from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.schemas.event import (
    GeopoliticalEventCreate,
    GeopoliticalEventRead,
    GeopoliticalEventUpdate,
)
from app.schemas.signal import (
    CorrelatedAsset,
    TradingSignalCreate,
    TradingSignalRead,
)
from app.schemas.alert import AlertRuleCreate, AlertRuleRead, AlertRuleUpdate

__all__ = [
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "GeopoliticalEventCreate",
    "GeopoliticalEventRead",
    "GeopoliticalEventUpdate",
    "CorrelatedAsset",
    "TradingSignalCreate",
    "TradingSignalRead",
    "AlertRuleCreate",
    "AlertRuleRead",
    "AlertRuleUpdate",
]
