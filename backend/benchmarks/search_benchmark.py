# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Search Benchmark: PostgreSQL FTS vs ILIKE on 100k records.

Measures p50/p95 latency for:
1. ILIKE-based search (current baseline)
2. PostgreSQL tsvector/tsquery full-text search (new)
3. Trigram similarity search (new)
4. Hybrid FTS + semantic search (new)

Usage:
    # Seed 100k records and run benchmark
    python -m benchmarks.search_benchmark --seed --count 100000

    # Run benchmark only (assumes data exists)
    python -m benchmarks.search_benchmark

    # Run with custom iterations
    python -m benchmarks.search_benchmark --iterations 200

Requires:
    - PostgreSQL with pg_trgm extension
    - tsvector columns and GIN indexes (run alembic migration first)
    - DATABASE_URL environment variable
"""

import argparse
import asyncio
import logging
import os
import random
import statistics
import string
import sys
import time
from typing import Any

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Sample data for seeding
SAMPLE_TITLES = [
    "The Great Gatsby", "To Kill a Mockingbird", "1984", "Pride and Prejudice",
    "The Catcher in the Rye", "Lord of the Flies", "The Grapes of Wrath",
    "Brave New World", "Slaughterhouse-Five", "One Hundred Years of Solitude",
    "The Old Man and the Sea", "Animal Farm", "A Tale of Two Cities",
    "Fahrenheit 451", "Of Mice and Men", "Moby-Dick", "War and Peace",
    "Crime and Punishment", "Don Quixote", "The Odyssey", "Jane Eyre",
    "Wuthering Heights", "Great Expectations", "The Brothers Karamazov",
    "Anna Karenina", "Catch-22", "Heart of Darkness", "The Sun Also Rises",
    "Beloved", "Invisible Man", "The Color Purple", "Things Fall Apart",
    "The Road", "Blood Meridian", "Neuromancer", "Dune",
    "Foundation", "Ender's Game", "The Handmaid's Tale", "Kafka on the Shore",
]

SAMPLE_AUTHORS = [
    "F. Scott Fitzgerald", "Harper Lee", "George Orwell", "Jane Austen",
    "J.D. Salinger", "William Golding", "John Steinbeck", "Aldous Huxley",
    "Kurt Vonnegut", "Gabriel Garcia Marquez", "Ernest Hemingway",
    "Charles Dickens", "Ray Bradbury", "Herman Melville", "Leo Tolstoy",
    "Fyodor Dostoevsky", "Miguel de Cervantes", "Homer", "Charlotte Bronte",
    "Emily Bronte", "Joseph Heller", "Joseph Conrad", "Toni Morrison",
    "Ralph Ellison", "Alice Walker", "Chinua Achebe", "Cormac McCarthy",
    "William Gibson", "Frank Herbert", "Isaac Asimov", "Orson Scott Card",
    "Margaret Atwood", "Haruki Murakami", "Stephen King", "Neil Gaiman",
]

SAMPLE_SUBJECTS = [
    "fiction, classic, american literature",
    "fiction, dystopian, science fiction",
    "fiction, romance, british literature",
    "fiction, war, history",
    "non-fiction, science, physics",
    "non-fiction, biography, history",
    "fiction, mystery, thriller",
    "fiction, fantasy, adventure",
    "non-fiction, philosophy, ethics",
    "fiction, horror, supernatural",
    "non-fiction, technology, computers",
    "fiction, literary fiction, modernism",
    "non-fiction, self-help, psychology",
    "fiction, young adult, coming of age",
    "non-fiction, nature, environment",
]

# Queries to benchmark (mix of common patterns)
BENCHMARK_QUERIES = [
    # Simple single-word queries
    "python", "history", "garden", "mystery", "science",
    # Multi-word queries
    "harry potter", "machine learning", "civil war", "climate change",
    "organic chemistry", "world history", "data science",
    # Author-like queries
    "Stephen King", "J.K. Rowling", "Tolkien", "Hemingway",
    # Misspelled queries (trigram should handle)
    "hary poter", "tolk1en", "gardning", "scince fiction",
    # Phrase queries
    "great american novel", "space exploration for beginners",
    "introduction to programming", "history of ancient rome",
    # Short queries
    "AI", "Go", "art",
]


async def seed_catalog_items(count: int = 100_000) -> None:
    """Seed the catalog_items table with synthetic data for benchmarking."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    database_url = os.environ["DATABASE_URL"]  # Required - no hardcoded credentials
    engine = create_async_engine(database_url, pool_size=5)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    logger.info(f"Seeding {count:,} catalog items...")

    batch_size = 1000
    total_inserted = 0

    async with async_session() as session:
        # Check existing count
        result = await session.execute(text("SELECT count(*) FROM catalog_items"))
        existing = result.scalar() or 0
        logger.info(f"Existing items: {existing:,}")

        if existing >= count:
            logger.info(f"Already have {existing:,} items, skipping seed.")
            await engine.dispose()
            return

        remaining = count - existing

        for batch_start in range(0, remaining, batch_size):
            batch_end = min(batch_start + batch_size, remaining)
            values = []

            for i in range(batch_start, batch_end):
                title_base = random.choice(SAMPLE_TITLES)
                suffix = f" Vol. {random.randint(1, 99)}" if random.random() > 0.5 else ""
                prefix = random.choice(["The Complete ", "Essential ", "New ", "Modern ", ""]) if random.random() > 0.7 else ""
                title = f"{prefix}{title_base}{suffix}"

                author = random.choice(SAMPLE_AUTHORS)
                subjects = random.choice(SAMPLE_SUBJECTS)
                description = f"A compelling work by {author} exploring themes of {subjects.split(',')[0].strip()}. " * random.randint(1, 3)
                item_type = random.choice(["book", "audiobook", "ebook", "dvd", "cd", "magazine"])
                status = random.choice(["available", "checked_out", "on_hold", "in_transit", "available", "available"])
                year = random.randint(1900, 2025)
                location = random.choice(["Main Library", "East Branch", "West Branch", "Downtown", "Mobile Unit"])
                isbn = "".join(random.choices(string.digits, k=13)) if random.random() > 0.3 else None

                values.append({
                    "title": title,
                    "author": author,
                    "subjects": subjects,
                    "description": description,
                    "item_type": item_type,
                    "status": status,
                    "publication_year": year,
                    "location": location,
                    "isbn": isbn,
                })

            # Bulk insert
            placeholders = []
            params = {}
            for j, v in enumerate(values):
                idx = batch_start + j
                placeholders.append(
                    f"(:title_{idx}, :author_{idx}, :subjects_{idx}, :description_{idx}, "
                    f":item_type_{idx}, :status_{idx}, :pub_year_{idx}, :location_{idx}, :isbn_{idx})"
                )
                params[f"title_{idx}"] = v["title"]
                params[f"author_{idx}"] = v["author"]
                params[f"subjects_{idx}"] = v["subjects"]
                params[f"description_{idx}"] = v["description"]
                params[f"item_type_{idx}"] = v["item_type"]
                params[f"status_{idx}"] = v["status"]
                params[f"pub_year_{idx}"] = v["publication_year"]
                params[f"location_{idx}"] = v["location"]
                params[f"isbn_{idx}"] = v["isbn"]

            insert_sql = f"""
                INSERT INTO catalog_items (title, author, subjects, description,
                    item_type, status, publication_year, location, isbn)
                VALUES {', '.join(placeholders)}
            """
            await session.execute(text(insert_sql), params)
            await session.commit()

            total_inserted += len(values)
            if total_inserted % 10_000 == 0:
                logger.info(f"  Inserted {total_inserted:,}/{remaining:,}")

    logger.info(f"Seeding complete. Total inserted: {total_inserted:,}")
    await engine.dispose()


