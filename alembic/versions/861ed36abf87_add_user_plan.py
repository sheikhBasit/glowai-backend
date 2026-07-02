"""add user plan and plan_expires_at

Revision ID: 861ed36abf87
Revises: e226c650e18c
Create Date: 2026-07-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '861ed36abf87'
down_revision: Union[str, None] = 'e226c650e18c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('plan', sa.String(), nullable=False, server_default='free'))
    op.add_column('users', sa.Column('plan_expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'plan_expires_at')
    op.drop_column('users', 'plan')
