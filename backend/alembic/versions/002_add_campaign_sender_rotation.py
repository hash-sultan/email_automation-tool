"""add campaign sender rotation support

Revision ID: 002_add_campaign_sender_rotation
Revises: 001_add_template_type
Create Date: 2026-01-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_add_campaign_sender_rotation"
down_revision: Union[str, None] = "001_add_template_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  # Campaign sender rotation flags
  op.add_column(
      "campaigns",
      sa.Column(
          "sender_rotation_enabled",
          sa.Boolean(),
          nullable=False,
          server_default=sa.false(),
      ),
  )
  op.add_column(
      "campaigns",
      sa.Column("max_senders", sa.Integer(), nullable=True),
  )

  # Association table for multi-sender campaigns
  op.create_table(
      "campaign_senders",
      sa.Column("id", sa.Integer(), primary_key=True, index=True),
      sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
      sa.Column("sender_id", sa.Integer(), sa.ForeignKey("senders.id", ondelete="CASCADE"), nullable=False, index=True),
      sa.Column("position", sa.Integer(), nullable=True),
      sa.UniqueConstraint("campaign_id", "sender_id", name="uq_campaign_senders_campaign_sender"),
  )


def downgrade() -> None:
  op.drop_table("campaign_senders")
  op.drop_column("campaigns", "max_senders")
  op.drop_column("campaigns", "sender_rotation_enabled")


