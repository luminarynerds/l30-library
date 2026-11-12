# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.reading_status import ReadingStatus


def _is_postgresql(db: AsyncSession) -> bool:
    return db.bind.dialect.name == "postgresql"


class PatronTagsService:

    @staticmethod
    async def get_all_tags(db: AsyncSession, user_id: int) -> list[str]:
        if _is_postgresql(db):
            result = await db.execute(
                text(
                    "SELECT DISTINCT tag "
                    "FROM reading_statuses, "
                    "jsonb_array_elements_text(personal_tags::jsonb) AS tag "
                    "WHERE user_id = :user_id "
                    "ORDER BY tag"
                ),
                {"user_id": user_id},
            )
            return [row[0] for row in result]

        # SQLite fallback
        result = await db.execute(
            select(ReadingStatus.personal_tags)
            .where(ReadingStatus.user_id == user_id)
        )
        all_tags: set[str] = set()
        for (tags,) in result:
            if tags:
                all_tags.update(tags)
        return sorted(all_tags)

    @staticmethod
    async def rename_tag(
        db: AsyncSession, user_id: int, old_name: str, new_name: str
    ) -> int:
        if _is_postgresql(db):
            result = await db.execute(
                text(
                    "UPDATE reading_statuses "
                    "SET personal_tags = ("
                    "  SELECT jsonb_agg("
                    "    CASE WHEN elem = :old_name THEN :new_name ELSE elem END"
                    "  ) "
                    "  FROM jsonb_array_elements_text(personal_tags::jsonb) AS elem"
                    ") "
                    "WHERE user_id = :user_id "
                    "AND personal_tags::jsonb @> to_jsonb(CAST(:old_name AS text))"
                ),
                {"user_id": user_id, "old_name": old_name, "new_name": new_name},
            )
            count = result.rowcount
            if count > 0:
                await db.commit()
            return count

        # SQLite fallback
        result = await db.execute(
            select(ReadingStatus)
            .where(ReadingStatus.user_id == user_id)
        )
        entries = list(result.scalars().all())
        count = 0
        for entry in entries:
            tags = list(entry.personal_tags or [])
            if old_name in tags:
                tags = [new_name if t == old_name else t for t in tags]
                entry.personal_tags = tags
                count += 1
        if count > 0:
            await db.commit()
        return count

    @staticmethod
    async def delete_tag(db: AsyncSession, user_id: int, tag_name: str) -> int:
        if _is_postgresql(db):
            result = await db.execute(
                text(
                    "UPDATE reading_statuses "
                    "SET personal_tags = ("
                    "  SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb) "
                    "  FROM jsonb_array_elements_text(personal_tags::jsonb) AS elem "
                    "  WHERE elem != :tag_name"
                    ") "
                    "WHERE user_id = :user_id "
                    "AND personal_tags::jsonb @> to_jsonb(CAST(:tag_name AS text))"
                ),
                {"user_id": user_id, "tag_name": tag_name},
            )
            count = result.rowcount
            if count > 0:
                await db.commit()
            return count

        # SQLite fallback
        result = await db.execute(
            select(ReadingStatus)
            .where(ReadingStatus.user_id == user_id)
        )
        entries = list(result.scalars().all())
        count = 0
        for entry in entries:
            tags = list(entry.personal_tags or [])
            if tag_name in tags:
                tags = [t for t in tags if t != tag_name]
                entry.personal_tags = tags
                count += 1
        if count > 0:
            await db.commit()
        return count
