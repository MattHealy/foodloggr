"""empty message

Revision ID: 54b79770f77c
Revises: 2ab668097ec4
Create Date: 2015-10-18 13:08:02.550649

"""

# revision identifiers, used by Alembic.
revision = '54b79770f77c'
down_revision = '2ab668097ec4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('reminder_setting',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('morning', sa.Boolean(), nullable=True),
    sa.Column('afternoon', sa.Boolean(), nullable=True),
    sa.Column('evening', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('reminder_setting')
    ### end Alembic commands ###
