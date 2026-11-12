# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..clients import PalaceClient
from ..clients.streaming_base import BaseStreamingClient, StreamingClientError, StreamingContent
from ..models.streaming import (
    DefaultPatronStreamingLimit,
    PatronStreamingLimit,
    StreamingBudget,
    StreamingCatalogItem,
    StreamingCheckout,
    StreamingCheckoutStatus,
    StreamingContentType,
    StreamingService,
    StreamingServiceConfig,
    StreamingUsageStats,
)
from ..models.user import User
from ..schemas.streaming import (
    BulkStreamingAvailability,
    CatalogStreamingAvailability,
    CollectionDevelopmentReport,
    DeepLinkResponse,
    PatronStreamingDashboard,
    PatronStreamingOverview,
    StreamingBudgetResponse,
    StreamingCatalogItemResponse,
    StreamingCheckoutResponse,
    StreamingDashboardStats,
    StreamingUsageStatsResponse,
    UnifiedSearchResponse,
)
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class StreamingServiceError(Exception):
    pass


class BudgetExceededError(StreamingServiceError):
    pass


class CheckoutLimitExceededError(StreamingServiceError):
    pass


class StreamingServiceManager:

    def __init__(self, db: AsyncSession):
        self.db = db
        self._clients: dict[StreamingService, BaseStreamingClient] = {}

    async def _get_client(self, service: StreamingService) -> BaseStreamingClient:
        if service in self._clients:
            return self._clients[service]

        # Get service configuration from database
        result = await self.db.execute(
            select(StreamingServiceConfig).where(StreamingServiceConfig.service == service)
        )
        config = result.scalar_one_or_none()
        if not config or not config.is_active:
            raise StreamingServiceError(f"Service {service.value} is not configured or inactive")

        if service == StreamingService.PALACE:
            client = PalaceClient(
                base_url=config.api_base_url,
                api_key=config.api_key,
                api_secret=config.api_secret,
                library_id=config.library_id,
            )
        else:
            raise StreamingServiceError(f"Unknown service: {service}")

        self._clients[service] = client
        return client

    async def _get_all_active_configs(self) -> list[StreamingServiceConfig]:
        result = await self.db.execute(
            select(StreamingServiceConfig).where(StreamingServiceConfig.is_active == True)
        )
        return list(result.scalars().all())

    async def close_clients(self) -> None:
        for client in self._clients.values():
            await client.close()
        self._clients.clear()

    # =========================================================================
    # Service Configuration
    # =========================================================================

    async def get_service_configs(self) -> list[StreamingServiceConfig]:
        result = await self.db.execute(select(StreamingServiceConfig))
        return list(result.scalars().all())

    async def create_service_config(
        self,
        service: StreamingService,
        api_base_url: str,
        api_key: str | None = None,
        api_secret: str | None = None,
        library_id: str | None = None,
        cost_per_checkout: Decimal = Decimal("0.00"),
        app_deep_link_template: str | None = None,
        web_deep_link_template: str | None = None,
    ) -> StreamingServiceConfig:
        config = StreamingServiceConfig(
            service=service,
            is_active=True,
            api_base_url=api_base_url,
            api_key=api_key,
            api_secret=api_secret,
            library_id=library_id,
            cost_per_checkout=cost_per_checkout,
            app_deep_link_template=app_deep_link_template,
            web_deep_link_template=web_deep_link_template,
        )
        self.db.add(config)
        await self.db.flush()
        return config

    async def update_service_config(
        self,
        config_id: int,
        **kwargs,
    ) -> StreamingServiceConfig | None:
        result = await self.db.execute(
            select(StreamingServiceConfig).where(StreamingServiceConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)

        config.updated_at = utc_now()
        await self.db.flush()
        return config

    # =========================================================================
    # Budget Management
    # =========================================================================

    async def create_budget(
        self,
        service_config_id: int,
        fiscal_year: int,
        allocated_amount: Decimal,
        fiscal_month: int | None = None,
        max_checkouts: int | None = None,
    ) -> StreamingBudget:
        budget = StreamingBudget(
            service_config_id=service_config_id,
            fiscal_year=fiscal_year,
            fiscal_month=fiscal_month,
            allocated_amount=allocated_amount,
            max_checkouts=max_checkouts,
        )
        self.db.add(budget)
        await self.db.flush()
        return budget

    async def get_current_budget(
        self,
        service_config_id: int,
    ) -> StreamingBudget | None:
        now = utc_now()
        current_year = now.year
        current_month = now.month

        # Try to find monthly budget first
        result = await self.db.execute(
            select(StreamingBudget).where(
                and_(
                    StreamingBudget.service_config_id == service_config_id,
                    StreamingBudget.fiscal_year == current_year,
                    StreamingBudget.fiscal_month == current_month,
                )
            )
        )
        budget = result.scalar_one_or_none()

        if budget:
            return budget

        # Fall back to annual budget
        result = await self.db.execute(
            select(StreamingBudget).where(
                and_(
                    StreamingBudget.service_config_id == service_config_id,
                    StreamingBudget.fiscal_year == current_year,
                    StreamingBudget.fiscal_month == None,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_budgets(
        self,
        service_config_id: int | None = None,
        fiscal_year: int | None = None,
    ) -> list[StreamingBudgetResponse]:
        query = select(StreamingBudget).options(
            selectinload(StreamingBudget.service_config)
        )

        if service_config_id:
            query = query.where(StreamingBudget.service_config_id == service_config_id)
        if fiscal_year:
            query = query.where(StreamingBudget.fiscal_year == fiscal_year)

        result = await self.db.execute(query)
        budgets = result.scalars().all()

        responses = []
        for budget in budgets:
            utilization = 0.0
            if budget.allocated_amount > 0:
                utilization = float(budget.spent_amount / budget.allocated_amount * 100)

            responses.append(StreamingBudgetResponse(
                id=budget.id,
                service_config_id=budget.service_config_id,
                service_name=str(budget.service_config.service) if budget.service_config else None,
                fiscal_year=budget.fiscal_year,
                fiscal_month=budget.fiscal_month,
                allocated_amount=budget.allocated_amount,
                spent_amount=budget.spent_amount,
                remaining_amount=budget.remaining_amount,
                max_checkouts=budget.max_checkouts,
                current_checkouts=budget.current_checkouts,
                remaining_checkouts=budget.remaining_checkouts,
                utilization_percentage=utilization,
                created_at=budget.created_at,
                updated_at=budget.updated_at,
            ))

        return responses

    async def check_budget_available(
        self,
        service_config_id: int,
        cost: Decimal,
    ) -> bool:
        budget = await self.get_current_budget(service_config_id)
        if not budget:
            return True  # No budget means no restrictions

        # Check monetary budget
        if budget.remaining_amount < cost:
            return False

        # Check checkout limit
        if budget.max_checkouts is not None and budget.remaining_checkouts is not None:
            if budget.remaining_checkouts <= 0:
                return False

        return True

    async def record_budget_usage(
        self,
        service_config_id: int,
        cost: Decimal,
    ) -> None:
        budget = await self.get_current_budget(service_config_id)
        if budget:
            budget.spent_amount += cost
            budget.current_checkouts += 1
            budget.updated_at = utc_now()

    # =========================================================================
    # Patron Limit Management
    # =========================================================================

    async def get_patron_limit(
        self,
        user_id: int,
        service_config_id: int,
    ) -> PatronStreamingLimit | None:
        result = await self.db.execute(
            select(PatronStreamingLimit).where(
                and_(
                    PatronStreamingLimit.user_id == user_id,
                    PatronStreamingLimit.service_config_id == service_config_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_patron_limit(
        self,
        user: User,
        service_config_id: int,
    ) -> PatronStreamingLimit:
        limit = await self.get_patron_limit(user.id, service_config_id)

        if limit:
            # Check if reset is needed
            if limit.limit_reset_date <= utc_now():
                limit.current_month_checkouts = 0
                limit.limit_reset_date = self._get_next_reset_date()
                limit.updated_at = utc_now()
            return limit

        # Get default limit for user's role
        default_limit = await self._get_default_limit(service_config_id, str(user.role))

        limit = PatronStreamingLimit(
            user_id=user.id,
            service_config_id=service_config_id,
            monthly_limit=default_limit,
            current_month_checkouts=0,
            limit_reset_date=self._get_next_reset_date(),
        )
        self.db.add(limit)
        await self.db.flush()
        return limit

    async def _get_default_limit(
        self,
        service_config_id: int,
        user_role: str,
    ) -> int:
        result = await self.db.execute(
            select(DefaultPatronStreamingLimit).where(
                and_(
                    DefaultPatronStreamingLimit.service_config_id == service_config_id,
                    DefaultPatronStreamingLimit.user_role == user_role,
                )
            )
        )
        default = result.scalar_one_or_none()
        return default.monthly_limit if default else 5  # Default to 5 if not configured

    def _get_next_reset_date(self) -> datetime:
        now = utc_now()
        # Reset on the 1st of next month
        if now.month == 12:
            return datetime(now.year + 1, 1, 1)
        return datetime(now.year, now.month + 1, 1)

    async def check_patron_limit(
        self,
        user: User,
        service_config_id: int,
    ) -> tuple[bool, int]:
        limit = await self.get_or_create_patron_limit(user, service_config_id)
        remaining = limit.remaining_checkouts
        return remaining > 0, remaining

    async def record_patron_checkout(
        self,
        user_id: int,
        service_config_id: int,
    ) -> None:
        limit = await self.get_patron_limit(user_id, service_config_id)
        if limit:
            limit.current_month_checkouts += 1
            limit.updated_at = utc_now()

    async def set_default_patron_limit(
        self,
        service_config_id: int,
        user_role: str,
        monthly_limit: int,
    ) -> DefaultPatronStreamingLimit:
        result = await self.db.execute(
            select(DefaultPatronStreamingLimit).where(
                and_(
                    DefaultPatronStreamingLimit.service_config_id == service_config_id,
                    DefaultPatronStreamingLimit.user_role == user_role,
                )
            )
        )
        default = result.scalar_one_or_none()

        if default:
            default.monthly_limit = monthly_limit
            default.updated_at = utc_now()
        else:
            default = DefaultPatronStreamingLimit(
                service_config_id=service_config_id,
                user_role=user_role,
                monthly_limit=monthly_limit,
            )
            self.db.add(default)

        await self.db.flush()
        return default

    # =========================================================================
    # Unified Search
    # =========================================================================

    async def unified_search(
        self,
        query: str,
        content_types: list[StreamingContentType] | None = None,
        services: list[StreamingService] | None = None,
        include_unavailable: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> UnifiedSearchResponse:
        configs = await self._get_all_active_configs()

        if services:
            configs = [c for c in configs if c.service in services]

        all_items: list[StreamingCatalogItemResponse] = []
        total_count = 0
        services_searched = []

        for config in configs:
            try:
                client = await self._get_client(config.service)
                items, count = await client.search(
                    query=query,
                    content_types=content_types,
                    page=page,
                    page_size=page_size,
                )

                services_searched.append(str(config.service))
                total_count += count

                for item in items:
                    if not include_unavailable and not item.is_available:
                        continue

                    # Cache item in database
                    db_item = await self._cache_catalog_item(config, item)

                    all_items.append(self._to_catalog_item_response(db_item, config))

            except StreamingClientError as e:
                logger.error(f"Error searching {config.service}: {e}")
                continue

        # Sort by title
        all_items.sort(key=lambda x: x.title.lower())

        # Calculate pagination
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

        return UnifiedSearchResponse(
            items=all_items[:page_size],  # Limit to page size
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            services_searched=services_searched,
            query=query,
        )

    async def _cache_catalog_item(
        self,
        config: StreamingServiceConfig,
        content: StreamingContent,
    ) -> StreamingCatalogItem:
        result = await self.db.execute(
            select(StreamingCatalogItem).where(
                and_(
                    StreamingCatalogItem.service_config_id == config.id,
                    StreamingCatalogItem.external_id == content.external_id,
                )
            )
        )
        db_item = result.scalar_one_or_none()

        if db_item:
            # Update existing
            db_item.title = content.title
            db_item.author = content.author
            db_item.description = content.description
            db_item.content_type = content.content_type
            db_item.isbn = content.isbn
            db_item.duration_minutes = content.duration_minutes
            db_item.release_year = content.release_year
            db_item.genres = json.dumps(content.genres) if content.genres else None
            db_item.cover_url = content.cover_url
            db_item.rating = content.rating
            db_item.is_available = content.is_available
            db_item.available_until = content.available_until
            db_item.last_synced_at = utc_now()
            db_item.updated_at = utc_now()
        else:
            # Create new
            db_item = StreamingCatalogItem(
                service_config_id=config.id,
                external_id=content.external_id,
                title=content.title,
                author=content.author,
                description=content.description,
                content_type=content.content_type,
                isbn=content.isbn,
                duration_minutes=content.duration_minutes,
                release_year=content.release_year,
                genres=json.dumps(content.genres) if content.genres else None,
                cover_url=content.cover_url,
                rating=content.rating,
                is_available=content.is_available,
                available_until=content.available_until,
            )
            self.db.add(db_item)

        await self.db.flush()
        return db_item

    def _to_catalog_item_response(
        self,
        item: StreamingCatalogItem,
        config: StreamingServiceConfig,
    ) -> StreamingCatalogItemResponse:
        # Generate deep links
        app_link = None
        web_link = None

        if config.app_deep_link_template:
            app_link = config.app_deep_link_template.replace("{content_id}", item.external_id)
        if config.web_deep_link_template:
            web_link = config.web_deep_link_template.replace("{content_id}", item.external_id)

        return StreamingCatalogItemResponse(
            id=item.id,
            service_config_id=item.service_config_id,
            service_name=str(config.service),
            external_id=item.external_id,
            title=item.title,
            author=item.author,
            description=item.description,
            content_type=item.content_type,
            isbn=item.isbn,
            duration_minutes=item.duration_minutes,
            release_year=item.release_year,
            genres=item.genres,
            cover_url=item.cover_url,
            rating=item.rating,
            is_available=item.is_available,
            available_until=item.available_until,
            catalog_item_id=item.catalog_item_id,
            last_synced_at=item.last_synced_at,
            created_at=item.created_at,
            app_deep_link=app_link,
            web_deep_link=web_link,
        )

    # =========================================================================
    # Checkout Management
    # =========================================================================

    async def checkout_content(
        self,
        user: User,
        streaming_item_id: int,
    ) -> StreamingCheckoutResponse:
        # Get the streaming item
        result = await self.db.execute(
            select(StreamingCatalogItem)
            .options(selectinload(StreamingCatalogItem.service_config))
            .where(StreamingCatalogItem.id == streaming_item_id)
        )
        item = result.scalar_one_or_none()

        if not item:
            raise StreamingServiceError("Streaming item not found")

        config = item.service_config
        if not config or not config.is_active:
            raise StreamingServiceError("Streaming service is not available")

        # Check budget
        if not await self.check_budget_available(config.id, config.cost_per_checkout):
            raise BudgetExceededError("Library streaming budget has been exceeded")

        # Check patron limit
        can_checkout, remaining = await self.check_patron_limit(user, config.id)
        if not can_checkout:
            raise CheckoutLimitExceededError(
                "You have reached your monthly checkout limit. "
                "Your limit will reset on the 1st of next month."
            )

        # Perform checkout with external service
        client = await self._get_client(config.service)
        checkout_result = await client.checkout(
            external_id=item.external_id,
            patron_barcode=user.library_card or str(user.id),
        )

        if not checkout_result.success:
            raise StreamingServiceError(
                checkout_result.error_message or "Checkout failed"
            )

        # Record checkout in database
        checkout = StreamingCheckout(
            user_id=user.id,
            service_config_id=config.id,
            streaming_item_id=item.id,
            external_checkout_id=checkout_result.external_checkout_id,
            status=StreamingCheckoutStatus.ACTIVE,
            expires_at=checkout_result.expires_at,
            cost=config.cost_per_checkout,
            item_title=item.title,
            item_content_type=item.content_type,
        )
        self.db.add(checkout)

        # Update budget and patron limit
        await self.record_budget_usage(config.id, config.cost_per_checkout)
        await self.record_patron_checkout(user.id, config.id)

        await self.db.flush()

        # Generate deep links
        app_link = client.get_app_deep_link(item.external_id)
        web_link = client.get_web_deep_link(item.external_id)

        return StreamingCheckoutResponse(
            id=checkout.id,
            user_id=checkout.user_id,
            service_config_id=checkout.service_config_id,
            service_name=str(config.service),
            streaming_item_id=checkout.streaming_item_id,
            external_checkout_id=checkout.external_checkout_id,
            status=checkout.status,
            checked_out_at=checkout.checked_out_at,
            expires_at=checkout.expires_at,
            returned_at=checkout.returned_at,
            cost=checkout.cost,
            item_title=checkout.item_title,
            item_content_type=checkout.item_content_type,
            cover_url=item.cover_url,
            app_deep_link=app_link,
            web_deep_link=web_link,
        )

    async def return_content(
        self,
        user: User,
        checkout_id: int,
    ) -> bool:
        result = await self.db.execute(
            select(StreamingCheckout)
            .options(selectinload(StreamingCheckout.service_config))
            .where(
                and_(
                    StreamingCheckout.id == checkout_id,
                    StreamingCheckout.user_id == user.id,
                    StreamingCheckout.status == StreamingCheckoutStatus.ACTIVE,
                )
            )
        )
        checkout = result.scalar_one_or_none()

        if not checkout:
            raise StreamingServiceError("Active checkout not found")

        config = checkout.service_config

        # Return with external service
        client = await self._get_client(config.service)
        success = await client.return_content(
            external_checkout_id=checkout.external_checkout_id or "",
            patron_barcode=user.library_card or str(user.id),
        )

        # Update checkout status regardless of external result
        checkout.status = StreamingCheckoutStatus.RETURNED
        checkout.returned_at = utc_now()
        checkout.updated_at = utc_now()

        await self.db.flush()
        return success

    async def get_patron_checkouts(
        self,
        user_id: int,
        status: StreamingCheckoutStatus | None = None,
    ) -> list[StreamingCheckoutResponse]:
        query = (
            select(StreamingCheckout)
            .options(
                selectinload(StreamingCheckout.service_config),
                selectinload(StreamingCheckout.streaming_item),
            )
            .where(StreamingCheckout.user_id == user_id)
            .order_by(StreamingCheckout.checked_out_at.desc())
        )

        if status:
            query = query.where(StreamingCheckout.status == status)

        result = await self.db.execute(query)
        checkouts = result.scalars().all()

        responses = []
        for checkout in checkouts:
            config = checkout.service_config
            item = checkout.streaming_item

            app_link = None
            web_link = None
            cover_url = None

            if config and item:
                if config.app_deep_link_template:
                    app_link = config.app_deep_link_template.replace("{content_id}", item.external_id)
                if config.web_deep_link_template:
                    web_link = config.web_deep_link_template.replace("{content_id}", item.external_id)
                cover_url = item.cover_url

            responses.append(StreamingCheckoutResponse(
                id=checkout.id,
                user_id=checkout.user_id,
                service_config_id=checkout.service_config_id,
                service_name=str(config.service) if config else None,
                streaming_item_id=checkout.streaming_item_id,
                external_checkout_id=checkout.external_checkout_id,
                status=checkout.status,
                checked_out_at=checkout.checked_out_at,
                expires_at=checkout.expires_at,
                returned_at=checkout.returned_at,
                cost=checkout.cost,
                item_title=checkout.item_title,
                item_content_type=checkout.item_content_type,
                cover_url=cover_url,
                app_deep_link=app_link,
                web_deep_link=web_link,
            ))

        return responses

    # =========================================================================
    # Patron Dashboard
    # =========================================================================

    async def get_patron_dashboard(
        self,
        user: User,
    ) -> PatronStreamingDashboard:
        configs = await self._get_all_active_configs()

        services = []
        total_active = 0

        for config in configs:
            limit = await self.get_or_create_patron_limit(user, config.id)

            # Get active checkouts for this service
            active_checkouts = await self.get_patron_checkouts(
                user.id,
                status=StreamingCheckoutStatus.ACTIVE,
            )
            service_checkouts = [
                c for c in active_checkouts
                if c.service_config_id == config.id
            ]
            total_active += len(service_checkouts)

            services.append(PatronStreamingOverview(
                service=config.service,
                service_name=str(config.service).title(),
                monthly_limit=limit.monthly_limit,
                current_month_checkouts=limit.current_month_checkouts,
                remaining_checkouts=limit.remaining_checkouts,
                limit_reset_date=limit.limit_reset_date,
                active_checkouts=service_checkouts,
                is_available=config.is_active,
            ))

        # Get recent checkouts (last 30 days)
        result = await self.db.execute(
            select(StreamingCheckout)
            .options(
                selectinload(StreamingCheckout.service_config),
                selectinload(StreamingCheckout.streaming_item),
            )
            .where(
                and_(
                    StreamingCheckout.user_id == user.id,
                    StreamingCheckout.checked_out_at >= utc_now() - timedelta(days=30),
                )
            )
            .order_by(StreamingCheckout.checked_out_at.desc())
            .limit(10)
        )
        recent_raw = result.scalars().all()

        recent_checkouts = []
        for checkout in recent_raw:
            config = checkout.service_config
            item = checkout.streaming_item

            app_link = None
            web_link = None
            cover_url = None

            if config and item:
                if config.app_deep_link_template:
                    app_link = config.app_deep_link_template.replace("{content_id}", item.external_id)
                if config.web_deep_link_template:
                    web_link = config.web_deep_link_template.replace("{content_id}", item.external_id)
                cover_url = item.cover_url

            recent_checkouts.append(StreamingCheckoutResponse(
                id=checkout.id,
                user_id=checkout.user_id,
                service_config_id=checkout.service_config_id,
                service_name=str(config.service) if config else None,
                streaming_item_id=checkout.streaming_item_id,
                external_checkout_id=checkout.external_checkout_id,
                status=checkout.status,
                checked_out_at=checkout.checked_out_at,
                expires_at=checkout.expires_at,
                returned_at=checkout.returned_at,
                cost=checkout.cost,
                item_title=checkout.item_title,
                item_content_type=checkout.item_content_type,
                cover_url=cover_url,
                app_deep_link=app_link,
                web_deep_link=web_link,
            ))

        return PatronStreamingDashboard(
            services=services,
            total_active_checkouts=total_active,
            recent_checkouts=recent_checkouts,
        )

    # =========================================================================
    # Catalog Integration
    # =========================================================================

    async def get_streaming_availability(
        self,
        catalog_item_id: int,
    ) -> CatalogStreamingAvailability:
        from ..models.catalog import CatalogItem

        # Get catalog item
        result = await self.db.execute(
            select(CatalogItem).where(CatalogItem.id == catalog_item_id)
        )
        catalog_item = result.scalar_one_or_none()

        if not catalog_item:
            raise StreamingServiceError("Catalog item not found")

        # Find linked streaming items
        result = await self.db.execute(
            select(StreamingCatalogItem)
            .options(selectinload(StreamingCatalogItem.service_config))
            .where(StreamingCatalogItem.catalog_item_id == catalog_item_id)
        )
        streaming_items = result.scalars().all()

        options = []
        for item in streaming_items:
            if item.service_config and item.service_config.is_active:
                options.append(self._to_catalog_item_response(item, item.service_config))

        return CatalogStreamingAvailability(
            catalog_item_id=catalog_item_id,
            catalog_item_title=catalog_item.title,
            streaming_options=options,
            has_streaming=len(options) > 0,
        )

    async def get_bulk_streaming_availability(
        self,
        catalog_item_ids: list[int],
    ) -> BulkStreamingAvailability:
        items = []
        for item_id in catalog_item_ids:
            try:
                availability = await self.get_streaming_availability(item_id)
                items.append(availability)
            except StreamingServiceError as e:
                logger.warning("Streaming availability check failed for item %s: %s", item_id, e)
                continue

        return BulkStreamingAvailability(items=items)

    async def link_to_catalog(
        self,
        streaming_item_id: int,
        catalog_item_id: int,
    ) -> StreamingCatalogItem:
        result = await self.db.execute(
            select(StreamingCatalogItem).where(StreamingCatalogItem.id == streaming_item_id)
        )
        item = result.scalar_one_or_none()

        if not item:
            raise StreamingServiceError("Streaming item not found")

        item.catalog_item_id = catalog_item_id
        item.updated_at = utc_now()
        await self.db.flush()
        return item

    # =========================================================================
    # Deep Links
    # =========================================================================

    async def get_deep_link(
        self,
        streaming_item_id: int,
        user: User | None = None,
    ) -> DeepLinkResponse:
        result = await self.db.execute(
            select(StreamingCatalogItem)
            .options(selectinload(StreamingCatalogItem.service_config))
            .where(StreamingCatalogItem.id == streaming_item_id)
        )
        item = result.scalar_one_or_none()

        if not item:
            raise StreamingServiceError("Streaming item not found")

        config = item.service_config

        app_link = None
        web_link = None

        if config:
            if config.app_deep_link_template:
                app_link = config.app_deep_link_template.replace("{content_id}", item.external_id)
            if config.web_deep_link_template:
                web_link = config.web_deep_link_template.replace("{content_id}", item.external_id)

        # Check if user has active checkout
        is_checked_out = False
        if user:
            result = await self.db.execute(
                select(StreamingCheckout).where(
                    and_(
                        StreamingCheckout.user_id == user.id,
                        StreamingCheckout.streaming_item_id == streaming_item_id,
                        StreamingCheckout.status == StreamingCheckoutStatus.ACTIVE,
                    )
                )
            )
            is_checked_out = result.scalar_one_or_none() is not None

        return DeepLinkResponse(
            streaming_item_id=item.id,
            service=config.service if config else StreamingService.PALACE,
            title=item.title,
            app_deep_link=app_link,
            web_deep_link=web_link,
            requires_checkout=True,
            is_checked_out=is_checked_out,
        )

    # =========================================================================
    # Analytics and Reporting
    # =========================================================================

    async def get_dashboard_stats(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> StreamingDashboardStats:
        if not start_date:
            start_date = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = utc_now()

        # Get checkouts in period
        result = await self.db.execute(
            select(StreamingCheckout)
            .options(selectinload(StreamingCheckout.service_config))
            .where(
                and_(
                    StreamingCheckout.checked_out_at >= start_date,
                    StreamingCheckout.checked_out_at <= end_date,
                )
            )
        )
        checkouts = list(result.scalars().all())

        total_checkouts = len(checkouts)
        total_cost = sum(c.cost for c in checkouts)
        unique_patrons = len(set(c.user_id for c in checkouts if c.user_id))
        avg_cost = total_cost / total_checkouts if total_checkouts > 0 else Decimal("0.00")

        # Per-service breakdown
        service_stats = {}
        for checkout in checkouts:
            service_name = str(checkout.service_config.service) if checkout.service_config else "unknown"
            if service_name not in service_stats:
                service_stats[service_name] = {
                    "service": service_name,
                    "checkouts": 0,
                    "cost": Decimal("0.00"),
                    "unique_patrons": set(),
                }
            service_stats[service_name]["checkouts"] += 1
            service_stats[service_name]["cost"] += checkout.cost
            if checkout.user_id:
                service_stats[service_name]["unique_patrons"].add(checkout.user_id)

        # Convert sets to counts
        service_stats_list = []
        for stats in service_stats.values():
            stats["unique_patrons"] = len(stats["unique_patrons"])
            stats["cost"] = float(stats["cost"])
            service_stats_list.append(stats)

        # Budget info
        configs = await self._get_all_active_configs()
        total_allocated = Decimal("0.00")
        total_spent = Decimal("0.00")

        for config in configs:
            budget = await self.get_current_budget(config.id)
            if budget:
                total_allocated += budget.allocated_amount
                total_spent += budget.spent_amount

        utilization = float(total_spent / total_allocated * 100) if total_allocated > 0 else 0.0

        # Top titles
        title_counts: dict[str, dict] = {}
        for checkout in checkouts:
            title = checkout.item_title or "Unknown"
            if title not in title_counts:
                title_counts[title] = {"title": title, "checkouts": 0, "content_type": checkout.item_content_type}
            title_counts[title]["checkouts"] += 1

        top_titles = sorted(title_counts.values(), key=lambda x: x["checkouts"], reverse=True)[:10]

        # Checkouts by content type
        type_counts: dict[str, int] = {}
        for checkout in checkouts:
            ct = str(checkout.item_content_type) if checkout.item_content_type else "unknown"
            type_counts[ct] = type_counts.get(ct, 0) + 1

        # Daily trend (last 30 days)
        trend: dict[str, int] = {}
        for checkout in checkouts:
            day = checkout.checked_out_at.strftime("%Y-%m-%d")
            trend[day] = trend.get(day, 0) + 1

        trend_list = [{"date": k, "checkouts": v} for k, v in sorted(trend.items())]

        return StreamingDashboardStats(
            total_checkouts_this_month=total_checkouts,
            total_cost_this_month=total_cost,
            unique_patrons_this_month=unique_patrons,
            average_cost_per_checkout=avg_cost,
            service_stats=service_stats_list,
            total_budget_allocated=total_allocated,
            total_budget_spent=total_spent,
            budget_utilization_percentage=utilization,
            top_titles=top_titles,
            checkouts_by_content_type=type_counts,
            checkouts_trend=trend_list,
        )

    async def get_collection_development_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> CollectionDevelopmentReport:
        # Get all checkouts in period
        result = await self.db.execute(
            select(StreamingCheckout)
            .options(
                selectinload(StreamingCheckout.service_config),
                selectinload(StreamingCheckout.streaming_item),
            )
            .where(
                and_(
                    StreamingCheckout.checked_out_at >= start_date,
                    StreamingCheckout.checked_out_at <= end_date,
                )
            )
        )
        checkouts = list(result.scalars().all())

        # Most watched titles
        title_data: dict[str, dict] = {}
        for checkout in checkouts:
            title = checkout.item_title or "Unknown"
            if title not in title_data:
                title_data[title] = {
                    "title": title,
                    "checkouts": 0,
                    "service": str(checkout.service_config.service) if checkout.service_config else None,
                    "content_type": str(checkout.item_content_type) if checkout.item_content_type else None,
                }
            title_data[title]["checkouts"] += 1

        most_watched = sorted(title_data.values(), key=lambda x: x["checkouts"], reverse=True)[:20]

        # Genre analysis
        genre_counts: dict[str, int] = {}
        for checkout in checkouts:
            if checkout.streaming_item and checkout.streaming_item.genres:
                try:
                    genres = json.loads(checkout.streaming_item.genres)
                    for genre in genres:
                        genre_counts[genre] = genre_counts.get(genre, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    pass

        most_watched_genres = sorted(
            [{"genre": k, "checkouts": v} for k, v in genre_counts.items()],
            key=lambda x: x["checkouts"],
            reverse=True,
        )[:10]

        # Content type breakdown
        type_counts: dict[str, int] = {}
        for checkout in checkouts:
            ct = str(checkout.item_content_type) if checkout.item_content_type else "unknown"
            type_counts[ct] = type_counts.get(ct, 0) + 1

        most_active_types = sorted(
            [{"content_type": k, "checkouts": v} for k, v in type_counts.items()],
            key=lambda x: x["checkouts"],
            reverse=True,
        )

        # Cost analysis
        total_cost = sum(c.cost for c in checkouts)
        cost_by_service: dict[str, Decimal] = {}
        cost_by_type: dict[str, Decimal] = {}

        for checkout in checkouts:
            service = str(checkout.service_config.service) if checkout.service_config else "unknown"
            cost_by_service[service] = cost_by_service.get(service, Decimal("0.00")) + checkout.cost

            ct = str(checkout.item_content_type) if checkout.item_content_type else "unknown"
            cost_by_type[ct] = cost_by_type.get(ct, Decimal("0.00")) + checkout.cost

        # Cost per checkout by service
        service_checkout_counts: dict[str, int] = {}
        for checkout in checkouts:
            service = str(checkout.service_config.service) if checkout.service_config else "unknown"
            service_checkout_counts[service] = service_checkout_counts.get(service, 0) + 1

        cost_per_checkout = {
            service: float(cost_by_service.get(service, 0) / count) if count > 0 else 0
            for service, count in service_checkout_counts.items()
        }

        # Patron engagement
        unique_patrons = len(set(c.user_id for c in checkouts if c.user_id))
        patron_by_service: dict[str, set] = {}
        for checkout in checkouts:
            if checkout.user_id:
                service = str(checkout.service_config.service) if checkout.service_config else "unknown"
                if service not in patron_by_service:
                    patron_by_service[service] = set()
                patron_by_service[service].add(checkout.user_id)

        engagement_by_service = {k: len(v) for k, v in patron_by_service.items()}

        # Repeat users (users with more than one checkout)
        user_checkout_counts: dict[int, int] = {}
        for checkout in checkouts:
            if checkout.user_id:
                user_checkout_counts[checkout.user_id] = user_checkout_counts.get(checkout.user_id, 0) + 1

        repeat_users = sum(1 for count in user_checkout_counts.values() if count > 1)
        repeat_rate = repeat_users / unique_patrons if unique_patrons > 0 else 0

        return CollectionDevelopmentReport(
            report_period_start=start_date,
            report_period_end=end_date,
            most_watched_titles=most_watched,
            most_watched_genres=most_watched_genres,
            most_active_content_types=most_active_types,
            total_cost=total_cost,
            cost_by_service={k: float(v) for k, v in cost_by_service.items()},
            cost_by_content_type={k: float(v) for k, v in cost_by_type.items()},
            cost_per_checkout_by_service=cost_per_checkout,
            total_unique_patrons=unique_patrons,
            patron_engagement_by_service=engagement_by_service,
            repeat_user_rate=repeat_rate,
            titles_frequently_unavailable=[],  # Would need tracking of failed checkouts
            recommended_additions=[],  # Would need more sophisticated analysis
        )

    async def aggregate_daily_stats(self, stat_date: datetime) -> None:
        start = stat_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        configs = await self._get_all_active_configs()

        for config in configs:
            # Get checkouts for the day
            result = await self.db.execute(
                select(StreamingCheckout).where(
                    and_(
                        StreamingCheckout.service_config_id == config.id,
                        StreamingCheckout.checked_out_at >= start,
                        StreamingCheckout.checked_out_at < end,
                    )
                )
            )
            checkouts = list(result.scalars().all())

            if not checkouts:
                continue

            total_checkouts = len(checkouts)
            unique_patrons = len(set(c.user_id for c in checkouts if c.user_id))
            total_cost = sum(c.cost for c in checkouts)

            # Content type breakdown
            type_counts: dict[str, int] = {}
            for checkout in checkouts:
                ct = str(checkout.item_content_type) if checkout.item_content_type else "unknown"
                type_counts[ct] = type_counts.get(ct, 0) + 1

            # Top items
            title_counts: dict[str, dict[str, Any]] = {}
            for checkout in checkouts:
                item_id = checkout.streaming_item_id
                if item_id:
                    if item_id not in title_counts:
                        title_counts[item_id] = {
                            "item_id": item_id,
                            "title": checkout.item_title,
                            "checkouts": 0,
                        }
                    title_counts[item_id]["checkouts"] += 1

            top_items = sorted(title_counts.values(), key=lambda x: x["checkouts"], reverse=True)[:10]

            # Create or update stats record
            result = await self.db.execute(
                select(StreamingUsageStats).where(
                    and_(
                        StreamingUsageStats.service_config_id == config.id,
                        StreamingUsageStats.stat_date == start,
                    )
                )
            )
            stats = result.scalar_one_or_none()

            if stats:
                stats.total_checkouts = total_checkouts
                stats.unique_patrons = unique_patrons
                stats.total_cost = total_cost
                stats.checkouts_by_type = json.dumps(type_counts)
                stats.top_items = json.dumps(top_items)
            else:
                stats = StreamingUsageStats(
                    service_config_id=config.id,
                    stat_date=start,
                    total_checkouts=total_checkouts,
                    unique_patrons=unique_patrons,
                    total_cost=total_cost,
                    checkouts_by_type=json.dumps(type_counts),
                    top_items=json.dumps(top_items),
                )
                self.db.add(stats)

        await self.db.flush()

    async def expire_checkouts(self) -> int:
        now = utc_now()

        result = await self.db.execute(
            select(StreamingCheckout).where(
                and_(
                    StreamingCheckout.status == StreamingCheckoutStatus.ACTIVE,
                    StreamingCheckout.expires_at != None,
                    StreamingCheckout.expires_at <= now,
                )
            )
        )
        expired_checkouts = result.scalars().all()

        for checkout in expired_checkouts:
            checkout.status = StreamingCheckoutStatus.EXPIRED
            checkout.updated_at = now

        await self.db.flush()
        return len(expired_checkouts)
