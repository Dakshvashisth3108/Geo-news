"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-03

Creates all baseline tables. The `trading_signals` table has a composite
primary key `(id, timestamp)` so it can be promoted to a TimescaleDB
hypertable in environments where the extension is available
(Timescale Cloud, self-hosted Timescale). On vanilla Postgres
(e.g. Render's managed instance), the conditional block is a no-op and
the table behaves as a regular Postgres table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- enums -----
    signal_direction = postgresql.ENUM(
        "LONG", "SHORT", "NEUTRAL", name="signal_direction"
    )
    event_type = postgresql.ENUM(
        "WAR", "CONFLICT", "SANCTION", "ELECTION", "POLICY",
        "TERRORISM", "NATURAL_DISASTER", "ECONOMIC", "DIPLOMATIC", "OTHER",
        name="event_type",
    )
    event_severity = postgresql.ENUM(
        "LOW", "MEDIUM", "HIGH", "CRITICAL", name="event_severity"
    )
    alert_operator = postgresql.ENUM(
        "GT", "GTE", "LT", "LTE", "EQ", name="alert_operator"
    )
    bind = op.get_bind()
    signal_direction.create(bind, checkfirst=True)
    event_type.create(bind, checkfirst=True)
    event_severity.create(bind, checkfirst=True)
    alert_operator.create(bind, checkfirst=True)

    # ----- users -----
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ----- geopolitical_events -----
    op.create_table(
        "geopolitical_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("severity", event_severity, nullable=False),
        sa.Column("region", sa.String(128)),
        sa.Column("countries", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("source", sa.String(128)),
        sa.Column("source_url", sa.String(1024)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("raw_data", postgresql.JSONB),
    )
    op.create_index("ix_events_event_type", "geopolitical_events", ["event_type"])
    op.create_index("ix_events_severity", "geopolitical_events", ["severity"])
    op.create_index("ix_events_region", "geopolitical_events", ["region"])
    op.create_index("ix_events_occurred_at", "geopolitical_events", ["occurred_at"])
    op.create_index(
        "ix_events_type_occurred",
        "geopolitical_events",
        ["event_type", "occurred_at"],
    )

    # ----- trading_signals (composite PK for TimescaleDB compatibility) -----
    op.create_table(
        "trading_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("asset", sa.String(64), nullable=False),
        sa.Column("direction", signal_direction, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("uncertainty", sa.Float, nullable=False),
        sa.Column("gti", sa.Float, nullable=False),
        sa.Column("explanation", sa.Text, nullable=False),
        sa.Column("correlated_assets", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("geopolitical_events.id", ondelete="SET NULL"),
        ),
        sa.PrimaryKeyConstraint("id", "timestamp", name="pk_trading_signals"),
    )
    op.create_index(
        "ix_signals_asset_timestamp", "trading_signals", ["asset", "timestamp"]
    )
    op.create_index("ix_signals_timestamp", "trading_signals", ["timestamp"])

    # ----- TimescaleDB hypertable (optional) -----
    # Wrapped in a DO block: only runs if the extension is present, so this
    # migration applies cleanly on Render's plain Postgres too.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
            ) THEN
                PERFORM create_hypertable(
                    'trading_signals',
                    'timestamp',
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                );
            END IF;
        END
        $$;
        """
    )

    # ----- alert_rules -----
    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset", sa.String(64), nullable=False),
        sa.Column("metric", sa.String(32), nullable=False),
        sa.Column("operator", alert_operator, nullable=False),
        sa.Column("threshold", sa.Float, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_alerts_user_id", "alert_rules", ["user_id"])
    op.create_index("ix_alerts_asset", "alert_rules", ["asset"])


def downgrade() -> None:
    op.drop_table("alert_rules")
    op.drop_table("trading_signals")
    op.drop_table("geopolitical_events")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_name in (
        "alert_operator",
        "event_severity",
        "event_type",
        "signal_direction",
    ):
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
