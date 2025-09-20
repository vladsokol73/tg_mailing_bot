"""change telegram_id to bigint

Revision ID: change_telegram_id_to_bigint
Revises: initial_schema
Create Date: 2025-04-09 16:09:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'change_telegram_id_to_bigint'
down_revision = 'initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Изменяем тип колонки telegram_id на BIGINT
    op.alter_column('users', 'telegram_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)


def downgrade() -> None:
    # Возвращаем тип колонки telegram_id на INTEGER
    op.alter_column('users', 'telegram_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False)
