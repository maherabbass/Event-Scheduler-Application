"""Initial schema — users, events, event_attendees, invitations

Revision ID: 0001
Revises:
Create Date: 2026-02-22 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False on PG_ENUM prevents op.create_table from auto-issuing
# CREATE TYPE.  We create the types ourselves below using PL/pgSQL that
# silently ignores duplicate_object errors, making the migration idempotent.
userrole_enum = PG_ENUM("ADMIN", "ORGANIZER", "MEMBER", name="userrole", create_type=False)
eventstatus_enum = PG_ENUM("DRAFT", "PUBLISHED", "CANCELLED", name="eventstatus", create_type=False)
rsvpstatus_enum = PG_ENUM(
    "UPCOMING", "ATTENDING", "MAYBE", "DECLINED", name="rsvpstatus", create_type=False
)


def upgrade() -> None:
    # Create enum types idempotently — PL/pgSQL swallows duplicate_object so
    # re-running the migration after a partial failure is safe.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('ADMIN', 'ORGANIZER', 'MEMBER');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
        """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE eventstatus AS ENUM ('DRAFT', 'PUBLISHED', 'CANCELLED');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
        """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE rsvpstatus AS ENUM ('UPCOMING', 'ATTENDING', 'MAYBE', 'DECLINED');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
        """)

    # users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            userrole_enum,
            nullable=False,
            server_default="MEMBER",
        ),
        sa.Column("oauth_provider", sa.String(50), nullable=True),
        sa.Column("oauth_subject", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # events table
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(5000), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("start_datetime", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("end_datetime", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("tags", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column(
            "status",
            eventstatus_enum,
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # event_attendees table
    op.create_table(
        "event_attendees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("rsvp_status", rsvpstatus_enum, nullable=False),
        sa.Column("responded_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_attendee"),
    )

    # invitations table
    op.create_table(
        "invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invited_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("invited_email", sa.String(255), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("token", name="uq_invitations_token"),
        sa.UniqueConstraint("event_id", "invited_email", name="uq_invitation_event_email"),
    )


def downgrade() -> None:
    op.drop_table("invitations")
    op.drop_table("event_attendees")
    op.drop_table("events")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS rsvpstatus")
    op.execute("DROP TYPE IF EXISTS eventstatus")
    op.execute("DROP TYPE IF EXISTS userrole")
