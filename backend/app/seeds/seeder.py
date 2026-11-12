# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from enum import Enum
from typing import Callable, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.seeds.bootstrap_library_system import LibrarySystemBootstrap
from app.seeds.seed_event_data import seed_events_and_related_data
from app.seeds.seed_staff_knowledge_base import seed_staff_knowledge_base
from app.seeds.seed_knowledge_base_public import seed_knowledge_base_public
from app.seeds.seed_board_data import seed_board_data
from app.seeds.seed_board_data_full import seed_board_data_full
from app.seeds.seed_simple_domains import seed_simple_domains
from app.seeds.seed_medium_domains import seed_medium_domains
from app.seeds.seed_batch_patron import seed_batch_patron
from app.seeds.seed_batch_staff import seed_batch_staff
from app.seeds.seed_batch_facilities import seed_batch_facilities
from app.seeds.seed_batch_programs import seed_batch_programs
from app.seeds.seed_batch_digital import seed_batch_digital
from app.seeds.seed_batch_compliance import seed_batch_compliance
from app.seeds.seed_batch_learning import seed_batch_learning
from app.seeds.seed_learning_content import seed_learning_content
from app.seeds.seed_ai_curriculum import seed_ai_curriculum
from app.seeds.seed_batch_niche1 import seed_batch_niche1
from app.seeds.seed_batch_makerspace import seed_batch_makerspace
from app.seeds.seed_batch_patron_services import seed_batch_patron_services
from app.seeds.seed_batch_events_misc import seed_batch_events_misc
from app.seeds.seed_batch_system import seed_batch_system
from app.seeds.seed_batch_patron_facing import seed_batch_patron_facing
from app.seeds.seed_batch_staff_facing import seed_batch_staff_facing
from app.seeds.seed_batch_community import seed_batch_community
from app.seeds.seed_batch_operations import seed_batch_operations
from app.seeds.seed_community_resource_links import seed_community_resource_links
from app.seeds.seed_computers import seed_computers
from app.seeds.seed_missing_data import seed_missing_data
from app.seeds.seed_search_indexes import seed_search_indexes
from app.seeds.seed_acquisitions_data import seed_acquisitions_data
from app.seeds.seed_catalog_covers import seed_catalog_covers

logger = get_logger(__name__)


class SeedPriority(int, Enum):
    CRITICAL = 1  # Must run first (system bootstrap)
    IMPORTANT = 2  # Core data structures
    NORMAL = 3  # Standard data


class SeedTask:

    def __init__(
        self,
        name: str,
        priority: SeedPriority,
        func: Callable,
        description: str = "",
        required: bool = True,
    ):
        self.name = name
        self.priority = priority
        self.func = func
        self.description = description
        self.required = required


class DatabaseSeeder:

    def __init__(self, session: AsyncSession, dry_run: bool = False, verbose: bool = False):
        self.session = session
        self.dry_run = dry_run
        self.verbose = verbose
        self.tasks: List[SeedTask] = []
        self.results: dict = {}

    def register_task(
        self,
        name: str,
        priority: SeedPriority,
        func: Callable,
        description: str = "",
        required: bool = True,
    ) -> None:
        task = SeedTask(name, priority, func, description, required)
        self.tasks.append(task)

    async def run(self) -> bool:
        if not self.tasks:
            logger.info("No seed tasks registered")
            return True

        # Sort by priority
        sorted_tasks = sorted(self.tasks, key=lambda t: t.priority.value)

        logger.info("=" * 70)
        logger.info("DATABASE SEEDING")
        logger.info("=" * 70)
        if self.dry_run:
            logger.warning("DRY RUN MODE - Changes will not be committed")
        logger.info(f"Executing {len(sorted_tasks)} seed tasks in priority order")
        logger.info("=" * 70)

        success = True
        succeeded = 0
        failed = 0

        for task in sorted_tasks:
            try:
                logger.info(f"\n[{task.priority.name}] Running: {task.name}")
                if task.description:
                    logger.info(f"  Description: {task.description}")

                # Use savepoint so one task failure doesn't poison the session
                async with self.session.begin_nested():
                    result = await task.func()

                self.results[task.name] = {"success": result, "error": None}

                if result:
                    logger.info(f"  Status: SUCCESS")
                    succeeded += 1
                else:
                    logger.error(f"  Status: FAILED")
                    failed += 1
                    if task.required:
                        success = False
                        logger.error(f"  {task.name} is required - stopping seed execution")
                        break

            except Exception as e:  # noqa: BLE001  # task orchestrator — any task failure must be captured and recorded, not crash the run
                logger.error(f"  Status: ERROR - {e}")
                self.results[task.name] = {"success": False, "error": str(e)}
                failed += 1

                if task.required:
                    success = False
                    logger.error(f"  {task.name} is required - stopping seed execution")
                    break

        # Commit or rollback
        if not self.dry_run:
            try:
                await self.session.commit()
                logger.info("\n" + "=" * 70)
                logger.info(f"Seeding complete: {succeeded} succeeded, {failed} failed")
                logger.info("=" * 70)
            except Exception as e:
                logger.error(f"Error committing seed data: {e}", exc_info=True)
                await self.session.rollback()
                success = False
        elif self.dry_run:
            await self.session.rollback()
            logger.info("\n" + "=" * 70)
            logger.info("DRY RUN COMPLETE - All changes rolled back")
            logger.info("=" * 70)

        return success


async def seed_bootstrap_library_system(
    session: AsyncSession,
    dry_run: bool = False,
    verbose: bool = False
) -> bool:
    seeder = LibrarySystemBootstrap(session, dry_run=dry_run, verbose=verbose)
    return await seeder.run()


