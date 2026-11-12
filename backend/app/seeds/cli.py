# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from app.core.logging import get_logger
import sys
from argparse import ArgumentParser

from app.core.database import AsyncSessionLocal
from app.seeds.seeder import initialize_database
from app.seeds.bootstrap_library_system import bootstrap
from app.seeds.fix_sequences import fix_sequences

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = get_logger(__name__)


async def run_all_seeds(dry_run: bool = False, verbose: bool = False) -> bool:
    async with AsyncSessionLocal() as session:
        result = await initialize_database(session, dry_run=dry_run, verbose=verbose)
    if not dry_run:
        await fix_sequences()
    return result


async def run_bootstrap_seed(dry_run: bool = False, verbose: bool = False) -> bool:
    return await bootstrap(dry_run=dry_run, verbose=verbose)


def create_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Bébé Memorial Library - Database Seeding Tool",
        prog="lsc-seed",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="Seed command to execute",
    )

    # Seed all command
    seed_parser = subparsers.add_parser(
        "seed",
        help="Run all seed operations",
    )
    seed_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate seeding without committing changes",
    )

    # Bootstrap command
    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help="Run only bootstrap library system seed",
    )
    bootstrap_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate seeding without committing changes",
    )

    # Fix sequences command
    subparsers.add_parser(
        "fix-sequences",
        help="Reset all autoincrement sequences to match current MAX(id)",
    )

    # Default: show help if no command
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    return parser


async def main():
    parser = create_parser()
    args = parser.parse_args()

    # Configure verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")

    # Execute command
    if args.command == "seed":
        logger.info("Running all seed operations")
        success = await run_all_seeds(
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    elif args.command == "bootstrap":
        logger.info("Running bootstrap library system seed")
        success = await run_bootstrap_seed(
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    elif args.command == "fix-sequences":
        logger.info("Fixing autoincrement sequences")
        await fix_sequences()
        success = True
    else:
        parser.print_help()
        return

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
