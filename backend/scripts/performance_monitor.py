#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Performance Monitoring Script for LSC Load Testing

Monitors system metrics, database performance, Redis cache, and API response times
during load testing. Can be run alongside locust or pytest load tests.

Usage:
    python performance_monitor.py --duration 300 --output report.json
    python performance_monitor.py --redis-only
    python performance_monitor.py --db-only
"""

import asyncio
import json
import time
import psutil
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import statistics

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

try:
    from sqlalchemy import text, select, func
    from sqlalchemy.ext.asyncio import create_async_engine
except ImportError:
    text = select = func = None


class SystemMonitor:
    """Monitor system-level metrics."""

    def __init__(self):
        self.samples: List[Dict] = []
        self.start_time = time.time()

    def sample(self):
        """Take a system metrics sample."""
        process = psutil.Process()
        memory_info = process.memory_info()

        sample = {
            'timestamp': datetime.now().isoformat(),
            'elapsed_seconds': time.time() - self.start_time,
            'cpu_percent': process.cpu_percent(interval=0.1),
            'memory_rss_mb': memory_info.rss / (1024 * 1024),
            'memory_vms_mb': memory_info.vms / (1024 * 1024),
            'threads': process.num_threads(),
            'open_files': process.num_fds() if hasattr(process, 'num_fds') else 0,
            'system_cpu_percent': psutil.cpu_percent(interval=0.1),
            'system_memory_percent': psutil.virtual_memory().percent,
            'disk_usage_percent': psutil.disk_usage('/').percent,
        }
        self.samples.append(sample)
        return sample

    def get_summary(self) -> Dict:
        """Get system metrics summary."""
        if not self.samples:
            return {}

        memory_samples = [s['memory_rss_mb'] for s in self.samples]
        cpu_samples = [s['cpu_percent'] for s in self.samples]

        return {
            'samples': len(self.samples),
            'duration_seconds': self.samples[-1]['elapsed_seconds'],
            'memory': {
                'avg_mb': statistics.mean(memory_samples),
                'max_mb': max(memory_samples),
                'min_mb': min(memory_samples),
                'peak_mb': max(memory_samples),
            },
            'cpu': {
                'avg_percent': statistics.mean(cpu_samples),
                'max_percent': max(cpu_samples),
                'min_percent': min(cpu_samples),
            },
        }


class RedisMonitor:
    """Monitor Redis cache performance."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.samples: List[Dict] = []
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis."""
        if not redis:
            print("ERROR: redis-py not installed. Install with: pip install redis")
            return False

        try:
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
            return True
        except Exception as e:
            print(f"ERROR: Failed to connect to Redis: {e}")
            return False

    async def sample(self):
        """Take a Redis metrics sample."""
        if not self.redis_client:
            return None

        try:
            info = await self.redis_client.info()

            sample = {
                'timestamp': datetime.now().isoformat(),
                'memory': {
                    'used_memory_mb': info.get('used_memory', 0) / (1024 * 1024),
                    'used_memory_peak_mb': info.get('used_memory_peak', 0) / (1024 * 1024),
                    'used_memory_percent': info.get('used_memory_human', 'N/A'),
                },
                'stats': {
                    'total_connections_received': info.get('total_connections_received', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0),
                    'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec', 0),
                    'connected_clients': info.get('connected_clients', 0),
                },
                'keyspace': {
                    'keys': info.get('db0', {}).get('keys', 0) if 'db0' in info else 0,
                    'expires': info.get('db0', {}).get('expires', 0) if 'db0' in info else 0,
                },
            }
            self.samples.append(sample)
            return sample
        except Exception as e:
            print(f"ERROR: Failed to sample Redis: {e}")
            return None

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()

    def get_summary(self) -> Dict:
        """Get Redis metrics summary."""
        if not self.samples:
            return {}

        memory_samples = [s['memory']['used_memory_mb'] for s in self.samples]
        ops_samples = [s['stats']['instantaneous_ops_per_sec'] for s in self.samples]

        return {
            'samples': len(self.samples),
            'memory': {
                'avg_mb': statistics.mean(memory_samples),
                'max_mb': max(memory_samples),
                'min_mb': min(memory_samples),
            },
            'operations': {
                'avg_ops_per_sec': statistics.mean(ops_samples),
                'max_ops_per_sec': max(ops_samples),
                'min_ops_per_sec': min(ops_samples),
            },
            'first_sample': self.samples[0] if self.samples else {},
            'last_sample': self.samples[-1] if self.samples else {},
        }


class DatabaseMonitor:
    """Monitor PostgreSQL database performance."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.samples: List[Dict] = []
        self.engine = None

    async def connect(self):
        """Connect to database."""
        if not text or not select:
            print("ERROR: sqlalchemy not installed. Install with: pip install sqlalchemy")
            return False

        try:
            self.engine = create_async_engine(self.database_url)
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"ERROR: Failed to connect to database: {e}")
            return False

    async def sample(self):
        """Take a database metrics sample."""
        if not self.engine:
            return None

        try:
            async with self.engine.begin() as conn:
                # Get connection pool stats
                pool = self.engine.pool

                # Get active connections
                result = await conn.execute(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                ))
                active_connections = result.scalar()

                # Get slow queries
                result = await conn.execute(text(
                    """
                    SELECT query, mean_exec_time, calls
                    FROM pg_stat_statements
                    WHERE mean_exec_time > 100
                    ORDER BY mean_exec_time DESC
                    LIMIT 5
                    """
                ))
                slow_queries = []
                try:
                    for row in result:
                        slow_queries.append({
                            'query': row[0][:100],
                            'avg_time_ms': float(row[1]),
                            'calls': row[2],
                        })
                except Exception:
                    pass

                # Get cache hit ratio
                result = await conn.execute(text(
                    """
                    SELECT
                        sum(heap_blks_read) as heap_read,
                        sum(heap_blks_hit) as heap_hit
                    FROM pg_statio_user_tables
                    """
                ))
                heap_read, heap_hit = result.one()
                heap_read = heap_read or 0
                heap_hit = heap_hit or 0
                cache_hit_ratio = (heap_hit / (heap_hit + heap_read) * 100) if (heap_hit + heap_read) > 0 else 0

                sample = {
                    'timestamp': datetime.now().isoformat(),
                    'connections': {
                        'active': active_connections,
                        'pool_size': pool.size() if hasattr(pool, 'size') else 0,
                    },
                    'performance': {
                        'cache_hit_ratio_percent': cache_hit_ratio,
                        'slow_queries': slow_queries,
                    },
                }
                self.samples.append(sample)
                return sample
        except Exception as e:
            print(f"ERROR: Failed to sample database: {e}")
            return None

    async def disconnect(self):
        """Disconnect from database."""
        if self.engine:
            await self.engine.dispose()

    def get_summary(self) -> Dict:
        """Get database metrics summary."""
        if not self.samples:
            return {}

        active_connections = [s['connections']['active'] for s in self.samples]
        cache_ratios = [s['performance']['cache_hit_ratio_percent'] for s in self.samples]

        return {
            'samples': len(self.samples),
            'connections': {
                'avg_active': statistics.mean(active_connections),
                'max_active': max(active_connections),
                'min_active': min(active_connections),
            },
            'cache': {
                'avg_hit_ratio_percent': statistics.mean(cache_ratios),
                'min_hit_ratio_percent': min(cache_ratios),
                'max_hit_ratio_percent': max(cache_ratios),
            },
        }


