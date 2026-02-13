"""init schema

Revision ID: 20260212_0001
Revises:
Create Date: 2026-02-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260212_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    store_engine = sa.Enum("woocommerce", "medusa", name="store_engine")
    store_status = sa.Enum("QUEUED", "PROVISIONING", "READY", "FAILED", "DELETING", "DELETED", name="store_status")
    job_action = sa.Enum("PROVISION", "DELETE", name="job_action")
    job_status = sa.Enum("QUEUED", "IN_PROGRESS", "SUCCEEDED", "FAILED", name="job_status")

    op.create_table(
        "stores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("engine", store_engine, nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("namespace", sa.String(length=140), nullable=False, unique=True),
        sa.Column("release_name", sa.String(length=140), nullable=False, unique=True),
        sa.Column("status", store_status, nullable=False),
        sa.Column("url", sa.String(length=255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "provisioning_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", job_action, nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_provisioning_jobs_status_created", "provisioning_jobs", ["status", "created_at"])

    op.create_table(
        "store_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_store_events_store_id_created", "store_events", ["store_id", "created_at"])

    op.create_table(
        "rate_limit_buckets",
        sa.Column("key", sa.String(length=200), primary_key=True, nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rate_limit_buckets")
    op.drop_index("ix_store_events_store_id_created", table_name="store_events")
    op.drop_table("store_events")
    op.drop_index("ix_provisioning_jobs_status_created", table_name="provisioning_jobs")
    op.drop_table("provisioning_jobs")
    op.drop_table("stores")

    bind = op.get_bind()
    sa.Enum(name="job_status").drop(bind, checkfirst=True)
    sa.Enum(name="job_action").drop(bind, checkfirst=True)
    sa.Enum(name="store_status").drop(bind, checkfirst=True)
    sa.Enum(name="store_engine").drop(bind, checkfirst=True)
