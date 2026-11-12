# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Set default fiscal sponsor configuration."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import AsyncSessionLocal
from app.models.organization_features import OrganizationFeatures


async def seed():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(OrganizationFeatures).limit(1))
        features = result.scalar_one_or_none()
        if not features:
            print("No organization features found")
            return

        config = dict(features.configuration or {})
        if "fiscal_sponsor" not in config:
            config["fiscal_sponsor"] = {
                "mode": "shared",
            }
            features.configuration = config
            flag_modified(features, "configuration")
            await db.commit()
            print("Set fiscal sponsor mode to 'shared' (platform foundation)")
        else:
            print(f"Fiscal sponsor already configured: mode={config['fiscal_sponsor'].get('mode')}")


if __name__ == "__main__":
    asyncio.run(seed())
