# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import io
from app.core.logging import get_logger
from datetime import date

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem, ItemType, ItemStatus
from app.models.circulation import Checkout
from app.models.user import User, UserRole
from app.models.event import Event
from app.core.branding import branding

logger = get_logger(__name__)

# PLS field definitions -- code, label, category
PLS_FIELDS = [
    # Collection
    ("BKVOL", "Print materials", "collection"),
    ("EBOOK", "Electronic books", "collection"),
    ("AUDIO_PH", "Physical audio materials", "collection"),
    ("AUDIO_DL", "Downloadable audio materials", "collection"),
    ("VIDEO_PH", "Physical video materials", "collection"),
    ("OTHER_PH", "Other physical materials", "collection"),
    ("EC_DBASE", "Licensed databases", "collection"),
    # Circulation
    ("TOTCIR", "Total circulation", "circulation"),
    ("KIDCIRCL", "Children's circulation", "circulation"),
    ("ELMATCIR", "Electronic materials circulation", "circulation"),
    ("PHYSCIR", "Physical materials circulation", "circulation"),
    ("TOTCOLL", "Total collection expenditures", "circulation"),
    # Usage
    ("VISITS", "Library visits", "usage"),
    ("REFERENC", "Reference transactions", "usage"),
    ("REGBOR", "Registered borrowers", "usage"),
    # Programs
    ("TOTPRO", "Total programs", "programs"),
    ("KIDPRO", "Children's programs", "programs"),
    ("YAPRO", "Young adult programs", "programs"),
    ("TOTATTEN", "Total program attendance", "programs"),
    # Staffing
    ("LIBRARIA", "ALA-MLS librarians (FTE)", "staffing"),
    ("OTHPAID", "Other paid staff (FTE)", "staffing"),
    ("TOTSTAFF", "Total paid staff (FTE)", "staffing"),
    # Finance
    ("LOCGVT", "Local government revenue", "finance"),
    ("STGVT", "State government revenue", "finance"),
    ("FEDGVT", "Federal government revenue", "finance"),
    ("OTHINCM", "Other revenue", "finance"),
    ("TOTINCM", "Total operating revenue", "finance"),
    ("SALARIES", "Staff expenditures", "finance"),
    ("BENEFIT", "Employee benefits", "finance"),
    ("TOTOPEXP", "Total operating expenditures", "finance"),
    ("PRMATEXP", "Print material expenditures", "finance"),
    ("ELMATEXP", "Electronic material expenditures", "finance"),
    ("OTHMATEX", "Other material expenditures", "finance"),
    ("TOTEXPCO", "Total collection expenditures", "finance"),
    ("CAPITAL", "Capital expenditures", "finance"),
    # Facilities
    ("CENTLIB", "Central libraries", "facilities"),
    ("BRANLIB", "Branch libraries", "facilities"),
    ("BKMOB", "Bookmobiles", "facilities"),
    ("HRS_OPEN", "Total annual public service hours", "facilities"),
]


class PLSExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_preview(
        self, fiscal_year: int, overrides: dict | None = None,
    ) -> dict:
        fy_start = date(fiscal_year - 1, 7, 1)
        fy_end = date(fiscal_year, 6, 30)
        overrides = overrides or {}

        elements = []
        auto_count = 0
        override_count = 0
        missing_count = 0
        fields_requiring_manual_input: list[str] = []

        for code, label, category in PLS_FIELDS:
            if code in overrides:
                elements.append({
                    "code": code, "label": label, "category": category,
                    "value": overrides[code], "source": "manual_override", "notes": None,
                })
                override_count += 1
                continue

            value = await self._calculate_field(code, fy_start, fy_end)
            if value is None:
                source = "manual_required"
                missing_count += 1
                fields_requiring_manual_input.append(code)
            else:
                source = "auto"
                auto_count += 1

            elements.append({
                "code": code, "label": label, "category": category,
                "value": value, "source": source, "notes": None,
            })

        return {
            "fiscal_year": fiscal_year,
            "library_name": branding.library_name,
            "fscs_id": None,
            "elements": elements,
            "auto_calculated": auto_count,
            "manual_overrides": override_count,
            "missing": missing_count,
            "fields_requiring_manual_input": fields_requiring_manual_input,
        }

    async def generate_csv(self, fiscal_year: int, overrides: dict | None = None) -> str:
        preview = await self.generate_preview(fiscal_year, overrides)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Field Code", "Field Label", "Category", "Value", "Source"])
        for elem in preview["elements"]:
            writer.writerow([
                elem["code"], elem["label"], elem["category"],
                elem["value"] if elem["value"] is not None else "",
                elem["source"],
            ])
        return output.getvalue()

    async def _calculate_field(self, code: str, fy_start: date, fy_end: date):
        fy_filter = and_(
            Checkout.checked_out_at >= fy_start,
            Checkout.checked_out_at <= fy_end,
        )

        if code == "BKVOL":
            return (await self.db.execute(
                select(func.count(CatalogItem.id)).where(
                    CatalogItem.item_type.in_([ItemType.book]),
                    CatalogItem.status != ItemStatus.withdrawn,
                )
            )).scalar()

        elif code == "EBOOK":
            return (await self.db.execute(
                select(func.count(CatalogItem.id)).where(
                    CatalogItem.item_type == ItemType.ebook,
                    CatalogItem.status != ItemStatus.withdrawn,
                )
            )).scalar()

        elif code == "AUDIO_PH":
            return (await self.db.execute(
                select(func.count(CatalogItem.id)).where(
                    CatalogItem.item_type.in_([ItemType.cd, ItemType.vinyl]),
                    CatalogItem.status != ItemStatus.withdrawn,
                )
            )).scalar()

        elif code == "VIDEO_PH":
            return (await self.db.execute(
                select(func.count(CatalogItem.id)).where(
                    CatalogItem.item_type.in_([ItemType.dvd, ItemType.bluray]),
                    CatalogItem.status != ItemStatus.withdrawn,
                )
            )).scalar()

        elif code == "OTHER_PH":
            return (await self.db.execute(
                select(func.count(CatalogItem.id)).where(
                    CatalogItem.item_type.in_([
                        ItemType.game, ItemType.equipment, ItemType.kit,
                        ItemType.magazine, ItemType.other,
                    ]),
                    CatalogItem.status != ItemStatus.withdrawn,
                )
            )).scalar()

        elif code == "TOTCIR":
            return (await self.db.execute(
                select(func.count(Checkout.id)).where(fy_filter)
            )).scalar()

        elif code == "REGBOR":
            return (await self.db.execute(
                select(func.count(User.id)).where(User.role == UserRole.PATRON)
            )).scalar()

        elif code == "TOTPRO":
            return (await self.db.execute(
                select(func.count(Event.id)).where(
                    Event.start_time >= fy_start,
                    Event.start_time <= fy_end,
                )
            )).scalar()

        # Fields that need manual input (staffing FTE, financials, etc.)
        return None
