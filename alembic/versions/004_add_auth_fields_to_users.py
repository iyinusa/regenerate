"""Add authentication fields to users table

Revision ID: 004
Revises: 003
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new authentication fields to rg_users table
    op.add_column('rg_users', sa.Column('username', sa.String(length=255), nullable=True))
    op.add_column('rg_users', sa.Column('password_hash', sa.Text(), nullable=True))
    op.add_column('rg_users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))
    op.add_column('rg_users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('rg_users', sa.Column('refresh_token', sa.Text(), nullable=True))
    
    # Add indexes for better performance
    op.create_index(op.f('ix_rg_users_username'), 'rg_users', ['username'], unique=True)
    op.create_index(op.f('ix_rg_users_email'), 'rg_users', ['email'], unique=True)
    
    # Drop the old non-unique index on email if it exists
    try:
        op.drop_index('ix_rg_users_email', table_name='rg_users')
    except:
        pass  # Index might not exist


def downgrade() -> None:
    # Remove the new columns
    op.drop_index(op.f('ix_rg_users_username'), table_name='rg_users')
    op.drop_column('rg_users', 'refresh_token')
    op.drop_column('rg_users', 'is_verified')
    op.drop_column('rg_users', 'is_active')
    op.drop_column('rg_users', 'password_hash')
    op.drop_column('rg_users', 'username')
    
    # Recreate the old email index
    op.create_index('ix_rg_users_email', 'rg_users', ['email'], unique=False)