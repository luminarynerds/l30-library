#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
LSC Configuration Debugging Script

This script helps debug environment configuration issues by:
1. Showing which .env file is being loaded
2. Displaying active configuration values
3. Validating database connectivity
4. Checking Docker volume mounting
5. Verifying environment-specific settings

Usage:
    python scripts/debug_config.py
    python scripts/debug_config.py --check-db      # Test database connection
    python scripts/debug_config.py --check-redis   # Test Redis connection
    python scripts/debug_config.py --check-all     # Run all checks
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_subsection(title):
    """Print a formatted subsection header."""
    print(f"\n{title}")
    print(f"{'-' * len(title)}\n")


def check_env_files():
    """Check which .env files exist and are being used."""
    print_section("ENVIRONMENT FILES")

    env_files = [
        (".env", "Root .env file"),
        ("backend/.env", "Backend .env file"),
        (".env.local", "Local overrides"),
        (".env.prod", "Production config"),
        ("backend/.env.example", "Backend template"),
        (".env.example", "Root template"),
    ]

    print("Checking for .env files:")
    for env_file, description in env_files:
        full_path = Path(env_file)
        exists = "✓" if full_path.exists() else "✗"
        size = f"{full_path.stat().st_size} bytes" if full_path.exists() else "N/A"
        print(f"  {exists} {env_file:<25} ({description:<20}) - {size}")

    # Check pydantic settings location
    print_subsection("Pydantic Settings Configuration")
    print("  Pydantic env_file setting: '.env'")
    print(f"  Current working directory: {os.getcwd()}")
    print(f"  PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")


def show_environment_variables():
    """Show relevant environment variables."""
    print_section("ENVIRONMENT VARIABLES (Non-Sensitive)")

    env_vars = {
        "Application": [
            "DEBUG",
            "ENVIRONMENT",
            "APP_VERSION",
            "FRONTEND_URL",
            "LOG_LEVEL",
            "LOG_FORMAT",
        ],
        "Database": [
            "DATABASE_REQUIRE_SSL",
            "DB_POOL_SIZE",
            "DB_MAX_OVERFLOW",
            "DB_POOL_TIMEOUT",
            "DB_POOL_RECYCLE",
        ],
        "Cache": [
            "REDIS_SSL",
            "CACHE_WARMING_ENABLED",
            "CACHE_REFRESH_INTERVAL_MINUTES",
        ],
        "Authentication": [
            "ALGORITHM",
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "REFRESH_TOKEN_EXPIRE_DAYS",
            "MAX_LOGIN_ATTEMPTS",
            "LOCKOUT_DURATION_MINUTES",
            "PASSWORD_MIN_LENGTH",
        ],
        "Features": [
            "SIP2_ENABLED",
            "SMS_ENABLED",
            "VIRUS_SCAN_ENABLED",
            "SCHEDULER_ENABLED",
            "ENABLE_ENDPOINT_TRACKING",
            "ENABLE_MEMORY_PROFILING",
            "PII_ENCRYPTION_ENABLED",
        ],
        "Storage": [
            "STORAGE_BACKEND",
            "STORAGE_LOCAL_PATH",
        ],
    }

    for category, vars_list in env_vars.items():
        print_subsection(category)
        for var_name in vars_list:
            value = os.environ.get(var_name, "NOT SET")
            # Show truncated value if it's very long
            if len(str(value)) > 60:
                display_value = f"{str(value)[:57]}..."
            else:
                display_value = value
            print(f"  {var_name:<40} = {display_value}")


def show_sensitive_variables():
    """Show sensitive variables status (not values for security)."""
    print_section("SENSITIVE VARIABLES (Status Only)")

    sensitive_vars = {
        "Security": [
            "SECRET_KEY",
            "JWT_SECRET",
            "PII_ENCRYPTION_KEY",
        ],
        "Database": [
            "DATABASE_URL",
        ],
        "Cache": [
            "REDIS_URL",
            "REDIS_PASSWORD",
        ],
        "APIs": [
            "RESEND_API_KEY",
            "SENTRY_DSN",
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
        ],
    }

    for category, vars_list in sensitive_vars.items():
        print_subsection(category)
        for var_name in vars_list:
            value = os.environ.get(var_name)
            if value:
                # Show first 10 chars if available
                prefix = value[:10] if len(value) > 10 else value
                status = f"✓ SET (starts with: {prefix}...)"
            else:
                status = "✗ NOT SET"
            print(f"  {var_name:<40} {status}")


