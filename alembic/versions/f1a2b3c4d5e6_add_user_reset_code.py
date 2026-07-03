"""add user reset_code_hash and reset_code_expires_at

Revision ID: f1a2b3c4d5e6
Revises: a3f9c2d17b04
Create Date: 2026-07-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'a3f9c2d17b04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('reset_code_hash', sa.String(), nullable=True))
    op.add_column('users', sa.Column('reset_code_expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'reset_code_expires_at')
    op.drop_column('users', 'reset_code_hash')
