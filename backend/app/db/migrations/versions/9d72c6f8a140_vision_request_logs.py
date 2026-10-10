"""vision request logs

Revision ID: 9d72c6f8a140
Revises: 4884015c3395
Create Date: 2026-10-10

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d72c6f8a140"
down_revision: Union[str, Sequence[str], None] = "4884015c3395"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vision_request_logs",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("profile_name", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.CheckConstraint("mode IN ('describe', 'ocr')", name="ck_vision_request_logs_mode"),
        sa.CheckConstraint("duration_ms >= 0", name="ck_vision_request_logs_duration"),
        sa.CheckConstraint(
            "(succeeded AND error_code IS NULL) OR (NOT succeeded AND error_code IS NOT NULL)",
            name="ck_vision_request_logs_result",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_vision_request_logs_user_created",
        "vision_request_logs",
        ["user_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("idx_vision_request_logs_user_created", table_name="vision_request_logs")
    op.drop_table("vision_request_logs")
