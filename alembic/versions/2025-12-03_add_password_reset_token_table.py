"""add password reset token table

Revision ID: 44af2c687fe3
Revises: 6a1ea56b96c9
Create Date: 2025-12-03 21:38:49.866661

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "44af2c687fe3"
down_revision = "6a1ea56b96c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_password_reset_token",
        sa.Column("token", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        schema="public"
    )


def downgrade() -> None:
    op.drop_table("auth_password_reset_token", schema="public")