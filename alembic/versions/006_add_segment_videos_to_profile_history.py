"""Add segment videos to profile history

Revision ID: 006
Revises: 005
Create Date: 2026-01-31 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands - add segment_videos column ###
    op.add_column('rg_profile_history', sa.Column('segment_videos', sa.JSON(), nullable=True))
    # ### end commands ###


def downgrade() -> None:
    # ### commands - drop segment_videos column ###
    op.drop_column('rg_profile_history', 'segment_videos')
    # ### end commands ###
