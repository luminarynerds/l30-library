# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Alembic async migration environment for L30.

Uses the same async engine configuration as the application.
Imports all models so autogenerate can detect schema changes.

NOTE: The database was created via init_schema_async_raw_sql.py which
doesn't emit column comments, FK ondelete clauses, or some indexes.
These pre-existing differences are filtered out so autogenerate only
catches real future changes. If you later want to sync these, remove
the filters and generate a dedicated migration.
"""

import asyncio
import os
import warnings

from alembic import context
from alembic.operations import ops
from sqlalchemy import exc as sa_exc
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Suppress noisy warning about cyclic FKs between indie_authors ↔ indie_ebooks.
# This is a known model pattern (mutual FK with use_alter=True) and is harmless.
warnings.filterwarnings(
    "ignore",
    message="Cannot correctly sort tables",
    category=sa_exc.SAWarning,
)

# Import Base and all models so metadata is fully populated
from app.core.database import Base
import app.models  # noqa: F401 — registers all models with Base.metadata

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url from environment variable
database_url = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://lsc:password@localhost:5432/lsc_library",
)
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata

# Tables that exist in the database but have no corresponding model.
# Autogenerate will ignore these instead of generating DROP TABLE ops.
EXCLUDE_TABLES = set()

# Indexes that use custom names (not matching naming_convention) and already
# exist in the DB. Autogenerate can't match them by name, so it always wants
# to re-create them. We suppress those false positives here.
EXISTING_CUSTOM_INDEXES = {
    "ix_reservations_patron_status",
    "ix_reservations_start_status",
    "ix_guest_pass_code",
    "ix_policy_category",
    "ix_waitlist_expires",
    "ix_waitlist_patron_status",
    "ix_volunteer_hour_logs_volunteer_date",
    "ix_fines_user_status",
}


def include_object(object, name, type_, reflected, compare_to):
    """Filter autogenerate output to reduce noise."""
    if type_ == "table" and name in EXCLUDE_TABLES:
        return False
    return True



def process_revision_directives(context, revision, directives):
    """Filter out pre-existing cosmetic diffs from autogenerate output.

    The DB was created by raw SQL without comments, FK ondelete, or some
    indexes. These show up as diffs but are not real schema changes.
    """
    if not directives:
        return
    script = directives[0]
    if not script.upgrade_ops:
        return

    def _is_comment_only_alter(op_obj):
        """True if AlterColumnOp only changes the comment."""
        if not isinstance(op_obj, ops.AlterColumnOp):
            return False
        return (
            op_obj.modify_comment is not False  # has a comment change
            and op_obj.modify_nullable is None
            and op_obj.modify_type is None
            and op_obj.modify_name is None
            and op_obj.modify_server_default is False
        )

    def _keep(op_obj):
        """Return False for ops we want to suppress."""
        # Known indexes that already exist but autogenerate can't match
        if isinstance(op_obj, ops.CreateIndexOp):
            if getattr(op_obj, "index_name", None) in EXISTING_CUSTOM_INDEXES:
                return False

        # Known unique constraint that already exists
        if isinstance(op_obj, ops.CreateUniqueConstraintOp):
            if getattr(op_obj, "constraint_name", None) == "uq_collection_ebook":
                return False

        # Comment-only alter_column
        if _is_comment_only_alter(op_obj):
            return False

        # ModifyTableOps containing only comment-only AlterColumnOps
        if isinstance(op_obj, ops.ModifyTableOps):
            if all(_is_comment_only_alter(sub) for sub in op_obj.ops):
                return False

        return True

    def _is_fk_ondelete_pair(sub_ops, i):
        """Check if ops[i:i+2] is a drop FK + create FK that only adds ondelete."""
        if i + 1 >= len(sub_ops):
            return False
        drop = sub_ops[i]
        create = sub_ops[i + 1]
        return (
            isinstance(drop, ops.DropConstraintOp)
            and getattr(drop, "constraint_type", None) == "foreignkey"
            and isinstance(create, ops.CreateForeignKeyOp)
            and create.kw.get("ondelete")
        )

    def _is_index_unique_reshuffle(sub_ops, i):
        """Check if ops[i:i+3] is drop_unique + drop_index + create_index(unique)."""
        if i + 2 >= len(sub_ops):
            return False
        return (
            isinstance(sub_ops[i], ops.DropConstraintOp)
            and getattr(sub_ops[i], "constraint_type", None) == "unique"
            and isinstance(sub_ops[i + 1], ops.DropIndexOp)
            and isinstance(sub_ops[i + 2], ops.CreateIndexOp)
            and getattr(sub_ops[i + 2], "unique", False)
        )

    def _filter_sub_ops(sub_ops):
        """Filter sub-ops within a ModifyTableOps."""
        filtered = []
        i = 0
        while i < len(sub_ops):
            # FK ondelete pair
            if _is_fk_ondelete_pair(sub_ops, i):
                i += 2
                continue
            # Unique constraint → unique index reshuffle
            if _is_index_unique_reshuffle(sub_ops, i):
                i += 3
                continue
            if _keep(sub_ops[i]):
                filtered.append(sub_ops[i])
            i += 1
        return filtered

    def _filter_top_ops(raw_ops):
        """Filter top-level ops (ModifyTableOps containers)."""
        filtered = []
        for op_obj in raw_ops:
            if isinstance(op_obj, ops.ModifyTableOps):
                op_obj.ops = _filter_sub_ops(op_obj.ops)
                if op_obj.ops:  # keep only if sub-ops remain
                    filtered.append(op_obj)
            elif _keep(op_obj):
                filtered.append(op_obj)
        return filtered

    script.upgrade_ops.ops = _filter_top_ops(script.upgrade_ops.ops)

    # If nothing real remains, suppress the revision entirely
    if not script.upgrade_ops.ops:
        directives[:] = []


# Configure which comparison dimensions to include.
# compare_type=True catches column type changes.
# compare_server_default=False ignores server_default diffs (noisy with asyncpg).
CONTEXT_OPTS = dict(
    target_metadata=target_metadata,
    include_object=include_object,
    process_revision_directives=process_revision_directives,
    compare_type=True,
    compare_server_default=False,
)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL script without connecting to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **CONTEXT_OPTS,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, **CONTEXT_OPTS)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
