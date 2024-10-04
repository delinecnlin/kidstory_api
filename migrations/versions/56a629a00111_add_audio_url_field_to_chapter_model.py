"""Add audio_url field to Chapter model

Revision ID: 56a629a00111
Revises: 276f61324fb1
Create Date: 2024-10-03 10:39:30.595440

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '56a629a00111'
down_revision = '276f61324fb1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('chapter', schema=None) as batch_op:
        batch_op.add_column(sa.Column('audio_url', sa.String(length=255), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('chapter', schema=None) as batch_op:
        batch_op.drop_column('audio_url')

    # ### end Alembic commands ###