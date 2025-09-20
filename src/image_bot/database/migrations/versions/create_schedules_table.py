"""create schedules table

Revision ID: create_schedules_table
Revises: create_channels_table
Create Date: 2025-04-06 23:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'create_schedules_table'
down_revision = 'create_channels_table'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.BigInteger(), nullable=False),
        sa.Column('time_of_day', sa.Time(), nullable=False),
        sa.Column('messages', sa.String(), nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('schedules')
