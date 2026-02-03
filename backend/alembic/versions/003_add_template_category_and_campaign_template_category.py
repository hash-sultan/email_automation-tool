"""add template category and campaign template_category

Revision ID: 003_template_category
Revises: 002_add_campaign_sender_rotation
Create Date: 2026-01-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_template_category"
down_revision: Union[str, None] = "002_add_campaign_sender_rotation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add category to templates (for grouping/rotation)
    op.add_column(
        "templates",
        sa.Column(
            "category",
            sa.String(length=100),
            nullable=False,
            server_default="General",
        ),
    )
    op.create_index("ix_templates_category", "templates", ["category"])

    # Add template_category to campaigns (to link campaigns to a category)
    op.add_column(
        "campaigns",
        sa.Column("template_category", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_campaigns_template_category", "campaigns", ["template_category"]
    )


def downgrade() -> None:
    op.drop_index("ix_campaigns_template_category", table_name="campaigns")
    op.drop_column("campaigns", "template_category")

    op.drop_index("ix_templates_category", table_name="templates")
    op.drop_column("templates", "category")


