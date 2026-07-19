"""add cancelled run status

Revision ID: ecf722526565
Revises: 9063f7b89c8d
Create Date: 2026-07-19 17:55:33.735225
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'ecf722526565'
down_revision: str | None = '9063f7b89c8d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite CHECK constraints can't be ALTERed directly; batch mode rebuilds the table.
    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum(
                'queued', 'running', 'done', 'error',
                name='ck_runs_status', native_enum=False, create_constraint=True,
            ),
            type_=sa.Enum(
                'queued', 'running', 'done', 'error', 'cancelled',
                name='ck_runs_status', native_enum=False, create_constraint=True,
            ),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('runs', schema=None) as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum(
                'queued', 'running', 'done', 'error', 'cancelled',
                name='ck_runs_status', native_enum=False, create_constraint=True,
            ),
            type_=sa.Enum(
                'queued', 'running', 'done', 'error',
                name='ck_runs_status', native_enum=False, create_constraint=True,
            ),
            existing_nullable=False,
        )