class PerformanceMonitor:
    """Orchestrate monitoring of all systems."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        database_url: Optional[str] = None,
        sample_interval: int = 5,
    ):
        self.redis_url = redis_url
        self.database_url = database_url
        self.sample_interval = sample_interval

        self.system_monitor = SystemMonitor()
        self.redis_monitor = RedisMonitor(redis_url)
        self.database_monitor = DatabaseMonitor(database_url) if database_url else None

    async def start(self, duration_seconds: Optional[int] = None):
        """Start monitoring."""
        print("="*80)
        print("LSC Performance Monitor Started")
        print("="*80)

        # Connect to services
        redis_ok = await self.redis_monitor.connect()
        if redis_ok:
            print("✓ Connected to Redis")
        else:
            print("✗ Could not connect to Redis (monitoring disabled)")

        db_ok = False
        if self.database_monitor:
            db_ok = await self.database_monitor.connect()
            if db_ok:
                print("✓ Connected to Database")
            else:
                print("✗ Could not connect to Database (monitoring disabled)")

        print("✓ System monitoring enabled")
        print(f"\nSampling every {self.sample_interval} seconds...")
        print("-"*80)

        try:
            start_time = time.time()
            sample_count = 0

            while True:
                if duration_seconds and (time.time() - start_time) > duration_seconds:
                    break

                # Take samples
                sys_sample = self.system_monitor.sample()
                self._print_sample(sys_sample, sample_count)

                if redis_ok:
                    redis_sample = await self.redis_monitor.sample()
                    if redis_sample:
                        print(f"  Redis: {redis_sample['memory']['used_memory_mb']:.1f}MB, " +
                              f"{redis_sample['stats']['instantaneous_ops_per_sec']} ops/sec")

                if db_ok and self.database_monitor:
                    db_sample = await self.database_monitor.sample()
                    if db_sample:
                        print(f"  DB: {db_sample['connections']['active']} active connections, " +
                              f"{db_sample['performance']['cache_hit_ratio_percent']:.1f}% cache hit ratio")

                sample_count += 1
                print()

                await asyncio.sleep(self.sample_interval)

        except KeyboardInterrupt:
            print("\n\nMonitoring interrupted by user")
        finally:
            await self.redis_monitor.disconnect()
            if self.database_monitor:
                await self.database_monitor.disconnect()

        self._print_summary()

    def _print_sample(self, sample: Dict, count: int):
        """Print a single sample."""
        elapsed = sample['elapsed_seconds']
        print(f"[{count:04d} @ {elapsed:6.1f}s] " +
              f"CPU: {sample['cpu_percent']:5.1f}% | " +
              f"Memory: {sample['memory_rss_mb']:6.1f}MB | " +
              f"Threads: {sample['threads']:3d} | " +
              f"Disk: {sample['disk_usage_percent']:5.1f}%")

    def _print_summary(self):
        """Print monitoring summary."""
        print("\n" + "="*80)
        print("PERFORMANCE MONITORING SUMMARY")
        print("="*80)

        # System summary
        sys_summary = self.system_monitor.get_summary()
        print("\nSystem Metrics:")
        print(json.dumps(sys_summary, indent=2))

        # Redis summary
        if self.redis_monitor.redis_client:
            redis_summary = self.redis_monitor.get_summary()
            print("\nRedis Metrics:")
            print(json.dumps(redis_summary, indent=2))

        # Database summary
        if self.database_monitor and self.database_monitor.engine:
            db_summary = self.database_monitor.get_summary()
            print("\nDatabase Metrics:")
            print(json.dumps(db_summary, indent=2))

        print("\n" + "="*80)

    def export_json(self, filepath: str):
        """Export all monitoring data to JSON file."""
        data = {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'summary': self.system_monitor.get_summary(),
                'samples': self.system_monitor.samples,
            },
            'redis': {
                'summary': self.redis_monitor.get_summary(),
                'samples': self.redis_monitor.samples,
            },
        }

        if self.database_monitor:
            data['database'] = {
                'summary': self.database_monitor.get_summary(),
                'samples': self.database_monitor.samples,
            }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Monitoring data exported to {filepath}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor LSC performance during load testing"
    )
    parser.add_argument(
        "--duration", type=int, default=None,
        help="Monitoring duration in seconds (default: infinite)"
    )
    parser.add_argument(
        "--interval", type=int, default=5,
        help="Sampling interval in seconds (default: 5)"
    )
    parser.add_argument(
        "--redis-url", default="redis://localhost:6379/0",
        help="Redis URL (default: redis://localhost:6379/0)"
    )
    parser.add_argument(
        "--database-url", default=None,
        help="PostgreSQL database URL (for DB monitoring)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output JSON file for results"
    )
    parser.add_argument(
        "--redis-only", action="store_true",
        help="Monitor Redis only"
    )
    parser.add_argument(
        "--db-only", action="store_true",
        help="Monitor database only"
    )

    args = parser.parse_args()

    monitor = PerformanceMonitor(
        redis_url=args.redis_url,
        database_url=args.database_url,
        sample_interval=args.interval,
    )

    await monitor.start(duration_seconds=args.duration)

    if args.output:
        monitor.export_json(args.output)


if __name__ == "__main__":
    asyncio.run(main())
