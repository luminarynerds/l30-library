#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Trending System Demo and Test Script

This script demonstrates the trending system functionality by:
1. Showing current trending books
2. Calculating trending scores for all active books
3. Displaying the trending formula breakdown

Usage:
    python scripts/test_trending_demo.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.services.trending_service import get_trending_service
from app.models.indie_author import IndieEbook, EbookSubmissionStatus


async def display_trending_demo():
    """Display trending books with calculation breakdown."""
    print("=" * 80)
    print("INDIE EBOOK TRENDING SYSTEM DEMO")
    print("=" * 80)
    print()

    async with AsyncSessionLocal() as db:
        trending_service = get_trending_service()

        # Get trending books for different time periods
        periods = ["7d", "30d", "90d"]

        for period in periods:
            print(f"\n{'='*80}")
            print(f"TOP 10 TRENDING BOOKS - {period.upper()} PERIOD")
            print(f"{'='*80}\n")

            trending_books = await trending_service.get_trending_books(
                db=db,
                limit=10,
                period=period,
                use_cache=False  # Force fresh calculation for demo
            )

            if not trending_books:
                print(f"No trending books found for {period} period.\n")
                continue

            # Display results in a table format
            print(f"{'Rank':<6} {'Title':<40} {'Score':<8} {'7d':<6} {'30d':<6} {'Rating':<8}")
            print("-" * 80)

            for idx, book in enumerate(trending_books, 1):
                title = book['title'][:37] + "..." if len(book['title']) > 40 else book['title']
                rating = f"{book['average_rating']:.1f}" if book['average_rating'] else "N/A"

                print(f"{idx:<6} {title:<40} {book['trending_score']:<8.2f} "
                      f"{book['borrows_7d']:<6} {book['borrows_30d']:<6} {rating:<8}")

            print()

        # Show trending formula breakdown for top book
        print(f"\n{'='*80}")
        print("TRENDING SCORE FORMULA BREAKDOWN")
        print(f"{'='*80}\n")

        print("Formula: (borrows_last_7_days × 3) + (borrows_last_30_days × 1) + (average_rating × 2)")
        print()

        top_trending = await trending_service.get_trending_books(
            db=db,
            limit=1,
            period="7d",
            use_cache=False
        )

        if top_trending:
            book = top_trending[0]
            print(f"Top Trending Book: {book['title']}")
            print(f"  - Borrows (7 days):  {book['borrows_7d']} × 3 = {book['borrows_7d'] * 3}")
            print(f"  - Borrows (30 days): {book['borrows_30d']} × 1 = {book['borrows_30d']}")

            if book['average_rating']:
                rating_score = book['average_rating'] * 2
                print(f"  - Average Rating:    {book['average_rating']:.2f} × 2 = {rating_score:.2f}")
            else:
                rating_score = 0
                print("  - Average Rating:    N/A × 2 = 0")

            total = (book['borrows_7d'] * 3) + book['borrows_30d'] + rating_score
            print(f"  - TOTAL SCORE:       {total:.2f}")
            print()

        # Show cache performance
        print(f"\n{'='*80}")
        print("CACHE PERFORMANCE TEST")
        print(f"{'='*80}\n")

        # First call (should calculate)
        start_time = datetime.now(timezone.utc)
        await trending_service.get_trending_books(db=db, limit=20, period="7d", use_cache=True)
        first_call_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        # Second call (should use cache)
        start_time = datetime.now(timezone.utc)
        await trending_service.get_trending_books(db=db, limit=20, period="7d", use_cache=True)
        second_call_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        print(f"First call (calculation):  {first_call_ms:.2f}ms")
        print(f"Second call (cached):      {second_call_ms:.2f}ms")
        print(f"Speedup:                   {first_call_ms / second_call_ms:.1f}x faster")
        print()

        # Update scores in database
        print(f"\n{'='*80}")
        print("UPDATING DATABASE TRENDING SCORES")
        print(f"{'='*80}\n")

        print("Calculating and storing trending scores for all active books...")
        updated_count = await trending_service.bulk_update_trending_scores(db, batch_size=100)
        print(f"Successfully updated {updated_count} ebooks with trending scores.\n")

        # Show genre-specific trending
        print(f"\n{'='*80}")
        print("GENRE-SPECIFIC TRENDING")
        print(f"{'='*80}\n")

        # Get all unique genres
        from sqlalchemy import select, distinct
        result = await db.execute(
            select(distinct(IndieEbook.genre))
            .where(
                IndieEbook.submission_status == EbookSubmissionStatus.approved,
                IndieEbook.lending_enabled == True,
                IndieEbook.genre.isnot(None)
            )
        )
        genres = result.scalars().all()

        if genres:
            for genre in genres[:5]:  # Show first 5 genres
                genre_trending = await trending_service.get_trending_books(
                    db=db,
                    limit=3,
                    genre=genre,
                    period="7d",
                    use_cache=False
                )

                if genre_trending:
                    print(f"\nTop 3 in {genre}:")
                    for idx, book in enumerate(genre_trending, 1):
                        print(f"  {idx}. {book['title']} (Score: {book['trending_score']:.2f})")
        else:
            print("No genres found in the database.\n")

        print()
        print("=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        print()
        print("API Endpoints available:")
        print("  - GET /api/v1/indie/trending")
        print("  - GET /api/v1/indie/trending/{genre}")
        print("  - GET /api/v1/indie/catalog?sort_by=trending")
        print()


async def main():
    """Entry point."""
    try:
        await display_trending_demo()
        return 0
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
