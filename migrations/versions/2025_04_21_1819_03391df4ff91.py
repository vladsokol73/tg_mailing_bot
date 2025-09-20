"""Add bet_amount to schedules

Revision ID: 03391df4ff91
Revises: change_telegram_id_to_bigint
Create Date: 2025-04-21 18:19:59.661383+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03391df4ff91'
down_revision: Union[str, None] = 'change_telegram_id_to_bigint'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле bet_amount в таблицу schedules
    op.add_column('schedules', sa.Column('bet_amount', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем поле bet_amount из таблицы schedules
    op.drop_column('schedules', 'bet_amount')
