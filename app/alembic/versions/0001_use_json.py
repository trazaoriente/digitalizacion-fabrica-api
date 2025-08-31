"""Use generic JSON for documents JSON fields

Revision ID: 0001_use_json
Revises: 
Create Date: 2024-06-xx
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_use_json"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Switch JSONB columns to generic JSON."""
    try:
        op.alter_column("documents", "tags", type_=sa.JSON(), postgresql_using="tags::json")
        op.alter_column("documents", "extra", type_=sa.JSON(), postgresql_using="extra::json")
    except Exception:
        pass


def downgrade() -> None:
    """Revert columns back to JSONB if needed."""
    try:
        from sqlalchemy.dialects import postgresql
        op.alter_column("documents", "tags", type_=postgresql.JSONB(), postgresql_using="tags::jsonb")
        op.alter_column("documents", "extra", type_=postgresql.JSONB(), postgresql_using="extra::jsonb")
    except Exception:
        pass
