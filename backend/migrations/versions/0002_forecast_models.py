"""Persist evaluated ML models as JSON, without executable pickle files."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("forecast_models",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("artifact", sa.JSON(), nullable=False))
    op.create_index("ix_forecast_models_device_id", "forecast_models", ["device_id"])


def downgrade():
    op.drop_table("forecast_models")
