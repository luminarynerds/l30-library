# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.carbon_metrics import CarbonMetric

logger = get_logger(__name__)

CO2_GRAMS_PER_BYTE = Decimal("0.00000040014")

LOG_PATTERN = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" '
    r'(?P<status>\d+) (?P<bytes>\d+)'
)

SECTION_RULES = [
    (re.compile(r'^/api/v1/'), 'api'),
    (re.compile(r'^/staff/'), 'staff'),
    (re.compile(r'^/(assets|icons|fonts|favicon|manifest|theme-init|sw)'), 'static'),
    (re.compile(r'^/events'), 'events'),
    (re.compile(r'^/(catalog|search|item/)'), 'catalog'),
]


def classify_section(path: str) -> str:
    for pattern, section in SECTION_RULES:
        if pattern.match(path):
            return section
    return 'patron'


def parse_nginx_time(time_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(time_str, "%d/%b/%Y:%H:%M:%S %z")
    except ValueError:
        return None


def parse_log_line(line: str) -> Optional[dict]:
    match = LOG_PATTERN.match(line)
    if not match:
        return None
    status = int(match.group('status'))
    if status >= 400:
        return None
    bytes_sent = int(match.group('bytes'))
    if bytes_sent == 0:
        return None
    timestamp = parse_nginx_time(match.group('time'))
    if not timestamp:
        return None
    return {
        'timestamp': timestamp,
        'path': match.group('path'),
        'bytes': bytes_sent,
        'section': classify_section(match.group('path')),
    }


async def aggregate_hour(db: AsyncSession, log_path: str, hour_start: datetime) -> int:
    hour_end = hour_start + timedelta(hours=1)

    existing = await db.execute(
        select(func.count(CarbonMetric.id)).where(
            and_(
                CarbonMetric.period_start == hour_start,
                CarbonMetric.period_type == 'hourly',
            )
        )
    )
    if existing.scalar() > 0:
        return 0

    section_data: dict[str, dict] = {}
    log_file = Path(log_path)
    if not log_file.exists():
        logger.warning(f"Log file not found: {log_path}")
        return 0

    with open(log_file) as f:
        for line in f:
            entry = parse_log_line(line)
            if not entry:
                continue
            if entry['timestamp'] < hour_start or entry['timestamp'] >= hour_end:
                continue
            section = entry['section']
            if section not in section_data:
                section_data[section] = {'bytes': 0, 'count': 0}
            section_data[section]['bytes'] += entry['bytes']
            section_data[section]['count'] += 1

    records = 0
    for section, data in section_data.items():
        total_bytes = data['bytes']
        count = data['count']
        co2 = Decimal(total_bytes) * CO2_GRAMS_PER_BYTE
        avg_bytes = Decimal(total_bytes) / Decimal(count) if count > 0 else Decimal(0)

        metric = CarbonMetric(
            period_start=hour_start,
            period_end=hour_end,
            period_type='hourly',
            section=section,
            total_bytes=total_bytes,
            request_count=count,
            estimated_co2_grams=co2,
            avg_bytes_per_request=avg_bytes,
        )
        db.add(metric)
        records += 1

    if records:
        await db.commit()
        logger.info(f"Aggregated {records} carbon metrics for {hour_start.isoformat()}")

    return records


async def get_monthly_summary(db: AsyncSession, months: int = 6) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
    result = await db.execute(
        select(
            func.date_trunc('month', CarbonMetric.period_start).label('month'),
            func.sum(CarbonMetric.total_bytes).label('total_bytes'),
            func.sum(CarbonMetric.request_count).label('total_requests'),
            func.sum(CarbonMetric.estimated_co2_grams).label('total_co2'),
        )
        .where(CarbonMetric.period_start >= cutoff)
        .group_by('month')
        .order_by('month')
    )
    rows = result.fetchall()
    return [
        {
            'month': row.month.isoformat() if row.month else None,
            'total_bytes': int(row.total_bytes or 0),
            'total_requests': int(row.total_requests or 0),
            'total_co2_grams': float(row.total_co2 or 0),
            'avg_co2_per_request': float(row.total_co2 / row.total_requests) if row.total_requests else 0,
        }
        for row in rows
    ]


async def get_section_breakdown(db: AsyncSession, days: int = 30) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            CarbonMetric.section,
            func.sum(CarbonMetric.total_bytes).label('total_bytes'),
            func.sum(CarbonMetric.request_count).label('total_requests'),
            func.sum(CarbonMetric.estimated_co2_grams).label('total_co2'),
        )
        .where(CarbonMetric.period_start >= cutoff)
        .group_by(CarbonMetric.section)
        .order_by(func.sum(CarbonMetric.estimated_co2_grams).desc())
    )
    rows = result.fetchall()
    return [
        {
            'section': row.section,
            'total_bytes': int(row.total_bytes or 0),
            'total_requests': int(row.total_requests or 0),
            'total_co2_grams': float(row.total_co2 or 0),
        }
        for row in rows
    ]


async def get_heaviest_pages(db: AsyncSession, limit: int = 10) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(
            CarbonMetric.section,
            CarbonMetric.avg_bytes_per_request,
            CarbonMetric.request_count,
        )
        .where(CarbonMetric.period_start >= cutoff)
        .order_by(CarbonMetric.avg_bytes_per_request.desc())
        .limit(limit)
    )
    rows = result.fetchall()
    return [
        {
            'section': row.section,
            'avg_bytes': float(row.avg_bytes_per_request or 0),
            'request_count': row.request_count,
            'avg_co2_grams': float((row.avg_bytes_per_request or 0) * CO2_GRAMS_PER_BYTE),
        }
        for row in rows
    ]


async def get_public_summary(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(
            func.sum(CarbonMetric.total_bytes).label('total_bytes'),
            func.sum(CarbonMetric.request_count).label('total_requests'),
            func.sum(CarbonMetric.estimated_co2_grams).label('total_co2'),
        )
        .where(CarbonMetric.period_start >= month_start)
    )
    row = result.fetchone()
    total_co2 = float(row.total_co2 or 0) if row else 0
    total_requests = int(row.total_requests or 0) if row else 0
    avg_per_page = total_co2 / total_requests if total_requests > 0 else 0

    benchmark = 0.5
    pct_cleaner = max(0, (1 - avg_per_page / benchmark) * 100) if benchmark > 0 else 0

    return {
        'month': month_start.strftime('%B %Y'),
        'total_co2_grams': round(total_co2, 2),
        'total_requests': total_requests,
        'avg_co2_per_page_grams': round(avg_per_page, 4),
        'benchmark_avg_grams': benchmark,
        'pct_cleaner_than_average': round(pct_cleaner, 1),
        'equivalent_km_driven': round(total_co2 / 120, 2),
        'equivalent_smartphone_charges': round(total_co2 / 8.22, 1),
    }
