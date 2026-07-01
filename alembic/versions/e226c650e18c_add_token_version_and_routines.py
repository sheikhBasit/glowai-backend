"""add token_version and routines

Revision ID: e226c650e18c
Revises: 09d6e5fb12fb
Create Date: 2026-06-23 21:54:31.842750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e226c650e18c'
down_revision: Union[str, None] = '09d6e5fb12fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('token_version', sa.SmallInteger(), nullable=False, server_default='0'))
    # routines table already created by create_all; create only if missing
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, 'routines'):
        op.create_table(
            'routines',
            sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('morning', sa.dialects.postgresql.JSONB(), nullable=False, server_default='[]'),
            sa.Column('evening', sa.dialects.postgresql.JSONB(), nullable=False, server_default='[]'),
            sa.Column('weekly',  sa.dialects.postgresql.JSONB(), nullable=False, server_default='[]'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_table('routines')
    op.drop_column('users', 'token_version')
