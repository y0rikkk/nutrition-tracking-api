"""Add history table

Revision ID: a1b2c3d4e5f6
Revises: 784b8226c7b4
Create Date: 2026-02-24 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "784b8226c7b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "history",
        sa.Column("object_type", sa.String(255), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("parent_id", sa.Uuid(), nullable=False),
        sa.Column("parent_type", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "action",
            sa.Enum("create", "update", "archive", "recover", "delete", name="historyactionenum"),
            nullable=False,
        ),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_history_object_id"), "history", ["object_id"], unique=False)
    op.create_index(op.f("ix_history_parent_id"), "history", ["parent_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_history_parent_id"), table_name="history")
    op.drop_index(op.f("ix_history_object_id"), table_name="history")
    op.drop_table("history")

    historyactionenum = sa.Enum(name="historyactionenum")
    historyactionenum.drop(op.get_bind())
