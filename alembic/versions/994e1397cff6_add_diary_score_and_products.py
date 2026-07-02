"""add diary score and products_used

Revision ID: 994e1397cff6
Revises: 861ed36abf87
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '994e1397cff6'
down_revision = '861ed36abf87'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('diary_entries', sa.Column('score', sa.Float(), nullable=True))
    op.add_column('diary_entries', sa.Column('products_used', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('diary_entries', 'products_used')
    op.drop_column('diary_entries', 'score')
