"""Data-access layer.

The repository pattern keeps SQL out of services and routes — services
orchestrate; repositories execute. This makes routes trivial, services
testable, and gives us a single place to optimize queries later
(e.g. when we promote `trading_signals` to a TimescaleDB hypertable
and add continuous aggregates).
"""

from app.repositories.signal_repository import SignalRepository

__all__ = ["SignalRepository"]
