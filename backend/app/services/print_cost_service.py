# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.print import PrintPricing


async def get_active_pricing(db: AsyncSession) -> PrintPricing:
    result = await db.execute(
        select(PrintPricing).where(PrintPricing.is_active == True).limit(1)
    )
    pricing = result.scalar_one_or_none()
    if not pricing:
        # Return default pricing
        return PrintPricing(
            blackwhite_price_per_page=Decimal("0.10"),
            color_price_per_page=Decimal("0.50"),
            minimum_charge=Decimal("0.25"),
            double_sided_discount_percentage=0,
            discount_percentage_for_bulk=0,
            bulk_threshold_pages=100,
        )
    return pricing


async def calculate_cost(
    db: AsyncSession,
    pages: int,
    copies: int = 1,
    color_mode: str = "blackwhite",
    double_sided: bool = True,
    device_type: Optional[str] = None,
) -> dict:
    pricing = await get_active_pricing(db)

    total_pages = pages * copies

    if color_mode == "color":
        cost_per_page = pricing.color_price_per_page
    else:
        cost_per_page = pricing.blackwhite_price_per_page

    subtotal = cost_per_page * total_pages

    # Double-sided discount
    discount = Decimal("0.00")
    if double_sided and pricing.double_sided_discount_percentage > 0:
        discount = subtotal * Decimal(pricing.double_sided_discount_percentage) / Decimal("100")

    # Bulk discount
    if total_pages >= pricing.bulk_threshold_pages and pricing.discount_percentage_for_bulk > 0:
        bulk_discount = subtotal * Decimal(pricing.discount_percentage_for_bulk) / Decimal("100")
        discount += bulk_discount

    total = max(subtotal - discount, pricing.minimum_charge)

    return {
        "pages": pages,
        "copies": copies,
        "color_mode": color_mode,
        "double_sided": double_sided,
        "cost_per_page": cost_per_page,
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
    }
