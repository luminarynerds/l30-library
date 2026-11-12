# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff Command Search API

Unified search endpoint for the staff command palette.
Searches patrons, catalog items, and returns static page matches.
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .dependencies import require_staff
from ...core.database import get_db
from ...models.catalog import CatalogItem
from ...models.user import User, UserRole, name_or_email_clause

router = APIRouter(prefix="/staff", tags=["Staff"])


class CommandSearchResult(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    category: str  # 'patron' | 'catalog' | 'page'
    url: str
    icon: Optional[str] = None


class CommandSearchResponse(BaseModel):
    results: List[CommandSearchResult] = []
    query: str


@router.get("/command-search", response_model=CommandSearchResponse)
async def command_search(
    q: str = Query(..., min_length=1),
    types: Optional[str] = Query(None, description="Comma-separated: patron,catalog,page"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Unified search for the command palette. Searches patrons, catalog items, and pages."""
    search_types = types.split(",") if types else ["patron", "catalog", "page"]
    results: List[CommandSearchResult] = []

    search_term = f"%{q}%"

    # Patron search
    if "patron" in search_types:
        stmt = (
            select(User)
            .where(
                and_(
                    User.role == UserRole.PATRON,
                    or_(
                        # Names + email encrypted: blind-index match, not substring.
                        *([name_or_email_clause(q)] if name_or_email_clause(q) is not None else []),
                        User.library_card.ilike(search_term),
                    ),
                )
            )
            .limit(5)
        )
        rows = (await db.execute(stmt)).scalars().all()
        for patron in rows:
            results.append(CommandSearchResult(
                id=f"patron-{patron.id}",
                label=f"{patron.first_name} {patron.last_name}",
                description=patron.email or patron.library_card,
                category="patron",
                url=f"/staff/patrons/{patron.id}",
                icon="User",
            ))

    # Catalog search
    if "catalog" in search_types:
        stmt = (
            select(CatalogItem)
            .where(
                or_(
                    CatalogItem.title.ilike(search_term),
                    CatalogItem.author.ilike(search_term),
                    CatalogItem.isbn.ilike(search_term),
                    CatalogItem.barcode.ilike(search_term),
                )
            )
            .limit(5)
        )
        rows = (await db.execute(stmt)).scalars().all()
        for item in rows:
            results.append(CommandSearchResult(
                id=f"catalog-{item.id}",
                label=item.title,
                description=f"{item.author or 'Unknown'} \u2022 {item.isbn or item.barcode or ''}",
                category="catalog",
                url=f"/catalog/{item.id}",
                icon="BookOpen",
            ))

    # Static page results (always available, filtered client-side for speed)
    if "page" in search_types:
        pages = [
            CommandSearchResult(id="page-circulation", label="Circulation", description="Manage checkouts and returns", category="page", url="/staff/circulation", icon="ArrowRightLeft"),
            CommandSearchResult(id="page-patrons", label="Patron Management", description="Search and manage patrons", category="page", url="/staff/patrons", icon="Users"),
            CommandSearchResult(id="page-cataloging", label="Cataloging", description="Catalog new items", category="page", url="/staff/cataloging", icon="BookOpen"),
            CommandSearchResult(id="page-inventory", label="Inventory", description="Manage library inventory", category="page", url="/staff/inventory", icon="Package"),
            CommandSearchResult(id="page-reports", label="Circulation Reports", description="View circulation reports", category="page", url="/staff/reports", icon="BarChart3"),
            CommandSearchResult(id="page-analytics", label="Analytics Dashboard", description="System analytics", category="page", url="/staff/analytics", icon="TrendingUp"),
            CommandSearchResult(id="page-holds", label="Hold Shelf", description="Manage hold shelf", category="page", url="/staff/holds/shelf", icon="Clock"),
            CommandSearchResult(id="page-acquisition", label="Acquisitions", description="Purchase orders and vendors", category="page", url="/staff/acquisition", icon="ShoppingCart"),
            CommandSearchResult(id="page-training", label="Staff Training", description="Training dashboard", category="page", url="/staff/training", icon="GraduationCap"),
            CommandSearchResult(id="page-rfid", label="RFID Management", description="RFID operations", category="page", url="/staff/rfid", icon="Radio"),
            CommandSearchResult(id="page-lost-damaged", label="Lost & Damaged", description="Manage lost and damaged items", category="page", url="/staff/lost-damaged", icon="AlertTriangle"),
            CommandSearchResult(id="page-makerspace", label="Makerspace", description="Makerspace management", category="page", url="/staff/makerspace", icon="Wrench"),
            CommandSearchResult(id="page-book-drop", label="Book Drop", description="Book drop processing", category="page", url="/staff/book-drop", icon="Inbox"),
            CommandSearchResult(id="page-admin", label="Admin Dashboard", description="System administration", category="page", url="/admin", icon="Settings"),
            CommandSearchResult(id="page-board", label="Board Management", description="Board governance", category="page", url="/admin/board", icon="Shield"),
        ]
        query_lower = q.lower()
        results.extend([p for p in pages if query_lower in p.label.lower() or query_lower in (p.description or "").lower()][:5])

    return CommandSearchResponse(results=results, query=q)