def show_pydantic_settings():
    """Show the loaded Pydantic Settings."""
    print_section("LOADED PYDANTIC SETTINGS")

    try:
        from app.core.config import get_settings
        settings = get_settings()

        settings_dict = {
            "Application": {
                "app_name": settings.app_name,
                "debug": settings.debug,
                "environment": settings.environment,
                "app_version": settings.app_version,
                "is_production": settings.is_production,
            },
            "Database": {
                "database_url": f"{settings.database_url[:30]}..." if settings.database_url else "NOT SET",
                "database_require_ssl": settings.database_require_ssl,
                "db_pool_size": settings.db_pool_size,
                "db_max_overflow": settings.db_max_overflow,
                "db_pool_timeout": settings.db_pool_timeout,
                "db_pool_recycle": settings.db_pool_recycle,
            },
            "Redis": {
                "redis_url": f"{settings.redis_url[:30]}..." if settings.redis_url else "NOT SET",
                "redis_ssl": settings.redis_ssl,
            },
            "Storage": {
                "storage_backend": settings.storage_backend,
                "storage_local_path": settings.storage_local_path,
            },
            "Features": {
                "sms_enabled": settings.sms_enabled,
                "sip2_enabled": settings.sip2_enabled,
                "virus_scan_enabled": settings.virus_scan_enabled,
                "scheduler_enabled": settings.scheduler_enabled,
                "cache_warming_enabled": settings.cache_warming_enabled,
                "pii_encryption_enabled": settings.pii_encryption_enabled,
            },
            "Frontend": {
                "frontend_url": settings.frontend_url,
                "cors_origins": settings.cors_origins[:60] + "..." if len(settings.cors_origins) > 60 else settings.cors_origins,
            },
            "Logging": {
                "log_level": settings.log_level,
                "log_format": settings.log_format,
            },
            "Monitoring": {
                "sentry_dsn": f"{settings.sentry_dsn[:30]}..." if settings.sentry_dsn else "NOT SET",
                "sentry_environment": settings.sentry_environment,
                "enable_endpoint_tracking": settings.enable_endpoint_tracking,
            },
        }

        for category, config_values in settings_dict.items():
            print_subsection(category)
            for key, value in config_values.items():
                print(f"  {key:<40} = {value}")

        return settings
    except Exception as e:
        print(f"✗ Error loading Pydantic settings: {e}")
        return None


def show_docker_volumes():
    """Show Docker volume information."""
    print_section("DOCKER VOLUME MOUNTING")

    # Check if running in Docker
    in_docker = os.path.exists("/.dockerenv")
    print(f"Running in Docker: {'✓ Yes' if in_docker else '✗ No'}")

    if in_docker:
        print_subsection("Mounted Volumes")
        try:
            # Read mount info from /proc/mounts
            with open("/proc/mounts", "r") as f:
                mounts = f.readlines()

            # Filter for app-related mounts
            app_mounts = [m for m in mounts if any(x in m for x in ["/app", "lsc", "uploads", "postgres"])]
            for mount in app_mounts:
                parts = mount.split()
                if len(parts) >= 2:
                    print(f"  {parts[0]:<30} -> {parts[1]}")
        except Exception as e:
            print(f"  Could not read mount information: {e}")
    else:
        print_subsection("Local Development")
        storage_path = os.environ.get("STORAGE_LOCAL_PATH", "/app/uploads")
        path = Path(storage_path)
        exists = "✓" if path.exists() else "✗"
        print(f"  {exists} Storage path exists: {storage_path}")


async def check_database_connection():
    """Test database connectivity."""
    print_section("DATABASE CONNECTION CHECK")

    try:
        from app.core.config import get_settings
        from sqlalchemy.ext.asyncio import create_async_engine

        settings = get_settings()

        if not settings.database_url:
            print("✗ DATABASE_URL not set")
            return False

        print(f"Database URL: {settings.database_url[:50]}...")
        print(f"SSL Required: {settings.database_require_ssl}")

        # Try to create engine and test connection
        engine = create_async_engine(settings.database_url, echo=False)

        try:
            async with engine.begin() as conn:
                _ = await conn.exec("SELECT 1")
                print("✓ Database connection successful")
                return True
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False
        finally:
            await engine.dispose()

    except Exception as e:
        print(f"✗ Error checking database: {e}")
        return False


async def check_redis_connection():
    """Test Redis connectivity."""
    print_section("REDIS CONNECTION CHECK")

    try:
        from app.core.config import get_settings
        import redis

        settings = get_settings()

        if not settings.redis_url:
            print("✗ REDIS_URL not set")
            return False

        print(f"Redis URL: {settings.redis_url[:50]}...")
        print(f"SSL: {settings.redis_ssl}")

        # Parse Redis URL and connect
        r = redis.from_url(settings.redis_url, decode_responses=True)
        ping = r.ping()

        if ping:
            print("✓ Redis connection successful")

            # Show some Redis stats
            info = r.info()
            print(f"\n  Connected clients: {info.get('connected_clients', 'N/A')}")
            print(f"  Used memory: {info.get('used_memory_human', 'N/A')}")
            print(f"  Uptime (seconds): {info.get('uptime_in_seconds', 'N/A')}")
            return True
        else:
            print("✗ Redis ping failed")
            return False

    except Exception as e:
        print(f"✗ Error checking Redis: {e}")
        return False


