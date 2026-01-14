"""Add OAuth fields to users table

Revision ID: 002
Revises: 001
Create Date: 2026-01-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add GitHub OAuth fields
    op.add_column('rg_users', sa.Column('github_id', sa.String(length=255), nullable=True))
    op.add_column('rg_users', sa.Column('github_username', sa.String(length=255), nullable=True))
    op.add_column('rg_users', sa.Column('github_access_token', sa.Text(), nullable=True))
    op.add_column('rg_users', sa.Column('github_token_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('rg_users', sa.Column('github_scopes', sa.String(length=512), nullable=True))
    
    # Add LinkedIn OAuth fields
    op.add_column('rg_users', sa.Column('linkedin_id', sa.String(length=255), nullable=True))
    op.add_column('rg_users', sa.Column('linkedin_access_token', sa.Text(), nullable=True))
    op.add_column('rg_users', sa.Column('linkedin_token_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('rg_users', sa.Column('linkedin_profile_url', sa.String(length=1024), nullable=True))
    
    # Add indices for OAuth lookup
    op.create_index(op.f('ix_github_id'), 'rg_users', ['github_id'], unique=True)
    op.create_index(op.f('ix_linkedin_id'), 'rg_users', ['linkedin_id'], unique=True)


def downgrade() -> None:
    # Drop indices
    op.drop_index(op.f('ix_linkedin_id'), table_name='rg_users')
    op.drop_index(op.f('ix_github_id'), table_name='rg_users')
    
    # Remove LinkedIn OAuth fields
    op.drop_column('rg_users', 'linkedin_profile_url')
    op.drop_column('rg_users', 'linkedin_token_expires_at')
    op.drop_column('rg_users', 'linkedin_access_token')
    op.drop_column('rg_users', 'linkedin_id')
    
    # Remove GitHub OAuth fields
    op.drop_column('rg_users', 'github_scopes')
    op.drop_column('rg_users', 'github_token_expires_at')
    op.drop_column('rg_users', 'github_access_token')
    op.drop_column('rg_users', 'github_username')
    op.drop_column('rg_users', 'github_id')
