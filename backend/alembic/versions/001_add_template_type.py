"""add template_type to templates

Revision ID: 001_add_template_type
Revises: 
Create Date: 2025-01-25 18:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_template_type'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add template_type column to templates table
    op.add_column('templates', 
        sa.Column('template_type', sa.String(length=20), nullable=False, server_default='initial')
    )
    
    # Create index for faster filtering
    op.create_index('ix_templates_template_type', 'templates', ['template_type'])


def downgrade():
    # Remove index
    op.drop_index('ix_templates_template_type', table_name='templates')
    
    # Remove column
    op.drop_column('templates', 'template_type')

