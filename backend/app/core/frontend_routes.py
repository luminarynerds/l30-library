# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class FrontendRoutes(BaseSettings):

    # --- Patron account ---
    account: str = Field(default="/account", alias="ROUTE_ACCOUNT")
    account_checkouts: str = Field(
        default="/my-account/checkouts", alias="ROUTE_ACCOUNT_CHECKOUTS"
    )
    account_holds: str = Field(
        default="/my-account/holds", alias="ROUTE_ACCOUNT_HOLDS"
    )
    account_fines: str = Field(
        default="/my-account/fines", alias="ROUTE_ACCOUNT_FINES"
    )
    account_settings: str = Field(
        default="/account/settings", alias="ROUTE_ACCOUNT_SETTINGS"
    )
    account_alerts: str = Field(
        default="/account/alerts", alias="ROUTE_ACCOUNT_ALERTS"
    )
    my_account: str = Field(default="/my-account", alias="ROUTE_MY_ACCOUNT")

    # --- Legacy /account/* paths (used by some job services) ---
    account_checkouts_alt: str = Field(
        default="/account/checkouts", alias="ROUTE_ACCOUNT_CHECKOUTS_ALT"
    )
    account_holds_alt: str = Field(
        default="/account/holds", alias="ROUTE_ACCOUNT_HOLDS_ALT"
    )

    # --- Catalog ---
    catalog: str = Field(default="/catalog", alias="ROUTE_CATALOG")
    catalog_item: str = Field(
        default="/catalog/{id}", alias="ROUTE_CATALOG_ITEM"
    )

    # --- Events ---
    events: str = Field(default="/events", alias="ROUTE_EVENTS")

    # --- Rooms ---
    rooms: str = Field(default="/rooms", alias="ROUTE_ROOMS")
    room_book: str = Field(
        default="/rooms/{id}/book", alias="ROUTE_ROOM_BOOK"
    )
    rooms_my_reservations: str = Field(
        default="/rooms/my-reservations", alias="ROUTE_ROOMS_MY_RESERVATIONS"
    )

    # --- Staff ---
    staff_acquisition: str = Field(
        default="/staff/acquisition", alias="ROUTE_STAFF_ACQUISITION"
    )
    staff_disputes_claims_returned: str = Field(
        default="/staff/disputes/claims-returned/{id}",
        alias="ROUTE_STAFF_DISPUTES_CLAIMS_RETURNED",
    )
    staff_panic_alerts: str = Field(
        default="/staff/panic-alerts/{id}", alias="ROUTE_STAFF_PANIC_ALERTS"
    )

    # --- Admin ---
    admin_databases: str = Field(
        default="/admin/databases/{id}", alias="ROUTE_ADMIN_DATABASES"
    )

    # --- Auth / account actions ---
    reset_password: str = Field(
        default="/reset-password", alias="ROUTE_RESET_PASSWORD"
    )
    verify_email: str = Field(
        default="/verify-email", alias="ROUTE_VERIFY_EMAIL"
    )
    auth_magic_link: str = Field(
        default="/auth/magic-link", alias="ROUTE_AUTH_MAGIC_LINK"
    )
    unsubscribe: str = Field(
        default="/unsubscribe", alias="ROUTE_UNSUBSCRIBE"
    )
    email_preferences: str = Field(
        default="/email-preferences", alias="ROUTE_EMAIL_PREFERENCES"
    )
    newsletter_confirm: str = Field(
        default="/newsletter/confirm", alias="ROUTE_NEWSLETTER_CONFIRM"
    )
    consent: str = Field(default="/consent", alias="ROUTE_CONSENT")

    # --- Indie author ---
    indie_dashboard: str = Field(
        default="/indie/dashboard", alias="ROUTE_INDIE_DASHBOARD"
    )

    # --- Card application ---
    card_application_status: str = Field(
        default="/card-application/status/{token}",
        alias="ROUTE_CARD_APPLICATION_STATUS",
    )

    # --- Assets ---
    logo: str = Field(default="/logo.png", alias="ROUTE_LOGO")

    class Config:
        env_prefix = ""
        case_sensitive = False

    def url(self, base_url: str, route: str, **kwargs) -> str:
        path = route.format(**kwargs) if kwargs else route
        return f"{base_url.rstrip('/')}{path}"


@lru_cache
def get_frontend_routes() -> FrontendRoutes:
    return FrontendRoutes()


# Singleton for convenient imports
routes = get_frontend_routes()
