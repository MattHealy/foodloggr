"""empty message

Revision ID: 7d9b7f4c182
Revises: 54b79770f77c
Create Date: 2015-12-17 07:42:33.122859

"""

# revision identifiers, used by Alembic.
revision = '7d9b7f4c182'
down_revision = '54b79770f77c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('weight_tracking',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('weight', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('weight_tracking')
    ### end Alembic commands ###
