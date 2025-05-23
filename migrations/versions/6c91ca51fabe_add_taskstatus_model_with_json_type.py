"""Add TaskStatus model with JSON type

Revision ID: 6c91ca51fabe
Revises: 1d463fca5798
Create Date: 2025-04-09 06:53:55.367705

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '6c91ca51fabe'
down_revision = '1d463fca5798'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('task_status',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.String(length=36), nullable=False),
    sa.Column('task_name', sa.String(length=100), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('related_type', sa.String(length=50), nullable=True),
    sa.Column('related_id', sa.String(length=36), nullable=True),
    sa.Column('worker_id', sa.String(length=100), nullable=True),
    sa.Column('args', sa.Text(), nullable=True),
    sa.Column('kwargs', sa.Text(), nullable=True),
    sa.Column('result', sa.JSON(), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('task_metadata', sa.JSON(), nullable=True),
    sa.Column('retry_count', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('task_status', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_task_status_related_id'), ['related_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_task_status_task_id'), ['task_id'], unique=True)

    with op.batch_alter_table('task_statuses', schema=None) as batch_op:
        batch_op.drop_index('ix_task_statuses_created_at')
        batch_op.drop_index('ix_task_statuses_related')
        batch_op.drop_index('ix_task_statuses_retry_count')
        batch_op.drop_index('ix_task_statuses_status')
        batch_op.drop_index('ix_task_statuses_status_created_at')
        batch_op.drop_index('ix_task_statuses_task_id')
        batch_op.drop_index('ix_task_statuses_task_name')

    op.drop_table('task_statuses')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('task_statuses',
    sa.Column('task_id', sa.VARCHAR(length=50), nullable=False),
    sa.Column('task_name', sa.VARCHAR(length=100), nullable=False),
    sa.Column('status', sa.VARCHAR(length=8), nullable=False),
    sa.Column('result', sqlite.JSON(), nullable=True),
    sa.Column('error_message', sa.VARCHAR(length=255), nullable=True),
    sa.Column('traceback', sa.TEXT(), nullable=True),
    sa.Column('retry_count', sa.INTEGER(), nullable=True),
    sa.Column('max_retries', sa.INTEGER(), nullable=True),
    sa.Column('next_retry_at', sa.DATETIME(), nullable=True),
    sa.Column('related_type', sa.VARCHAR(length=20), nullable=True),
    sa.Column('related_id', sa.INTEGER(), nullable=True),
    sa.Column('worker_id', sa.VARCHAR(length=100), nullable=True),
    sa.Column('args', sqlite.JSON(), nullable=True),
    sa.Column('kwargs', sqlite.JSON(), nullable=True),
    sa.Column('options', sqlite.JSON(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.Column('updated_at', sa.DATETIME(), nullable=True),
    sa.Column('started_at', sa.DATETIME(), nullable=True),
    sa.Column('completed_at', sa.DATETIME(), nullable=True),
    sa.Column('priority', sa.INTEGER(), nullable=True),
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('is_deleted', sa.BOOLEAN(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('task_statuses', schema=None) as batch_op:
        batch_op.create_index('ix_task_statuses_task_name', ['task_name'], unique=False)
        batch_op.create_index('ix_task_statuses_task_id', ['task_id'], unique=False)
        batch_op.create_index('ix_task_statuses_status_created_at', ['status', 'created_at'], unique=False)
        batch_op.create_index('ix_task_statuses_status', ['status'], unique=False)
        batch_op.create_index('ix_task_statuses_retry_count', ['retry_count'], unique=False)
        batch_op.create_index('ix_task_statuses_related', ['related_type', 'related_id'], unique=False)
        batch_op.create_index('ix_task_statuses_created_at', ['created_at'], unique=False)

    with op.batch_alter_table('task_status', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_task_status_task_id'))
        batch_op.drop_index(batch_op.f('ix_task_status_related_id'))

    op.drop_table('task_status')
    # ### end Alembic commands ###
