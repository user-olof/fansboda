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
    # Detect database type
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    if is_postgresql:
        # PostgreSQL: Use ENUM type
        # Check if type already exists (for safety)
        # bind is already a connection, use it directly
        result = bind.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'role'"))
        type_exists = result.fetchone() is not None

        if not type_exists:
            op.execute("CREATE TYPE role AS ENUM ('USER', 'ADMIN')")

        op.add_column(
            "user",
            sa.Column(
                "role",
                sa.Enum("USER", "ADMIN", name="role", create_type=False),
                nullable=False,
                server_default="USER",
            ),
        )
    else:
        # SQLite/MySQL: Use String type
        op.add_column(
            "user",
            sa.Column("role", sa.String(20), nullable=False, server_default="USER"),
        )


def downgrade():
    # Detect database type
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    # Drop column first
    op.drop_column("user", "role")

    if is_postgresql:
        # PostgreSQL: Drop ENUM type if it exists
        # bind is already a connection, use it directly
        result = bind.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'role'"))
        type_exists = result.fetchone() is not None

        if type_exists:
            op.execute("DROP TYPE role")
