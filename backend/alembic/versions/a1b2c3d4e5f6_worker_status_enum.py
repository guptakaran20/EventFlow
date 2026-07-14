"""worker status enum migration

Revision ID: a1b2c3d4e5f6
Revises: 87925a676c08
Create Date: 2026-07-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "87925a676c08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE workers SET status = 'IDLE' WHERE status = 'ONLINE'")
    op.execute("UPDATE workers SET status = 'OFFLINE' WHERE status = 'STALE'")


def downgrade() -> None:
    op.execute("UPDATE workers SET status = 'ONLINE' WHERE status = 'IDLE'")
    op.execute("UPDATE workers SET status = 'STALE' WHERE status = 'OFFLINE'")