async def run_benchmark(iterations: int = 100) -> dict[str, Any]:
    """Run search benchmarks comparing ILIKE, FTS, and trigram approaches."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    database_url = os.environ["DATABASE_URL"]  # Required - no hardcoded credentials
    engine = create_async_engine(database_url, pool_size=5)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    results: dict[str, list[float]] = {
        "ilike": [],
        "fts_tsquery": [],
        "trigram": [],
    }

    async with async_session() as session:
        # Get record count
        count_result = await session.execute(text("SELECT count(*) FROM catalog_items"))
        record_count = count_result.scalar() or 0
        logger.info(f"Benchmarking against {record_count:,} records")
        logger.info(f"Running {iterations} iterations per search type")
        logger.info("")

        for i in range(iterations):
            query = random.choice(BENCHMARK_QUERIES)

            # --- ILIKE baseline ---
            start = time.perf_counter()
            await session.execute(text("""
                SELECT id, title, author FROM catalog_items
                WHERE title ILIKE :pattern OR author ILIKE :pattern
                OR description ILIKE :pattern OR subjects ILIKE :pattern
                ORDER BY title LIMIT 20
            """), {"pattern": f"%{query}%"})
            results["ilike"].append((time.perf_counter() - start) * 1000)

            # --- FTS tsquery ---
            start = time.perf_counter()
            # Build simple tsquery (last word prefix match)
            words = query.split()
            if len(words) == 1:
                tsq = f"{words[0]}:*"
            else:
                tsq = " & ".join(words[:-1]) + f" & {words[-1]}:*"

            await session.execute(text("""
                SELECT id, title, author,
                       ts_rank_cd(search_tsv, to_tsquery('english', :tsq), 32) AS rank
                FROM catalog_items
                WHERE search_tsv @@ to_tsquery('english', :tsq)
                ORDER BY rank DESC LIMIT 20
            """), {"tsq": tsq})
            results["fts_tsquery"].append((time.perf_counter() - start) * 1000)

            # --- Trigram similarity ---
            start = time.perf_counter()
            await session.execute(text("""
                SELECT id, title, author,
                       similarity(title, :q) AS sim
                FROM catalog_items
                WHERE similarity(title, :q) > 0.3
                   OR similarity(author, :q) > 0.3
                ORDER BY sim DESC LIMIT 20
            """), {"q": query})
            results["trigram"].append((time.perf_counter() - start) * 1000)

            if (i + 1) % 25 == 0:
                logger.info(f"  Completed {i + 1}/{iterations} iterations")

    await engine.dispose()

    # Compute statistics
    report = {"record_count": record_count, "iterations": iterations, "benchmarks": {}}

    for name, latencies in results.items():
        sorted_lat = sorted(latencies)
        p50_idx = int(len(sorted_lat) * 0.50)
        p95_idx = int(len(sorted_lat) * 0.95)

        stats = {
            "p50_ms": round(sorted_lat[p50_idx], 2),
            "p95_ms": round(sorted_lat[p95_idx], 2),
            "min_ms": round(min(sorted_lat), 2),
            "max_ms": round(max(sorted_lat), 2),
            "mean_ms": round(statistics.mean(sorted_lat), 2),
            "stddev_ms": round(statistics.stdev(sorted_lat), 2) if len(sorted_lat) > 1 else 0,
        }
        report["benchmarks"][name] = stats

    return report


def print_report(report: dict[str, Any]) -> None:
    """Print a formatted benchmark report."""
    logger.info("=" * 72)
    logger.info("SEARCH BENCHMARK RESULTS")
    logger.info(f"Records: {report['record_count']:,}  |  Iterations: {report['iterations']}")
    logger.info("=" * 72)
    logger.info("")
    logger.info(f"{'Method':<20} {'p50 (ms)':>10} {'p95 (ms)':>10} {'Mean (ms)':>10} {'StdDev':>10}")
    logger.info("-" * 72)

    for name, stats in report["benchmarks"].items():
        logger.info(
            f"{name:<20} {stats['p50_ms']:>10.2f} {stats['p95_ms']:>10.2f} "
            f"{stats['mean_ms']:>10.2f} {stats['stddev_ms']:>10.2f}"
        )

    logger.info("-" * 72)
    logger.info("")

    # Speedup comparison
    ilike = report["benchmarks"].get("ilike", {})
    fts = report["benchmarks"].get("fts_tsquery", {})
    trigram = report["benchmarks"].get("trigram", {})

    if ilike and fts:
        if fts["p50_ms"] > 0:
            speedup_p50 = ilike["p50_ms"] / fts["p50_ms"]
            logger.info(f"FTS vs ILIKE speedup (p50): {speedup_p50:.1f}x")
        if fts["p95_ms"] > 0:
            speedup_p95 = ilike["p95_ms"] / fts["p95_ms"]
            logger.info(f"FTS vs ILIKE speedup (p95): {speedup_p95:.1f}x")

    if ilike and trigram:
        if trigram["p50_ms"] > 0:
            speedup_p50 = ilike["p50_ms"] / trigram["p50_ms"]
            logger.info(f"Trigram vs ILIKE speedup (p50): {speedup_p50:.1f}x")

    logger.info("")


async def main():
    parser = argparse.ArgumentParser(description="Search Benchmark: PostgreSQL FTS vs ILIKE")
    parser.add_argument("--seed", action="store_true", help="Seed 100k records before benchmarking")
    parser.add_argument("--count", type=int, default=100_000, help="Number of records to seed (default: 100000)")
    parser.add_argument("--iterations", type=int, default=100, help="Benchmark iterations per search type")
    args = parser.parse_args()

    if args.seed:
        await seed_catalog_items(args.count)
        logger.info("")

    report = await run_benchmark(args.iterations)
    print_report(report)


if __name__ == "__main__":
    asyncio.run(main())
