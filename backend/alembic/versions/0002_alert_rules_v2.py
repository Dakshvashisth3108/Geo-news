"""alert_rules v2 — compound conditions + channels

Revision ID: 0002_alert_rules_v2
Revises: 0001_initial
Create Date: 2026-05-03

Replaces the single-condition shape (metric / operator / threshold) with:
  * conditions JSONB list      — many AlertCondition entries
  * combinator alert_combinator (AND | OR)
  * channels JSONB list        — many NotificationChannel entries
  * name / description
  * cooldown_seconds, last_triggered_at, trigger_count

Also lifts NOT NULL on `asset` so a rule can apply to all assets.

NOTE: Destructive on existing data. The MVP scaffold has no real rules
yet; production users would replace the body of `upgrade()` with a
SELECT-then-UPDATE that maps every existing (metric, operator, threshold)
into the JSONB conditions list before dropping the columns.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0002_alert_rules_v2"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # New enum (idempotent)
    alert_combinator = postgresql.ENUM("AND", "OR", name="alert_combinator")
    alert_combinator.create(bind, checkfirst=True)

    # Drop old single-condition columns
    op.drop_column("alert_rules", "metric")
    op.drop_column("alert_rules", "operator")
    op.drop_column("alert_rules", "threshold")

    # Old enum was only used by alert_rules — safe to drop now
    sa.Enum(name="alert_operator").drop(bind, checkfirst=True)

    # New columns
    op.add_column(
        "alert_rules",
        sa.Column("name", sa.String(128), nullable=False, server_default="Untitled rule"),
    )
    op.add_column("alert_rules", sa.Column("description", sa.Text))
    op.add_column(
        "alert_rules",
        sa.Column(
            "conditions",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "alert_rules",
        sa.Column(
            "combinator",
            alert_combinator,
            nullable=False,
            server_default="AND",
        ),
    )
    op.add_column(
        "alert_rules",
        sa.Column(
            "channels",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "alert_rules",
        sa.Column("cooldown_seconds", sa.Integer, nullable=False, server_default="300"),
    )
    op.add_column(
        "alert_rules",
        sa.Column("last_triggered_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "alert_rules",
        sa.Column("trigger_count", sa.Integer, nullable=False, server_default="0"),
    )

    # Asset becomes optional (null = matches every asset)
    op.alter_column("alert_rules", "asset", nullable=True)


def downgrade() -> None:
    bind = op.get_bind()

    # Restore asset NOT NULL
    op.alter_column("alert_rules", "asset", nullable=False)

    # Drop new columns
    op.drop_column("alert_rules", "trigger_count")
    op.drop_column("alert_rules", "last_triggered_at")
    op.drop_column("alert_rules", "cooldown_seconds")
    op.drop_column("alert_rules", "channels")
    op.drop_column("alert_rules", "combinator")
    op.drop_column("alert_rules", "conditions")
    op.drop_column("alert_rules", "description")
    op.drop_column("alert_rules", "name")

    # Drop new enum
    sa.Enum(name="alert_combinator").drop(bind, checkfirst=True)

    # Restore old single-condition shape + enum
    alert_operator = postgresql.ENUM(
        "GT", "GTE", "LT", "LTE", "EQ", name="alert_operator",
    )
    alert_operator.create(bind, checkfirst=True)

    op.add_column(
        "alert_rules",
        sa.Column("metric", sa.String(32), nullable=False, server_default="gti"),
    )
    op.add_column(
        "alert_rules",
        sa.Column("operator", alert_operator, nullable=False, server_default="GT"),
    )
    op.add_column(
        "alert_rules",
        sa.Column("threshold", sa.Float, nullable=False, server_default="0.0"),
    )
