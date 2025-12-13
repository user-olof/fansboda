"""add role field to user table

Revision ID: 8a66cab00d72
Revises: 9f470ab60202
Create Date: 2025-12-13 22:16:12.829607

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8a66cab00d72"
down_revision = "9f470ab60202"
branch_labels = None
depends_on = None


def upgrade():
    # For PostgreSQL
    op.execute("CREATE TYPE role AS ENUM ('user', 'admin')")
    op.add_column(
        "user",
        sa.Column(
            "role",
            sa.Enum("user", "admin", name="role"),
            nullable=False,
            server_default="user",
        ),
    )

    # For SQLite/MySQL (simpler)
    # op.add_column('user', sa.Column('role', sa.String(20), nullable=False, server_default='user'))


def downgrade():
    op.drop_column("user", "role")
    op.execute("DROP TYPE role")  # PostgreSQL only
