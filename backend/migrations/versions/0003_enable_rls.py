"""Restrict Supabase Data API access; backend owner retains database access."""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLES = ("measurements", "forecast_models", "alembic_version")


def upgrade():
    if op.get_context().dialect.name == "postgresql":
        for table in TABLES:
            # No public policies: normal roles cannot access rows. The backend
            # connects as the table owner; do not FORCE RLS on that connection.
            op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')


def downgrade():
    if op.get_context().dialect.name == "postgresql":
        for table in TABLES:
            op.execute(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY')
