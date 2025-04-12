"""add version column to essays table for optimistic locking

Revision ID: add_version_column_to_essays
Revises: a2c835cfcf04
Create Date: 2025-04-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_version_column_to_essays'
down_revision = 'a2c835cfcf04'
branch_labels = None
depends_on = None


def upgrade():
    # 为essays表添加version字段
    op.add_column('essays', sa.Column('version', sa.Integer(), nullable=False, server_default='0'))
    
    # 添加索引以提高性能
    op.create_index(op.f('ix_essays_version'), 'essays', ['version'], unique=False)


def downgrade():
    # 删除索引
    op.drop_index(op.f('ix_essays_version'), table_name='essays')
    
    # 删除字段
    op.drop_column('essays', 'version') 