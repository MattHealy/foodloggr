"""empty message

Revision ID: 374cb959d078
Revises: 4892ebc95a5
Create Date: 2015-08-28 09:12:45.804618

"""

# revision identifiers, used by Alembic.
revision = '374cb959d078'
down_revision = '4892ebc95a5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('vote',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entry_id', sa.Integer(), nullable=True),
    sa.Column('upvote', sa.Boolean(), nullable=True),
    sa.Column('from_userid', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['entry_id'], ['entry.id'], ),
    sa.ForeignKeyConstraint(['from_userid'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('vote')
    ### end Alembic commands ###
