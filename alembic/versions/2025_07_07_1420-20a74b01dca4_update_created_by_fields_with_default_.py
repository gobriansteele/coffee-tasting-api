"""update_created_by_fields_with_default_user

Revision ID: 20a74b01dca4
Revises: bacddf8094d4
Create Date: 2025-07-07 14:20:30.383473

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20a74b01dca4'
down_revision = 'bacddf8094d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update all created_by fields to the default user ID
    default_user_id = 'ffa52d0a-096f-4c22-ad2d-d55ac1e6d9fc'
    
    # Update all tables that have created_by fields
    tables_to_update = [
        'roaster',
        'coffee', 
        'flavortag',
        'tasting_session',
        'tasting_note'
    ]
    
    for table_name in tables_to_update:
        op.execute(f"""
            UPDATE {table_name} 
            SET created_by = '{default_user_id}' 
            WHERE created_by IS NULL
        """)


def downgrade() -> None:
    # Set created_by back to NULL for records that were updated
    default_user_id = 'ffa52d0a-096f-4c22-ad2d-d55ac1e6d9fc'
    
    tables_to_revert = [
        'roaster',
        'coffee', 
        'flavortag',
        'tasting_session',
        'tasting_note'
    ]
    
    for table_name in tables_to_revert:
        op.execute(f"""
            UPDATE {table_name} 
            SET created_by = NULL 
            WHERE created_by = '{default_user_id}'
        """)