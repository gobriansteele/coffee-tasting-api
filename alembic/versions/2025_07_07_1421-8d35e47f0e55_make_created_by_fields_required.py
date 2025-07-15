"""make_created_by_fields_required

Revision ID: 8d35e47f0e55
Revises: 20a74b01dca4
Create Date: 2025-07-07 14:21:37.611976

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '8d35e47f0e55'
down_revision = '20a74b01dca4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make created_by fields NOT NULL for all tables
    tables_to_update = [
        'roaster',
        'coffee',
        'flavortag',
        'tasting_session',
        'tasting_note'
    ]

    for table_name in tables_to_update:
        op.alter_column(table_name, 'created_by', nullable=False)


def downgrade() -> None:
    # Make created_by fields nullable again
    tables_to_revert = [
        'roaster',
        'coffee',
        'flavortag',
        'tasting_session',
        'tasting_note'
    ]

    for table_name in tables_to_revert:
        op.alter_column(table_name, 'created_by', nullable=True)
