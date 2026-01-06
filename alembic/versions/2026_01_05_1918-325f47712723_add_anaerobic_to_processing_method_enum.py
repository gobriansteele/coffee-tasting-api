"""add_anaerobic_to_processing_method_enum

Revision ID: 325f47712723
Revises: 8d35e47f0e55
Create Date: 2026-01-05 19:18:07.266164

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '325f47712723'
down_revision = '8d35e47f0e55'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE processing_method_enum ADD VALUE 'ANAEROBIC'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly.
    # A true downgrade would require recreating the enum type.
    pass