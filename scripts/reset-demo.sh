#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# Reset demo data for setup.l30.org
# Cron: 0 4 * * * /opt/l30/scripts/reset-demo.sh >> /var/log/l30-demo-reset.log 2>&1
set -e

cd /opt/l30

echo "[$(date -Iseconds)] Starting demo reset..."

# Truncate all public tables
docker compose -f docker-compose.dist.yml exec -T database psql -U l30 -d l30 -c "
DO \$\$
DECLARE r RECORD;
BEGIN
  FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
    EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.tablename) || ' CASCADE';
  END LOOP;
END \$\$;
"

# Reload demo seed -- ORM-driven (app.seeds.demo_seeder), not a raw-SQL
# file. See docs/dist-install-characterization.md §6 for why the old
# demo/seed.sql approach was retired.
docker compose -f docker-compose.dist.yml exec -T l30-backend python -c "
import asyncio
from app.core.database import AsyncSessionLocal
from app.seeds.demo_seeder import seed_demo

async def main():
    async with AsyncSessionLocal() as db:
        result = await seed_demo(db)
        print(result)

asyncio.run(main())
"

echo "[$(date -Iseconds)] Demo reset complete."
