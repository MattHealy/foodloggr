"""empty message

Revision ID: 1f06b6030e3e
Revises: 3182e427607e
Create Date: 2015-09-10 20:52:55.760879

"""

# revision identifiers, used by Alembic.
revision = '1f06b6030e3e'
down_revision = '3182e427607e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('score', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'score')
    ### end Alembic commands ###
