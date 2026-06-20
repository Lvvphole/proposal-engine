"""add owner_id to envelopes + contractors (tenancy)

Revision ID: 0002_owner_id
Revises: 0001_initial
Create Date: 2026-06-20

Adds the per-user ownership column used to scope quotes and contractors to the
authenticated Supabase user when auth is enabled.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_owner_id"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("envelopes", sa.Column("owner_id", sa.String(length=128), nullable=True))
    op.create_index("ix_envelopes_owner_id", "envelopes", ["owner_id"])

    op.add_column("contractors", sa.Column("owner_id", sa.String(length=128), nullable=True))
    op.create_index("ix_contractors_owner_id", "contractors", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_contractors_owner_id", table_name="contractors")
    op.drop_column("contractors", "owner_id")
    op.drop_index("ix_envelopes_owner_id", table_name="envelopes")
    op.drop_column("envelopes", "owner_id")
