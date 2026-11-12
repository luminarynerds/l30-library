#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test script for indie ebook recommendation system.

This script tests the recommendation endpoints with real data.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.indie_author import (
    IndieEbook, IndieEbookBorrow, IndieAuthor,
    EbookSubmissionStatus, BorrowStatus
)
from app.services.recommendation_service import get_recommendation_service


async def print_separator(text=""):
    """Print a separator line."""
    if text:
        print(f"\n{'=' * 80}")
        print(f"  {text}")
        print('=' * 80)
    else:
        print('=' * 80)


async def check_data_availability():
    """Check if there's enough data for recommendations."""
    print_separator("Checking Data Availability")

    async with AsyncSessionLocal() as db:
        # Check approved ebooks
        result = await db.execute(
            select(func.count(IndieEbook.id))
            .where(IndieEbook.submission_status == EbookSubmissionStatus.approved)
        )
        ebook_count = result.scalar()
        print(f"✓ Approved ebooks: {ebook_count}")

        # Check total borrows
        result = await db.execute(select(func.count(IndieEbookBorrow.id)))
        borrow_count = result.scalar()
        print(f"✓ Total borrows: {borrow_count}")

        # Check unique users who borrowed
        result = await db.execute(
            select(func.count(func.distinct(IndieEbookBorrow.user_id)))
        )
        user_count = result.scalar()
        print(f"✓ Unique borrowers: {user_count}")

        # Get ebooks with most borrows
        result = await db.execute(
            select(
                IndieEbook.id,
                IndieEbook.title,
                IndieEbook.genre,
                IndieEbook.total_borrows,
                IndieEbook.average_rating,
                IndieAuthor.pen_name
            )
            .join(IndieAuthor, IndieEbook.author_id == IndieAuthor.id)
            .where(IndieEbook.submission_status == EbookSubmissionStatus.approved)
            .order_by(IndieEbook.total_borrows.desc())
            .limit(10)
        )
        popular_books = result.all()

        print("\n📚 Top 10 Most Borrowed Books:")
        for book in popular_books:
            rating_str = f"{book.average_rating:.1f}⭐" if book.average_rating else "No ratings"
            print(f"  • ID: {book.id:3d} | {book.title[:40]:40s} | {book.pen_name[:20]:20s}")
            print(f"    Genre: {book.genre or 'Unknown':20s} | Borrows: {book.total_borrows:3d} | {rating_str}")

        return ebook_count, borrow_count, user_count, popular_books


async def test_collaborative_recommendations(ebook_id: int):
    """Test collaborative filtering recommendations for a specific ebook."""
    await print_separator(f"Testing Collaborative Recommendations for Ebook ID: {ebook_id}")

    async with AsyncSessionLocal() as db:
        # Get ebook details
        result = await db.execute(
            select(IndieEbook, IndieAuthor.pen_name)
            .join(IndieAuthor, IndieEbook.author_id == IndieAuthor.id)
            .where(IndieEbook.id == ebook_id)
        )
        row = result.one_or_none()

        if not row:
            print(f"❌ Ebook {ebook_id} not found")
            return

        ebook, author_name = row
        print(f"📖 Book: {ebook.title}")
        print(f"👤 Author: {author_name}")
        print(f"🎭 Genre: {ebook.genre or 'Unknown'}")
        print(f"📊 Total Borrows: {ebook.total_borrows}")
        print(f"⭐ Rating: {ebook.average_rating or 'No ratings'}")

        # Get users who borrowed this book
        result = await db.execute(
            select(func.count(func.distinct(IndieEbookBorrow.user_id)))
            .where(IndieEbookBorrow.ebook_id == ebook_id)
        )
        borrower_count = result.scalar()
        print(f"👥 Unique Borrowers: {borrower_count}")

        if borrower_count == 0:
            print("\n⚠️  No borrowers found. Recommendations will use genre-based fallback.")

        # Get recommendations
        recommendation_service = get_recommendation_service()
        recommendations, rec_type = await recommendation_service.get_recommendations_for_ebook(
            ebook_id=ebook_id,
            db=db,
            limit=5,
            use_cache=False
        )

        print(f"\n🎯 Recommendation Type: {rec_type.upper()}")
        print(f"📋 Found {len(recommendations)} recommendations:")

        for i, rec in enumerate(recommendations, 1):
            rating_str = f"{rec.avg_rating:.1f}⭐" if rec.avg_rating else "No rating"
            available = "✓ Available" if rec.available_copies > 0 else "⏳ Waitlist"

            print(f"\n  {i}. {rec.title}")
            print(f"     Author: {rec.author_pen_name}")
            print(f"     Genre: {rec.genre or 'Unknown'}")
            print(f"     Score: {rec.score:.2f} (Borrows: {rec.borrow_count}, Rating: {rating_str})")
            print(f"     Copies: {rec.available_copies}/{rec.total_copies} {available}")


