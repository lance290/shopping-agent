"""add_user_referred_by_id

Revision ID: 7d2c4e1f9ab3
Revises: 5c3816aecf94
Create Date: 2026-03-05 22:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7d2c4e1f9ab3"
down_revision: Union[str, Sequence[str], None] = "5c3816aecf94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_NAME = "fk_user_referred_by_id_user"


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_cols = [c["name"] for c in inspector.get_columns("user")]
    if "referred_by_id" not in user_cols:
        op.add_column("user", sa.Column("referred_by_id", sa.Integer(), nullable=True))

    existing_fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("user")}
    if FK_NAME not in existing_fk_names:
        op.create_foreign_key(
            FK_NAME,
            "user",
            "user",
            ["referred_by_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("user")}
    if FK_NAME in existing_fk_names:
        op.drop_constraint(FK_NAME, "user", type_="foreignkey")

    user_cols = [c["name"] for c in inspector.get_columns("user")]
    if "referred_by_id" in user_cols:
        op.drop_column("user", "referred_by_id")
