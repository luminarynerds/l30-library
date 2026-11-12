#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
One-off: catalog-wide cover backfill (the /picks pass writ large).

Re-resolves real covers for every book/audiobook/ebook and cd/vinyl/dvd/bluray
whose cover_url is NULL or a doomed covers.openlibrary.org/b/isbn URL.

  - books/audio/ebook -> Open Library search by title+author, guarded by
    author-surname + normalized-title match (no fuzzy wrong-cover).
  - cd/vinyl/dvd/bluray -> iTunes.

Status-aware so a transient rate-limit can't destroy data:
  FOUND   -> set cover_url
  NOMATCH -> (API answered, nothing matched) null a broken b/isbn URL so the
             clean fallback renders; leave already-null rows untouched.
  ERROR   -> (network / 429 after retries) leave the row UNCHANGED for a re-run.

Idempotent. Dry-run by default; --apply to write. Commits every 25 changes.

    docker exec -d l30-backend sh -c \\
      'python scripts/catalog_cover_backfill.py --apply > /tmp/cover_backfill.log 2>&1'
"""
import sys, os, re, asyncio, logging

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

APPLY = "--apply" in sys.argv
DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

OL_SEARCH = "https://openlibrary.org/search.json"
OL_COVER_ID = "https://covers.openlibrary.org/b/id"
ITUNES_API = "https://itunes.apple.com/search"

QUERY = """
    SELECT id, title, author, artist, item_type, cover_url
    FROM catalog_items
    WHERE (cover_url IS NULL OR cover_url LIKE '%openlibrary.org/b/isbn%')
      AND item_type IN ('book','audiobook','ebook','cd','vinyl','dvd','bluray')
    ORDER BY id
"""


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def search_title(t):
    return re.sub(r"\s*\([^)]*\)\s*$", "", t or "").strip()


def title_matches(q, got):
    a, b = norm(search_title(q)), norm(got)
    return bool(a and b and (a == b or a in b or b in a))


def author_matches(q_author, got_authors):
    if not q_author:
        return False
    toks = norm(q_author.split(",")[0]).split()
    if not toks or len(toks[-1]) < 3:
        return False
    return toks[-1] in norm(" ".join(got_authors or [])).split()


async def fetch(client, url, **kw):
    """GET with retry/backoff on 429 and transient errors. None == give up (ERROR)."""
    for attempt in range(3):
        try:
            r = await client.get(url, **kw)
        except Exception:
            await asyncio.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code == 429:
            await asyncio.sleep(3.0 * (attempt + 1))
            continue
        return r
    return None


async def is_real_image(client, url):
    r = await fetch(client, url, follow_redirects=True)
    if r is None:
        return False
    return (r.status_code == 200
            and r.headers.get("content-type", "").startswith("image/")
            and len(r.content) > 1500)


async def resolve_book(client, title, author):
    """Returns (status, url): FOUND/NOMATCH/ERROR."""
    if not title:
        return ("NOMATCH", None)
    r = await fetch(client, OL_SEARCH, params={
        "title": search_title(title), "author": author or "",
        "fields": "title,author_name,cover_i", "limit": 3})
    if r is None or r.status_code != 200:
        return ("ERROR", None)
    try:
        docs = r.json().get("docs", [])
    except Exception:
        return ("ERROR", None)
    for d in docs:
        cid = d.get("cover_i")
        if (cid and title_matches(title, d.get("title", ""))
                and (not author or author_matches(author, d.get("author_name", [])))):
            url = f"{OL_COVER_ID}/{cid}-M.jpg"
            if await is_real_image(client, url):
                return ("FOUND", url)
    return ("NOMATCH", None)


async def resolve_itunes(client, term, media, entity):
    r = await fetch(client, ITUNES_API,
                    params={"term": term, "media": media, "entity": entity, "limit": 1})
    if r is None or r.status_code != 200:
        return ("ERROR", None)
    try:
        results = r.json().get("results", [])
    except Exception:
        return ("ERROR", None)
    if results:
        art = results[0].get("artworkUrl100", "")
        if art:
            cand = art.replace("100x100bb", "600x600bb")
            if await is_real_image(client, cand):
                return ("FOUND", cand)
    return ("NOMATCH", None)


async def main():
    log.info(f"catalog cover backfill ({'APPLY' if APPLY else 'DRY-RUN'})")
    async with async_session() as db:
        rows = (await db.execute(text(QUERY))).fetchall()
        total = len(rows)
        log.info(f"{total} items to process\n")

        found = nulled = errored = nomatch_null0 = 0
        pending = 0
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True,
                headers={"User-Agent": "l30-cover-backfill/1.0 (library demo)"}) as client:
            for n, (item_id, title, author, artist, item_type, old) in enumerate(rows, 1):
                if item_type in ("book", "audiobook", "ebook"):
                    status, url = await resolve_book(client, title, author)
                elif item_type in ("cd", "vinyl"):
                    status, url = await resolve_itunes(
                        client, f"{artist or author or ''} {title}".strip(), "music", "album")
                else:  # dvd, bluray
                    status, url = await resolve_itunes(client, title, "movie", "movie")

                if status == "FOUND":
                    found += 1
                    if APPLY:
                        await db.execute(text(
                            "UPDATE catalog_items SET cover_url=:u WHERE id=:i"),
                            {"u": url, "i": item_id}); pending += 1
                elif status == "NOMATCH":
                    if old and "openlibrary.org/b/isbn" in old:
                        nulled += 1
                        if APPLY:
                            await db.execute(text(
                                "UPDATE catalog_items SET cover_url=NULL WHERE id=:i"),
                                {"i": item_id}); pending += 1
                    else:
                        nomatch_null0 += 1  # already null, nothing to do
                else:
                    errored += 1

                if APPLY and pending >= 25:
                    await db.commit(); pending = 0

                if n % 50 == 0:
                    log.info(f"  [{n}/{total}] found={found} nulled={nulled} "
                             f"err={errored} alreadynull={nomatch_null0}")
                await asyncio.sleep(0.6)

            if APPLY:
                await db.commit()

    log.info(f"\nDONE: found={found} nulled={nulled} errored={errored} "
             f"already-null={nomatch_null0} of {total}"
             + ("" if APPLY else "  (dry-run)"))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
