"""initial tables

Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa
revision="0001"; down_revision=None; branch_labels=None; depends_on=None
def upgrade():
    op.create_table("users",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("telegram_id",sa.BigInteger(),nullable=False,unique=True),sa.Column("username",sa.String(100)),sa.Column("first_name",sa.String(200)),sa.Column("is_banned",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False))
    op.create_table("streams",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),sa.Column("platform",sa.String(40),nullable=False),sa.Column("original_url",sa.Text(),nullable=False),sa.Column("title",sa.Text()),sa.Column("channel_name",sa.String(300)),sa.Column("thumbnail",sa.Text()),sa.Column("status",sa.String(30),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False))
    op.create_table("stream_sessions",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("stream_id",sa.Integer(),sa.ForeignKey("streams.id"),nullable=False),sa.Column("session_id",sa.String(64),nullable=False,unique=True),sa.Column("quality",sa.String(40),nullable=False),sa.Column("playback_url",sa.Text()),sa.Column("status",sa.String(30),nullable=False),sa.Column("started_at",sa.DateTime(),nullable=False),sa.Column("stopped_at",sa.DateTime()))
    op.create_table("logs",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id")),sa.Column("action",sa.String(80),nullable=False),sa.Column("details",sa.Text()),sa.Column("created_at",sa.DateTime(),nullable=False))
def downgrade():
    op.drop_table("logs");op.drop_table("stream_sessions");op.drop_table("streams");op.drop_table("users")
