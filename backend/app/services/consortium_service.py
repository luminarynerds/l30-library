# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.multi_branch import (
    Consortium,
    ConsortiumBilling,
    ConsortiumMember,
    ConsortiumMemberStatus,
    ConsortiumMemberType,
    ConsortiumPatronLink,
    ConsortiumSettings,
    ConsortiumTransaction,
    ConsortiumWhiteLabel,
    LibrarySystem,
    ReciprocalBorrowingSettings,
    BillingItemType,
    BillingStatus,
)
from app.models.user import User


class ConsortiumService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # CONSORTIUM MANAGEMENT
    # =========================================================================

    async def create_consortium(
        self,
        code: str,
        name: str,
        **kwargs
    ) -> Consortium:
        consortium = Consortium(
            code=code.upper(),
            name=name,
            **kwargs
        )
        self.db.add(consortium)
        await self.db.flush()

        # Create default consortium settings
        settings = ConsortiumSettings(consortium_id=consortium.id)
        self.db.add(settings)

        await self.db.commit()
        await self.db.refresh(consortium)
        return consortium

    async def get_consortium(self, consortium_id: int) -> Consortium | None:
        result = await self.db.execute(
            select(Consortium)
            .options(
                selectinload(Consortium.members).selectinload(ConsortiumMember.library_system),
                joinedload(Consortium.settings),
            )
            .where(Consortium.id == consortium_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_consortium_by_code(self, code: str) -> Consortium | None:
        result = await self.db.execute(
            select(Consortium).where(Consortium.code == code.upper())
        )
        return result.scalar_one_or_none()

    async def list_consortiums(
        self,
        active_only: bool = True
    ) -> list[Consortium]:
        query = select(Consortium)
        if active_only:
            query = query.where(Consortium.is_active == True)
        query = query.order_by(Consortium.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_consortium(
        self,
        consortium_id: int,
        **kwargs
    ) -> Consortium | None:
        consortium = await self.get_consortium(consortium_id)
        if not consortium:
            return None

        for key, value in kwargs.items():
            if hasattr(consortium, key):
                setattr(consortium, key, value)

        await self.db.commit()
        await self.db.refresh(consortium)
        return consortium

    async def update_consortium_settings(
        self,
        consortium_id: int,
        **kwargs
    ) -> ConsortiumSettings | None:
        result = await self.db.execute(
            select(ConsortiumSettings).where(
                ConsortiumSettings.consortium_id == consortium_id
            )
        )
        settings = result.scalar_one_or_none()

        if not settings:
            return None

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    # =========================================================================
    # MEMBER MANAGEMENT
    # =========================================================================

    async def add_member(
        self,
        consortium_id: int,
        library_system_id: int,
        member_type: ConsortiumMemberType = ConsortiumMemberType.FULL,
        joined_date: date | None = None,
        liaison_user_id: int | None = None,
        **kwargs
    ) -> ConsortiumMember:
        if joined_date is None:
            joined_date = date.today()

        member = ConsortiumMember(
            consortium_id=consortium_id,
            library_system_id=library_system_id,
            member_type=member_type,
            joined_date=joined_date,
            liaison_user_id=liaison_user_id,
            **kwargs
        )
        self.db.add(member)
        await self.db.flush()

        # Create default reciprocal borrowing settings
        reciprocal_settings = ReciprocalBorrowingSettings(member_id=member.id)
        self.db.add(reciprocal_settings)

        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def get_member(self, member_id: int) -> ConsortiumMember | None:
        result = await self.db.execute(
            select(ConsortiumMember)
            .options(
                joinedload(ConsortiumMember.library_system),
                joinedload(ConsortiumMember.consortium),
                joinedload(ConsortiumMember.reciprocal_settings),
                joinedload(ConsortiumMember.white_label),
            )
            .where(ConsortiumMember.id == member_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_member_by_system(
        self,
        consortium_id: int,
        library_system_id: int
    ) -> ConsortiumMember | None:
        result = await self.db.execute(
            select(ConsortiumMember).where(
                and_(
                    ConsortiumMember.consortium_id == consortium_id,
                    ConsortiumMember.library_system_id == library_system_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_members(
        self,
        consortium_id: int,
        status: ConsortiumMemberStatus | None = None,
        active_only: bool = True
    ) -> list[ConsortiumMember]:
        query = (
            select(ConsortiumMember)
            .options(joinedload(ConsortiumMember.library_system))
            .where(ConsortiumMember.consortium_id == consortium_id)
        )

        if status:
            query = query.where(ConsortiumMember.status == status)
        elif active_only:
            query = query.where(ConsortiumMember.status == ConsortiumMemberStatus.ACTIVE)

        result = await self.db.execute(query)
        return list(result.unique().scalars().all())

    async def update_member(
        self,
        member_id: int,
        **kwargs
    ) -> ConsortiumMember | None:
        member = await self.get_member(member_id)
        if not member:
            return None

        for key, value in kwargs.items():
            if hasattr(member, key):
                setattr(member, key, value)

        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def update_member_status(
        self,
        member_id: int,
        status: ConsortiumMemberStatus
    ) -> ConsortiumMember | None:
        return await self.update_member(member_id, status=status)

    # =========================================================================
    # RECIPROCAL BORROWING
    # =========================================================================

    async def update_reciprocal_settings(
        self,
        member_id: int,
        **kwargs
    ) -> ReciprocalBorrowingSettings | None:
        result = await self.db.execute(
            select(ReciprocalBorrowingSettings).where(
                ReciprocalBorrowingSettings.member_id == member_id
            )
        )
        settings = result.scalar_one_or_none()

        if not settings:
            return None

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def can_patron_borrow_at_member(
        self,
        patron_user_id: int,
        target_member_id: int
    ) -> tuple[bool, str | None]:
        # Get the patron
        result = await self.db.execute(
            select(User).where(User.id == patron_user_id)
        )
        patron = result.scalar_one_or_none()

        if not patron:
            return False, "Patron not found"

        if not patron.is_active:
            return False, "Patron account is inactive"

        # Get patron's home system membership
        if not patron.home_library_system_id:
            return False, "Patron has no home library system"

        # Find the target member
        target_member = await self.get_member(target_member_id)
        if not target_member:
            return False, "Target library not found"

        if target_member.status != ConsortiumMemberStatus.ACTIVE:
            return False, "Target library is not an active consortium member"

        # Check reciprocal settings
        if not target_member.reciprocal_settings:
            return False, "Reciprocal borrowing not configured"

        if not target_member.reciprocal_settings.allow_incoming_borrowers:
            return False, "Library does not accept reciprocal borrowers"

        # Check if patron's home system is in the same consortium
        home_member = await self.get_member_by_system(
            target_member.consortium_id,
            patron.home_library_system_id
        )

        if not home_member:
            return False, "Patron's home library is not in this consortium"

        if home_member.status != ConsortiumMemberStatus.ACTIVE:
            return False, "Patron's home library membership is not active"

        # Check if home system allows outgoing borrowers
        if not home_member.reciprocal_settings.allow_outgoing_borrowers:
            return False, "Patron's home library does not allow reciprocal borrowing"

        # Check patron link status
        patron_link = await self.get_patron_link(patron_user_id, target_member_id)
        if patron_link:
            if patron_link.blocked:
                return False, patron_link.blocked_reason or "Patron is blocked at this library"
            if not patron_link.is_active:
                return False, "Patron registration has expired"
            if patron_link.expires_at and patron_link.expires_at < datetime.now(timezone.utc):
                return False, "Patron registration has expired"

        return True, None

    async def get_patron_checkout_limits_at_member(
        self,
        patron_user_id: int,
        target_member_id: int
    ) -> dict[str, int]:
        target_member = await self.get_member(target_member_id)
        if not target_member or not target_member.reciprocal_settings:
            return {"checkout_limit": 0, "hold_limit": 0}

        return {
            "checkout_limit": target_member.reciprocal_settings.incoming_checkout_limit,
            "hold_limit": target_member.reciprocal_settings.incoming_hold_limit,
        }

    # =========================================================================
    # PATRON LINKING (Cross-authentication)
    # =========================================================================

    async def create_patron_link(
        self,
        home_user_id: int,
        home_member_id: int,
        linked_member_id: int,
        linked_card_number: str | None = None,
        expires_at: datetime | None = None
    ) -> ConsortiumPatronLink:
        # If no expiry set, use the registration validity from settings
        if expires_at is None:
            linked_member = await self.get_member(linked_member_id)
            if linked_member and linked_member.reciprocal_settings:
                days = linked_member.reciprocal_settings.registration_valid_days
                expires_at = datetime.now(timezone.utc) + timedelta(days=days)

        link = ConsortiumPatronLink(
            home_user_id=home_user_id,
            home_member_id=home_member_id,
            linked_member_id=linked_member_id,
            linked_card_number=linked_card_number,
            expires_at=expires_at,
        )
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def get_patron_link(
        self,
        user_id: int,
        linked_member_id: int
    ) -> ConsortiumPatronLink | None:
        result = await self.db.execute(
            select(ConsortiumPatronLink).where(
                and_(
                    ConsortiumPatronLink.home_user_id == user_id,
                    ConsortiumPatronLink.linked_member_id == linked_member_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_patron_links(
        self,
        user_id: int,
        active_only: bool = True
    ) -> list[ConsortiumPatronLink]:
        query = select(ConsortiumPatronLink).where(
            ConsortiumPatronLink.home_user_id == user_id
        )

        if active_only:
            now = datetime.now(timezone.utc)
            query = query.where(
                and_(
                    ConsortiumPatronLink.is_active == True,
                    ConsortiumPatronLink.blocked == False,
                    or_(
                        ConsortiumPatronLink.expires_at.is_(None),
                        ConsortiumPatronLink.expires_at > now
                    )
                )
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_patron_link_by_id(
        self,
        link_id: int,
    ) -> ConsortiumPatronLink | None:
        result = await self.db.execute(
            select(ConsortiumPatronLink).where(ConsortiumPatronLink.id == link_id)
        )
        return result.scalar_one_or_none()

    async def update_patron_link(
        self,
        link_id: int,
        **kwargs
    ) -> ConsortiumPatronLink | None:
        result = await self.db.execute(
            select(ConsortiumPatronLink).where(ConsortiumPatronLink.id == link_id)
        )
        link = result.scalar_one_or_none()

        if not link:
            return None

        for key, value in kwargs.items():
            if hasattr(link, key):
                setattr(link, key, value)

        await self.db.commit()
        await self.db.refresh(link)
        return link

    async def block_patron_at_member(
        self,
        user_id: int,
        linked_member_id: int,
        reason: str
    ) -> ConsortiumPatronLink | None:
        link = await self.get_patron_link(user_id, linked_member_id)
        if link:
            link.blocked = True
            link.blocked_reason = reason
            await self.db.commit()
            await self.db.refresh(link)
        return link

    async def record_patron_activity(
        self,
        user_id: int,
        linked_member_id: int
    ) -> ConsortiumPatronLink | None:
        link = await self.get_patron_link(user_id, linked_member_id)
        if link:
            link.last_used_at = datetime.now(timezone.utc)
            link.total_checkouts += 1
            await self.db.commit()
            await self.db.refresh(link)
        return link

    # =========================================================================
    # SHARED CATALOG
    # =========================================================================

    async def get_searchable_systems(
        self,
        consortium_id: int,
        requesting_system_id: int | None = None
    ) -> list[int]:
        consortium = await self.get_consortium(consortium_id)
        if not consortium or not consortium.settings:
            return []

        if not consortium.settings.enable_shared_catalog:
            # Only search the requesting system
            return [requesting_system_id] if requesting_system_id else []

        if consortium.settings.catalog_search_all_members:
            # Get all active member system IDs
            members = await self.list_members(consortium_id, active_only=True)
            return [m.library_system_id for m in members]

        # Default: include only the requesting system
        return [requesting_system_id] if requesting_system_id else []

    # =========================================================================
    # WHITE LABELING
    # =========================================================================

    async def get_white_label_config(
        self,
        member_id: int
    ) -> ConsortiumWhiteLabel | None:
        result = await self.db.execute(
            select(ConsortiumWhiteLabel).where(
                ConsortiumWhiteLabel.member_id == member_id
            )
        )
        return result.scalar_one_or_none()

    async def update_white_label(
        self,
        member_id: int,
        **kwargs
    ) -> ConsortiumWhiteLabel:
        result = await self.db.execute(
            select(ConsortiumWhiteLabel).where(
                ConsortiumWhiteLabel.member_id == member_id
            )
        )
        config = result.scalar_one_or_none()

        if config:
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        else:
            config = ConsortiumWhiteLabel(member_id=member_id, **kwargs)
            self.db.add(config)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get_white_label_by_domain(
        self,
        domain: str
    ) -> ConsortiumWhiteLabel | None:
        result = await self.db.execute(
            select(ConsortiumWhiteLabel).where(
                or_(
                    ConsortiumWhiteLabel.custom_domain == domain,
                    ConsortiumWhiteLabel.subdomain == domain.split(".")[0]
                )
            )
        )
        return result.scalar_one_or_none()

    # =========================================================================
    # TRANSACTIONS (for billing)
    # =========================================================================

    async def record_transaction(
        self,
        consortium_id: int,
        transaction_type: str,
        lending_member_id: int | None = None,
        borrowing_member_id: int | None = None,
        item_copy_id: int | None = None,
        patron_user_id: int | None = None,
        fee_amount: Decimal = Decimal("0.00"),
        reference_type: str | None = None,
        reference_id: int | None = None,
        notes: str | None = None
    ) -> ConsortiumTransaction:
        transaction = ConsortiumTransaction(
            consortium_id=consortium_id,
            transaction_type=transaction_type,
            lending_member_id=lending_member_id,
            borrowing_member_id=borrowing_member_id,
            item_copy_id=item_copy_id,
            patron_user_id=patron_user_id,
            fee_amount=fee_amount,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
        )
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def get_unbilled_transactions(
        self,
        consortium_id: int,
        member_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None
    ) -> list[ConsortiumTransaction]:
        query = select(ConsortiumTransaction).where(
            and_(
                ConsortiumTransaction.consortium_id == consortium_id,
                ConsortiumTransaction.billed == False
            )
        )

        if member_id:
            query = query.where(
                or_(
                    ConsortiumTransaction.lending_member_id == member_id,
                    ConsortiumTransaction.borrowing_member_id == member_id
                )
            )

        if from_date:
            query = query.where(ConsortiumTransaction.transaction_date >= datetime.combine(from_date, datetime.min.time()))
        if to_date:
            query = query.where(ConsortiumTransaction.transaction_date <= datetime.combine(to_date, datetime.max.time()))

        query = query.order_by(ConsortiumTransaction.transaction_date)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # SSO / AUTHENTICATION
    # =========================================================================

    async def validate_sso_token(
        self,
        consortium_id: int,
        token: str,
        provider: str
    ) -> dict[str, Any] | None:
        consortium = await self.get_consortium(consortium_id)
        if not consortium or not consortium.settings:
            return None

        if not consortium.settings.enable_single_sign_on:
            return None

        if consortium.settings.sso_provider != provider:
            return None

        # Actual SSO validation would happen here based on provider
        # This is a placeholder that would integrate with SAML, OAuth2, etc.

        # Return user info if valid
        return None

    async def get_patron_home_member(
        self,
        user_id: int
    ) -> ConsortiumMember | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        patron = result.scalar_one_or_none()

        if not patron or not patron.home_library_system_id:
            return None

        # Find any consortium membership for this system
        result = await self.db.execute(
            select(ConsortiumMember)
            .options(joinedload(ConsortiumMember.consortium))
            .where(
                and_(
                    ConsortiumMember.library_system_id == patron.home_library_system_id,
                    ConsortiumMember.status == ConsortiumMemberStatus.ACTIVE
                )
            )
        )
        return result.unique().scalar_one_or_none()
