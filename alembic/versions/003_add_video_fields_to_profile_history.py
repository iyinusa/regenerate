"""Add video fields to profile history table

Revision ID: 003
Revises: 002
Create Date: 2026-01-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add intro_video and full_video fields to rg_profile_history table."""
    # Add video URL fields after structured_data
    op.add_column('rg_profile_history', sa.Column('intro_video', sa.String(length=2048), nullable=True))
    op.add_column('rg_profile_history', sa.Column('full_video', sa.String(length=2048), nullable=True))


def downgrade() -> None:
    """Remove video URL fields from rg_profile_history table."""
    op.drop_column('rg_profile_history', 'full_video')
    op.drop_column('rg_profile_history', 'intro_video')