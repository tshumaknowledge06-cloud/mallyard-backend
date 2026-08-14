"""add user_roles table

Revision ID: cfacd9c03839
Revises: 1311ca84b6dd
Create Date: 2026-07-06 15:18:42.033955

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfacd9c03839'
down_revision: Union[str, Sequence[str], None] = '1311ca84b6dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    op.create_table(
        "user_roles",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        sa.Column(
            "role",
            postgresql.ENUM(
                "admin",
                "seller",
                "customer",
                "delivery_partner",
                name="role",
                create_type=False,
            ),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_user_roles_user_id",
        "user_roles",
        ["user_id"],
    )

    # --------------------------------------------------
    # Backfill existing users
    # --------------------------------------------------

    op.execute(
        """
        INSERT INTO user_roles (user_id, role)
        SELECT id, role
        FROM users;
        """
    )

def downgrade():

    op.drop_index(
        "ix_user_roles_user_id",
        table_name="user_roles",
    )

    op.drop_table("user_roles")