def check_seed_data_info():
    """Show information about seed data configuration."""
    print_section("SEED DATA CONFIGURATION")

    environment = os.environ.get("ENVIRONMENT", "development")
    force_seed = os.environ.get("FORCE_SEED", "false").lower() == "true"

    print(f"Environment: {environment}")
    print(f"Force Seed: {force_seed}")

    print_subsection("Seeding Behavior")
    if environment == "production" and not force_seed:
        print("  ✓ Production mode - seeding DISABLED (set FORCE_SEED=true to override)")
    elif environment in ["development", "staging", "test"]:
        print(f"  ✓ {environment.title()} mode - seeding ENABLED")
    else:
        print(f"  ? Unknown environment: {environment}")

    # List available seed scripts
    print_subsection("Available Seed Scripts")
    seed_dir = Path(__file__).parent
    seed_scripts = sorted(seed_dir.glob("seed_*.py"))
    if seed_scripts:
        for script in seed_scripts:
            print(f"  • {script.name}")
    else:
        print("  ✗ No seed scripts found")


def show_configuration_summary():
    """Show a summary of critical configuration issues."""
    print_section("CONFIGURATION SUMMARY & WARNINGS")

    issues = []

    try:
        from app.core.config import get_settings
        settings = get_settings()

        # Check for production security issues
        if settings.is_production:
            if not settings.pii_encryption_enabled:
                issues.append({
                    "level": "CRITICAL",
                    "message": "PII_ENCRYPTION_ENABLED=false in production (GDPR/CCPA non-compliant)"
                })
            if not settings.database_require_ssl:
                issues.append({
                    "level": "CRITICAL",
                    "message": "DATABASE_REQUIRE_SSL=false in production"
                })
            if settings.debug:
                issues.append({
                    "level": "WARNING",
                    "message": "DEBUG=true in production"
                })

        # Check for required values
        if not settings.secret_key or settings.secret_key == "your_super_secret_key_here_change_this_in_production":
            issues.append({
                "level": "CRITICAL",
                "message": "SECRET_KEY not properly configured"
            })

        if not settings.jwt_secret or settings.jwt_secret == "your_jwt_secret_here_change_this_in_production":
            issues.append({
                "level": "CRITICAL",
                "message": "JWT_SECRET not properly configured"
            })

        # Check for hardcoded defaults
        if "localhost" in settings.database_url and settings.is_production:
            issues.append({
                "level": "WARNING",
                "message": "DATABASE_URL points to localhost in production"
            })

        # Check storage configuration
        if settings.storage_backend == "local" and settings.is_production:
            issues.append({
                "level": "WARNING",
                "message": "Using local storage backend in production (not recommended for horizontal scaling)"
            })

    except Exception as e:
        issues.append({
            "level": "ERROR",
            "message": f"Could not load settings: {e}"
        })

    if not issues:
        print("✓ No critical issues detected\n")
    else:
        for issue in issues:
            symbol = "🔴" if issue["level"] == "CRITICAL" else "🟡" if issue["level"] == "WARNING" else "🔵"
            print(f"{symbol} [{issue['level']}] {issue['message']}")


async def main():
    """Run the complete configuration debug."""

    print("\n" + "=" * 80)
    print("  LSC CONFIGURATION DEBUG REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Check for command line arguments
    check_db = "--check-db" in sys.argv or "--check-all" in sys.argv
    check_redis = "--check-redis" in sys.argv or "--check-all" in sys.argv

    # Run checks
    check_env_files()
    show_environment_variables()
    show_sensitive_variables()
    _ = show_pydantic_settings()
    show_docker_volumes()
    check_seed_data_info()
    show_configuration_summary()

    # Optional connectivity checks
    if check_db:
        await check_database_connection()

    if check_redis:
        await check_redis_connection()

    # Print final summary
    print_section("HOW TO USE THIS DEBUG REPORT")
    print("1. Verify .env file is being loaded (check ENVIRONMENT FILES section)")
    print("2. Confirm DATABASE_URL is correct (check LOADED PYDANTIC SETTINGS)")
    print("3. Look for any CRITICAL warnings in CONFIGURATION SUMMARY")
    print("4. For database issues, run: python scripts/debug_config.py --check-db")
    print("5. For Redis issues, run: python scripts/debug_config.py --check-redis")
    print("6. For all checks, run: python scripts/debug_config.py --check-all")

    print("\nCommon Issues to Check:")
    print("  • DATABASE_URL not set in .env")
    print("  • Wrong database host (check dev vs prod Docker Compose)")
    print("  • Port mismatch (dev uses 5434, prod uses 5432)")
    print("  • Hardcoded credentials overriding .env values")
    print("  • Docker volume not mounted for uploads")
    print("  • ENVIRONMENT variable not set correctly")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
