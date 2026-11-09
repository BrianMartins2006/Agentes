"""Create environmental measurements table."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("temperature_c", sa.Float(), nullable=False),
        sa.Column("air_humidity_pct", sa.Float(), nullable=False),
        sa.Column("soil_raw", sa.Integer(), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("air_humidity_pct >= 0 AND air_humidity_pct <= 100"),
        sa.CheckConstraint("soil_raw >= 0"))
    op.create_index("ix_measurements_measured_at", "measurements", ["measured_at"])
    op.create_index("ix_measurements_device_time", "measurements", ["device_id", "measured_at"])


def downgrade():
    op.drop_table("measurements")
