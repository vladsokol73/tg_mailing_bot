"""Add custom intervals to schedules

Revision ID: add_custom_intervals
Revises: 03391df4ff91
Create Date: 2025-05-13 16:05:45

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_custom_intervals'
down_revision = '03391df4ff91'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for custom intervals with non-nullable=False to work with existing data
    op.add_column('schedules', sa.Column('welcome_to_first_signal_seconds', sa.Integer(), nullable=True, server_default='60'))
    op.add_column('schedules', sa.Column('signal_to_win_seconds', sa.Integer(), nullable=True, server_default='45'))
    op.add_column('schedules', sa.Column('between_signals_seconds', sa.Integer(), nullable=True, server_default='25'))
    op.add_column('schedules', sa.Column('last_signal_to_summary_seconds', sa.Integer(), nullable=True, server_default='40'))


def downgrade():
    # Remove the custom interval columns
    op.drop_column('schedules', 'welcome_to_first_signal_seconds')
    op.drop_column('schedules', 'signal_to_win_seconds')
    op.drop_column('schedules', 'between_signals_seconds')
    op.drop_column('schedules', 'last_signal_to_summary_seconds')
