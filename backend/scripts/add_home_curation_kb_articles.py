# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""One-off: insert the two home-curation KB articles on an existing install.

seed_staff_knowledge_base() skips entirely when any article exists, so
already-seeded databases never pick up additions to ARTICLES. This script
inserts just the new titles, skipping any that already exist.

Run from backend/: .venv/bin/python scripts/add_home_curation_kb_articles.py
(needs the same DB env the app uses)
"""
import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.models.knowledge_base import ArticleVersion, StaffKnowledgeArticle
from app.seeds.seed_staff_knowledge_base import ARTICLES

NEW_TITLES = [
    "Who Controls What Patrons See on the Home Page",
    "Staff Picks: Lists, the /picks Page, and the Home Shelf",
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            text("SELECT id FROM users WHERE role IN ('super_admin','admin') ORDER BY id LIMIT 1")
        )
        admin_row = res.fetchone()
        admin_id = admin_row[0] if admin_row else 1

        for data in ARTICLES:
            if data["title"] not in NEW_TITLES:
                continue
            exists = await db.execute(
                select(StaffKnowledgeArticle.id).where(
                    StaffKnowledgeArticle.title == data["title"]
                )
            )
            if exists.scalar_one_or_none():
                print(f"skip (exists): {data['title']}")
                continue
            article = StaffKnowledgeArticle(
                title=data["title"],
                description=data.get("description"),
                content=data["content"],
                content_type=data["content_type"],
                category=data["category"],
                subcategory=data.get("subcategory"),
                tags=data.get("tags"),
                is_published=True,
                created_by_id=admin_id,
                current_version=1,
            )
            db.add(article)
            await db.flush()
            db.add(
                ArticleVersion(
                    article_id=article.id,
                    version_number=1,
                    title=article.title,
                    content=article.content,
                    change_notes="Initial version",
                    changed_by_id=admin_id,
                )
            )
            print(f"inserted: {data['title']}")
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