async def initialize_database(
    session: AsyncSession,
    dry_run: bool = False,
    verbose: bool = False
) -> bool:
    seeder = DatabaseSeeder(session, dry_run=dry_run, verbose=verbose)

    # Register all seed tasks in order of priority
    seeder.register_task(
        name="bootstrap_library_system",
        priority=SeedPriority.CRITICAL,
        func=lambda: seed_bootstrap_library_system(session, dry_run, verbose),
        description="Create main library system, regions, and branches",
        required=True,
    )

    seeder.register_task(
        name="seed_events",
        priority=SeedPriority.IMPORTANT,
        func=lambda: seed_events_and_related_data(session),
        description="Create comprehensive event seed data with registrations, reviews, and attendance info",
        required=False,
    )

    seeder.register_task(
        name="seed_staff_knowledge_base",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_staff_knowledge_base(session),
        description="Populate staff knowledge base with articles, decision trees, videos, and Q&A",
        required=False,
    )

    seeder.register_task(
        name="seed_knowledge_base_public",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_knowledge_base_public(session),
        description="Patron-facing FAQs, guides, policies, how-tos, read-alikes, chatbot patterns, seasonal FAQs",
        required=False,
    )

    seeder.register_task(
        name="seed_board_data",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_board_data(session),
        description="Board governance: members, meetings, committees, motions, minutes",
        required=False,
    )
    seeder.register_task(
        name="seed_board_data_full",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_board_data_full(session),
        description="Comprehensive board governance: 8 members, 5 committees, 12 meetings, 72 agenda items, minutes, documents, motions, resolutions",
        required=False,
    )
    seeder.register_task(
        name="seed_simple_domains",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_simple_domains(session),
        description="Simple domains: cookies, sightings, reviews, achievements, policies",
        required=False,
    )
    seeder.register_task(
        name="seed_medium_domains",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_medium_domains(session),
        description="Strategic planning, staff scheduling, outreach, equipment, visit stats",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_patron",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_patron(session),
        description="Patron reading history, preferences, notifications, tags, leaderboards",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_staff",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_staff(session),
        description="Staff training, certifications, EOD checklists, recognition, onboarding",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_facilities",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_facilities(session),
        description="Security systems, emergency resources, building closures, printing",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_programs",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_programs(session),
        description="Programs, volunteers, ESL, cultural events, teen advisory",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_digital",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_digital(session),
        description="Digital access, streaming, signage, RFID, SIP2, computer sessions",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_compliance",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_compliance(session),
        description="Compliance, legal services, policies, insurance, annual reports",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_learning",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_learning(session),
        description="Learning platform, literacy programs, assessments, tutoring",
        required=False,
    )
    seeder.register_task(
        name="seed_learning_content",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_learning_content(session),
        description="Comprehensive learning content: courses, modules, lessons, paths, enrollments, badges, skills, milestones, assessments, analytics",
        required=False,
    )
    seeder.register_task(
        name="seed_ai_curriculum",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_ai_curriculum(session),
        description="AI training curriculum: 4 courses, learning path, facilitator guides",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_niche1",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_niche1(session),
        description="Cannabis info center, genealogy, terpenes, strain data",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_makerspace",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_makerspace(session),
        description="Makerspace, equipment, comics, manga, collections management",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_patron_services",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_patron_services(session),
        description="Homebound, delivery, patron accounts, tech assistance, cards",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_events_misc",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_events_misc(session),
        description="Events, marketing, SMS, welcome packets, donations, workflows",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_system",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_system(session),
        description="System config, RBAC, AI, scheduling extras, documents, wellness",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_patron_facing",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_patron_facing(session),
        description="Reading programs, log entries, prizes, featured ebooks, storytime, certificates, chatbot",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_staff_facing",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_staff_facing(session),
        description="KB articles, decision trees, dashboards, executive reports, impact stories, courses",
        required=False,
    )

    seeder.register_task(
        name="seed_batch_community",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_community(session),
        description="Reading activities, milestones, ambassadors, parent groups, mentorship, quiz attempts, overflow purchases, found items, room waitlist, session extensions",
        required=False,
    )
    seeder.register_task(
        name="seed_batch_operations",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_batch_operations(session),
        description="Budget, ILL costs/tracking, serials, transit, repairs, imports, volunteers, attendance, feedback, content flags, damaged items, skills, committees",
        required=False,
    )

    seeder.register_task(
        name="community_resource_links",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_community_resource_links(session),
        description="Community resource link placeholders",
        required=False,
    )


    seeder.register_task(
        name="seed_computers",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_computers(),
        description="Computer lab: 21 computers, reservations, sessions, guest passes, waitlist",
        required=False,
    )

    seeder.register_task(
        name="seed_missing_data",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_missing_data(session),
        description="Printers, vendors, volunteers, teens, makerspace, comics, storytime, streaming, databases, ILL, transit, serials, newsletters, marketing, board reports, repairs",
        required=False,
    )

    seeder.register_task(
        name="seed_search_indexes",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_search_indexes(session),
        description="FTS: search_tsv column, trigger, GIN indexes, enum case fixes",
        required=False,
    )

    seeder.register_task(
        name="seed_acquisitions_data",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_acquisitions_data(session),
        description="Acquisitions: selection list items, order templates, additional purchase orders",
        required=False,
    )
    seeder.register_task(
        name="seed_catalog_covers",
        priority=SeedPriority.NORMAL,
        func=lambda: seed_catalog_covers(session),
        description="Unsplash placeholder cover images for all catalog items",
        required=False,
    )

    # Execute all tasks
    return await seeder.run()
