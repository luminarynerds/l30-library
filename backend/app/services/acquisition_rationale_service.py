# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acquisition_rationale import AcquisitionRationale
from app.models.catalog import CatalogItem
from app.schemas.acquisition_rationale import (
    AcquisitionRationaleCreate,
    AcquisitionRationaleUpdate,
)


class RationaleService:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        catalog_item_id: int,
        user_id: Optional[int],
        data: AcquisitionRationaleCreate,
    ) -> AcquisitionRationale:
        rat = AcquisitionRationale(
            catalog_item_id=catalog_item_id,
            created_by_id=user_id,
            **data.model_dump(),
        )
        self.session.add(rat)
        await self.session.flush()
        await self.session.refresh(rat)
        return rat

    async def get_by_catalog_item(
        self, catalog_item_id: int,
    ) -> Optional[AcquisitionRationale]:
        result = await self.session.execute(
            select(AcquisitionRationale).where(
                AcquisitionRationale.catalog_item_id == catalog_item_id
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        catalog_item_id: int,
        data: AcquisitionRationaleUpdate,
    ) -> Optional[AcquisitionRationale]:
        rat = await self.get_by_catalog_item(catalog_item_id)
        if rat is None:
            return None
        for k, v in data.model_dump().items():
            setattr(rat, k, v)
        await self.session.flush()
        await self.session.refresh(rat)
        return rat

    async def list_missing_rationale_items(self, limit: int = 50) -> list[int]:
        result = await self.session.execute(
            select(CatalogItem.id)
            .outerjoin(
                AcquisitionRationale,
                AcquisitionRationale.catalog_item_id == CatalogItem.id,
            )
            .where(AcquisitionRationale.id.is_(None))
            .order_by(CatalogItem.id)
            .limit(limit)
        )
        return [r[0] for r in result.all()]
