"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), nullable=False, server_default="default"),
        sa.Column("item_name", sa.String(), nullable=False),
        sa.Column("quantity", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("acquired_date", sa.String(), nullable=False),
        sa.Column("expiry_date", sa.String(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )
    op.create_index("ix_inventory_user_id", "inventory", ["user_id"])

    op.create_table(
        "shopping_list",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), nullable=False, server_default="default"),
        sa.Column("item_name", sa.String(), nullable=False),
        sa.Column("quantity", sa.String(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("source_recipe", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("feedback", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.Column("updated_at", sa.String(), nullable=True),
    )
    op.create_index("ix_shopping_list_user_id", "shopping_list", ["user_id"])
    op.create_index("ix_shopping_list_status", "shopping_list", ["status"])

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("scheduled_time", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
    )
    op.create_index("ix_reminders_scheduled_time", "reminders", ["scheduled_time"])
    op.create_index("ix_reminders_status", "reminders", ["status"])
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"])

    op.create_table(
        "agent_memory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=True),
    )
    op.create_index("ix_agent_memory_key", "agent_memory", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_agent_memory_key", table_name="agent_memory")
    op.drop_table("agent_memory")

    op.drop_index("ix_reminders_user_id", table_name="reminders")
    op.drop_index("ix_reminders_status", table_name="reminders")
    op.drop_index("ix_reminders_scheduled_time", table_name="reminders")
    op.drop_table("reminders")

    op.drop_index("ix_shopping_list_status", table_name="shopping_list")
    op.drop_index("ix_shopping_list_user_id", table_name="shopping_list")
    op.drop_table("shopping_list")

    op.drop_index("ix_inventory_user_id", table_name="inventory")
    op.drop_table("inventory")