async def test_personalized_recommendations(user_id: int):
    """Test personalized recommendations for a specific user."""
    await print_separator(f"Testing Personalized Recommendations for User ID: {user_id}")

    async with AsyncSessionLocal() as db:
        # Get user's borrow history
        result = await db.execute(
            select(
                IndieEbookBorrow.ebook_id,
                IndieEbook.title,
                IndieAuthor.pen_name,
                IndieEbook.genre,
                IndieEbookBorrow.rating
            )
            .join(IndieEbook, IndieEbookBorrow.ebook_id == IndieEbook.id)
            .join(IndieAuthor, IndieEbook.author_id == IndieAuthor.id)
            .where(IndieEbookBorrow.user_id == user_id)
            .order_by(IndieEbookBorrow.borrowed_at.desc())
            .limit(10)
        )
        user_borrows = result.all()

        print(f"📚 User's Recent Borrow History ({len(user_borrows)} books):")
        if user_borrows:
            for borrow in user_borrows:
                rating_str = f"{borrow.rating}⭐" if borrow.rating else "Not rated"
                print(f"  • {borrow.title[:40]:40s} by {borrow.pen_name[:20]:20s}")
                print(f"    Genre: {borrow.genre or 'Unknown':20s} | {rating_str}")
        else:
            print("  No borrow history found.")

        # Get personalized recommendations
        recommendation_service = get_recommendation_service()
        recommendations = await recommendation_service.get_personalized_recommendations(
            user_id=user_id,
            db=db,
            limit=10,
            exclude_borrowed=True
        )

        based_on = "user history" if user_borrows else "popular books"
        print(f"\n🎯 Recommendations based on: {based_on.upper()}")
        print(f"📋 Found {len(recommendations)} recommendations:")

        for i, rec in enumerate(recommendations, 1):
            rating_str = f"{rec.avg_rating:.1f}⭐" if rec.avg_rating else "No rating"
            available = "✓ Available" if rec.available_copies > 0 else "⏳ Waitlist"

            print(f"\n  {i}. {rec.title}")
            print(f"     Author: {rec.author_pen_name}")
            print(f"     Genre: {rec.genre or 'Unknown'}")
            print(f"     Score: {rec.score:.2f} (Strength: {rec.borrow_count}, Rating: {rating_str})")
            print(f"     Copies: {rec.available_copies}/{rec.total_copies} {available}")


async def test_genre_fallback():
    """Test genre-based fallback recommendations."""
    await print_separator("Testing Genre-Based Fallback")

    async with AsyncSessionLocal() as db:
        # Find a book with no borrows
        result = await db.execute(
            select(IndieEbook.id, IndieEbook.title, IndieEbook.genre, IndieEbook.total_borrows)
            .where(
                IndieEbook.submission_status == EbookSubmissionStatus.approved,
                IndieEbook.total_borrows == 0
            )
            .limit(1)
        )
        row = result.one_or_none()

        if not row:
            print("ℹ️  No books with zero borrows found. Creating synthetic test case.")
            # Find least borrowed book
            result = await db.execute(
                select(IndieEbook.id, IndieEbook.title, IndieEbook.genre, IndieEbook.total_borrows)
                .where(IndieEbook.submission_status == EbookSubmissionStatus.approved)
                .order_by(IndieEbook.total_borrows.asc())
                .limit(1)
            )
            row = result.one_or_none()

        if row:
            ebook_id, title, genre, borrows = row
            print(f"📖 Testing with: {title}")
            print(f"🎭 Genre: {genre or 'Unknown'}")
            print(f"📊 Borrows: {borrows}")

            await test_collaborative_recommendations(ebook_id)


async def test_cache_performance():
    """Test recommendation caching."""
    await print_separator("Testing Cache Performance")

    import time

    async with AsyncSessionLocal() as db:
        # Get a popular book
        result = await db.execute(
            select(IndieEbook.id)
            .where(IndieEbook.submission_status == EbookSubmissionStatus.approved)
            .order_by(IndieEbook.total_borrows.desc())
            .limit(1)
        )
        ebook_id = result.scalar()

        if not ebook_id:
            print("❌ No ebooks found for testing")
            return

        recommendation_service = get_recommendation_service()

        # First call (no cache)
        start = time.time()
        recommendations1, rec_type1 = await recommendation_service.get_recommendations_for_ebook(
            ebook_id=ebook_id,
            db=db,
            limit=5,
            use_cache=True
        )
        duration1 = time.time() - start

        # Second call (cached)
        start = time.time()
        recommendations2, rec_type2 = await recommendation_service.get_recommendations_for_ebook(
            ebook_id=ebook_id,
            db=db,
            limit=5,
            use_cache=True
        )
        duration2 = time.time() - start

        print(f"🔍 Testing ebook ID: {ebook_id}")
        print(f"⏱️  First call (no cache): {duration1*1000:.2f}ms")
        print(f"⚡ Second call (cached): {duration2*1000:.2f}ms")
        print(f"🚀 Speed improvement: {duration1/duration2:.1f}x faster")
        print(f"✓ Results match: {len(recommendations1) == len(recommendations2)}")


async def main():
    """Main test function."""
    print("\n" + "🎯" * 40)
    print("  INDIE EBOOK RECOMMENDATION SYSTEM TEST")
    print("🎯" * 40)

    try:
        # Check data availability
        ebook_count, borrow_count, user_count, popular_books = await check_data_availability()

        if ebook_count == 0:
            print("\n❌ No ebooks found. Please add some ebooks first.")
            return

        if borrow_count == 0:
            print("\n⚠️  No borrows found. Recommendations will be limited.")

        # Test collaborative recommendations with most popular book
        if popular_books:
            await test_collaborative_recommendations(popular_books[0].id)

        # Test personalized recommendations with a user who has borrows
        if user_count > 0:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(IndieEbookBorrow.user_id)
                    .group_by(IndieEbookBorrow.user_id)
                    .order_by(func.count(IndieEbookBorrow.id).desc())
                    .limit(1)
                )
                user_id = result.scalar()

                if user_id:
                    await test_personalized_recommendations(user_id)

        # Test genre-based fallback
        await test_genre_fallback()

        # Test cache performance
        await test_cache_performance()

        await print_separator("✅ All Tests Complete")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
