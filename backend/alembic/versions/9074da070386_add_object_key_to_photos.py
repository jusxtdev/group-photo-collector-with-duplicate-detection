"""add object_key to photos

Revision ID: 9074da070386
Revises: 2c44d6c57dae
Create Date: 2026-10-10 11:34:36.373825

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9074da070386'
down_revision: Union[str, Sequence[str], None] = '2c44d6c57dae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Pre-existing rows (demo/seed data) have no object key; clear them so the
    # new NOT NULL column can be added.
    op.execute(sa.text("DELETE FROM photos"))
    op.add_column(
        "photos",
        sa.Column("object_key", sa.String(length=1024), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("photos", "object_key")
