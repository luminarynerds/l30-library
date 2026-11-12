
import asyncio
import logging
from app.core.logging import get_logger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import AsyncSessionLocal

logger = get_logger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def fix_sequences():
    async with AsyncSessionLocal() as db:
        # Get all sequences owned by columns (serial/identity)
        result = await db.execute(text("""
            SELECT s.relname AS seq_name,
                   t.relname AS table_name,
                   a.attname AS col_name
            FROM pg_class s
            JOIN pg_depend d ON d.objid = s.oid
            JOIN pg_class t ON t.oid = d.refobjid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
            WHERE s.relkind = 'S'
              AND d.deptype = 'a'
              AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            ORDER BY t.relname
        """))
        sequences = result.fetchall()

        fixed = 0
        skipped = 0
        for seq_name, table_name, col_name in sequences:
            try:
                r = await db.execute(text(
                    f'SELECT setval(:seq, COALESCE((SELECT MAX("{col_name}") FROM "{table_name}"), 1))'
                ), {"seq": seq_name})
                new_val = r.scalar()
                fixed += 1
            except SQLAlchemyError:
                skipped += 1

        await db.commit()
        logger.info(f"Fixed {fixed} sequences, skipped {skipped}")


if __name__ == "__main__":
    asyncio.run(fix_sequences())
