"""initial schema: plans, sims, msisdn_pool, audit_events

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SIM_STATUS = sa.Enum(
    "PENDING",
    "ALLOCATED",
    "ACTIVE",
    "SUSPENDED",
    "PORTED",
    "RECYCLED",
    name="sim_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        SIM_STATUS.create(bind, checkfirst=True)

    op.create_table(
        "plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False, unique=True),
        sa.Column("data_gb", sa.Integer, nullable=False),
        sa.Column("voice_min", sa.Integer, nullable=False),
        sa.Column("sms_count", sa.Integer, nullable=False),
        sa.Column("monthly_inr", sa.Integer, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "sims",
        sa.Column("iccid", sa.String(length=20), primary_key=True),
        sa.Column("imsi", sa.String(length=15), nullable=False, unique=True),
        sa.Column("msisdn", sa.String(length=16), nullable=True, unique=True),
        sa.Column("status", SIM_STATUS, nullable=False, server_default="PENDING"),
        sa.Column(
            "plan_id",
            sa.String(length=36),
            sa.ForeignKey("plans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provisioning_ref", sa.String(length=64), nullable=True),
        sa.Column("allocated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_transition_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_sims_status", "sims", ["status"])
    op.create_index("ix_sims_plan_id", "sims", ["plan_id"])
    op.create_index("ix_sims_status_plan", "sims", ["status", "plan_id"])

    op.create_table(
        "msisdn_pool",
        sa.Column("msisdn", sa.String(length=16), primary_key=True),
        sa.Column("is_used", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("assigned_iccid", sa.String(length=20), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_msisdn_pool_is_used", "msisdn_pool", ["is_used"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "sim_iccid",
            sa.String(length=20),
            sa.ForeignKey("sims.iccid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=80), nullable=False, server_default="system"),
        sa.Column("from_status", SIM_STATUS, nullable=True),
        sa.Column("to_status", SIM_STATUS, nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index(
        "ix_audit_created_sim",
        "audit_events",
        [sa.text("created_at DESC"), "sim_iccid"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_created_sim", table_name="audit_events")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_request_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_msisdn_pool_is_used", table_name="msisdn_pool")
    op.drop_table("msisdn_pool")
    op.drop_index("ix_sims_status_plan", table_name="sims")
    op.drop_index("ix_sims_plan_id", table_name="sims")
    op.drop_index("ix_sims_status", table_name="sims")
    op.drop_table("sims")
    op.drop_table("plans")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        SIM_STATUS.drop(bind, checkfirst=True)
