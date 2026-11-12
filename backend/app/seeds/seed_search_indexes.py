# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


async def seed_search_indexes(session: AsyncSession) -> None:

    is_generated = await session.execute(text("""
        SELECT attgenerated = 's'
        FROM pg_attribute
        WHERE attrelid = 'catalog_items'::regclass
          AND attname = 'search_tsv'
          AND NOT attisdropped
    """))
    is_generated_value = is_generated.scalar()

    if not is_generated_value:
        # Trigger-managed path (pre-migration deployments). The migration
        # supersedes this whole branch.
        await session.execute(text(
            "ALTER TABLE catalog_items ADD COLUMN IF NOT EXISTS search_tsv tsvector"
        ))

        await session.execute(text("""
            CREATE OR REPLACE FUNCTION catalog_items_search_tsv_update() RETURNS trigger AS $$
            BEGIN
              NEW.search_tsv :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.author, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.subjects, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'D');
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """))

        await session.execute(text(
            "DROP TRIGGER IF EXISTS catalog_items_search_tsv_trigger ON catalog_items"
        ))
        await session.execute(text("""
            CREATE TRIGGER catalog_items_search_tsv_trigger
              BEFORE INSERT OR UPDATE OF title, author, subjects, description
              ON catalog_items
              FOR EACH ROW
              EXECUTE FUNCTION catalog_items_search_tsv_update()
        """))

        result = await session.execute(text(
            "UPDATE catalog_items SET title = title WHERE search_tsv IS NULL"
        ))
        populated = result.rowcount
        if populated:
            logger.info(f"Populated search_tsv for {populated} catalog items")

    # GIN index is created in either path (IF NOT EXISTS is idempotent).
    await session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_catalog_items_search_tsv "
        "ON catalog_items USING gin (search_tsv)"
    ))
    await session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_catalog_items_title_trgm "
        "ON catalog_items USING gin (title gin_trgm_ops)"
    ))
    await session.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_catalog_items_author_trgm "
        "ON catalog_items USING gin (author gin_trgm_ops)"
    ))

    # 6. Fix ALL uppercase PG enum values -> lowercase
    #    Two cases:
    #    A) Uppercase label exists, lowercase doesn't -> RENAME VALUE
    #    B) Both exist (collision) -> UPDATE data rows to lowercase, leave stale uppercase label
    #       (PG doesn't support DROP VALUE on enums, but the stale label is harmless once no data references it)
    rows = await session.execute(text("""
        SELECT t.typname, e.enumlabel
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE e.enumlabel != LOWER(e.enumlabel)
          AND t.typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        ORDER BY t.typname, e.enumsortorder
    """))
    enum_fixes = rows.fetchall()
    renamed = 0
    migrated = 0
    for typname, label in enum_fixes:
        lower_label = label.lower()
        # Check if lowercase version already exists (would cause collision on rename)
        exists = await session.execute(text(
            "SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid "
            "WHERE t.typname = :typname AND e.enumlabel = :label"
        ), {"typname": typname, "label": lower_label})
        if exists.scalar():
            # Both uppercase and lowercase exist -- update data rows to lowercase
            # Find all columns using this enum type and migrate data
            cols = await session.execute(text("""
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE udt_name = :typname
            """), {"typname": typname})
            for table_name, column_name in cols.fetchall():
                result = await session.execute(text(
                    f'UPDATE "{table_name}" SET "{column_name}" = :new_val '
                    f'WHERE "{column_name}" = :old_val'
                ), {"old_val": label, "new_val": lower_label})
                if result.rowcount > 0:
                    migrated += result.rowcount
                    logger.info(f"Migrated {result.rowcount} rows in {table_name}.{column_name}: {label} -> {lower_label}")
        else:
            await session.execute(text(
                f"ALTER TYPE {typname} RENAME VALUE :old_val TO :new_val"
            ), {"old_val": label, "new_val": lower_label})
            renamed += 1

    if renamed or migrated:
        logger.info(f"Enum fix: renamed {renamed} type values, migrated {migrated} data rows to lowercase")

    await session.commit()
    logger.info("Search indexes and triggers configured")
    return True
