"""remove_service_user_fields

Revision ID: 87b35128d3d7
Revises: b2a7c26f5f12
Create Date: 2026-04-05 21:57:45.061848
"""

import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa

from nutrition_tracking_api.api.utils.auth import hash_password
from nutrition_tracking_api.settings import settings


# revision identifiers, used by Alembic.
revision = "87b35128d3d7"
down_revision = "b2a7c26f5f12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("user", "access_token")
    op.drop_column("user", "access_token_expires_at")
    op.drop_column("user", "is_service_user")

    now = datetime.now()
    op.execute(
        sa.text(
            """
            INSERT INTO "user"
                (id, username, password_hash, is_superuser,
                 birth_date, gender, height_cm, weight_kg, activity_level,
                 created_at, updated_at)
            VALUES
                (:id, :username, :password_hash, :is_superuser,
                 :birth_date, :gender, :height_cm, :weight_kg, :activity_level,
                 :created_at, :updated_at)
            ON CONFLICT (username) DO NOTHING
            """
        ).bindparams(
            id=uuid.uuid4(),
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            is_superuser=True,
            birth_date=datetime(1990, 1, 1).date(),
            gender="male",
            height_cm=170.0,
            weight_kg=70.0,
            activity_level="moderately_active",
            created_at=now,
            updated_at=now,
        )
    )


def downgrade() -> None:
    op.add_column("user", sa.Column("is_service_user", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("user", sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user", sa.Column("access_token", sa.String(), nullable=True))
