"""添加评分字段并合并迁移头

Revision ID: merge_heads_and_add_scores
Revises: add_version_column_to_essays
Create Date: 2024-04-07

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads_and_add_scores'
down_revision = 'add_version_column_to_essays'
branch_labels = None
depends_on = None

def upgrade():
    # 添加新的评分字段
    op.add_column('essays', sa.Column('content_score', sa.Float(), nullable=True))
    op.add_column('essays', sa.Column('language_score', sa.Float(), nullable=True))
    op.add_column('essays', sa.Column('structure_score', sa.Float(), nullable=True))
    op.add_column('essays', sa.Column('writing_score', sa.Float(), nullable=True))

def downgrade():
    # 删除评分字段
    op.drop_column('essays', 'content_score')
    op.drop_column('essays', 'language_score')
    op.drop_column('essays', 'structure_score')
    op.drop_column('essays', 'writing_score') 