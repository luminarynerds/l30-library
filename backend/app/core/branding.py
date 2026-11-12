# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings


def _find_branding_json() -> dict:
    candidates = [
        Path("/opt/l30/branding.json"),
        Path("/app/branding.json"),
        Path(__file__).resolve().parents[3] / "branding.json",
    ]
    for path in candidates:
        if path.is_file():
            with open(path) as f:
                data = json.load(f)
            return {k: v for k, v in data.items() if not k.startswith("_")}
    return {}


class BrandingSettings(BaseSettings):

    # --- Public-facing identity ---
    library_name: str = "Anytown Public Library"
    library_short_name: str = "APL"
    domain: str = "https://anytown.example"

    # Contact info
    contact_email: str = "hello@example.com"
    privacy_email: str = "privacy@example.com"
    indie_email: str = "indie@example.com"
    giving_email: str = "giving@example.com"
    events_email: str = "events@example.com"
    print_email: str = "print@example.com"
    makerspace_email: str = "makerspace@example.com"
    phone: str = "(555) 123-4567"
    address_line1: str = "123 Main Street"
    address_line2: str = ""
    city: str = "Anytown"
    state: str = "OH"
    zip_code: str = "44101"
    country: str = "USA"
    fax: str = ""

    # Legal / institutional
    legal_name: str = ""
    tax_id: str = ""
    state_library_id: str = ""
    governance_type: str = "municipal"
    fiscal_year_start_month: int = 1
    timezone: str = "America/New_York"

    # Visual identity
    primary_color: str = "#E89B44"
    accent_color: str = "#8B5E5E"

    # Demo / instance flags
    is_demo: bool = False

    # Social presence (fediverse / Bluesky). Empty string hides the link in the UI.
    bluesky_url: str = ""
    mastodon_url: str = ""

    # Seasonal callout (e.g. Summer Reading Challenge). False = hide block on landing.
    seasonal_callout_active: bool = False

    # Donate-page content (tiers, impact areas, monthly, ways-to-give, intro,
    # testimonials, tax note). Empty by default so a fresh install ships no
    # library-specific content; per-library content lives in the library_branding
    # DB row and overrides this. See DonatePage.tsx for the shape.
    donate_config: dict = {}

    # --- Product naming ---
    PRODUCT_NAME: str = "Library 2030"
    PRODUCT_SLUG: str = "library-2030"
    PRODUCT_FULL_NAME: str = "Library 2030 System"
    PRODUCT_TAGLINE: str = "Your library, reimagined"

    # Organization (for multi-tenant deployments)
    ORG_NAME: str = "Library 2030"
    ORG_SLUG: str = "l30"

    # URLs and identifiers
    PRODUCT_URL: str = "https://l30.org"
    SUPPORT_EMAIL: str = "hello@l30.org"
    DOCS_URL: str = "https://l30.org/docs"

    # API metadata
    API_TITLE: str = "Library 2030 API"
    API_DESCRIPTION: str = "Next-generation library platform"
    API_VERSION: str = "1.0.0"

    # System identifiers (used in card numbers, MARC records, cache keys, metrics)
    CARD_PREFIX: str = "L30"
    TEMP_CARD_PREFIX: str = "TMP"
    MARC_PREFIX: str = "L30"
    CACHE_NAMESPACE: str = "l30"
    METRICS_PREFIX: str = "l30"
    USER_AGENT: str = "Library-2030/1.0"

    @model_validator(mode="before")
    @classmethod
    def apply_json_overrides(cls, values):
        json_data = _find_branding_json()
        if json_data:
            for key, val in json_data.items():
                if key not in values or values[key] is None:
                    values[key] = val
        return values

    class Config:
        env_prefix = ""
        case_sensitive = False
        extra = "ignore"


@lru_cache
def get_branding() -> BrandingSettings:
    return BrandingSettings()


# Singleton instance for convenient imports
branding = get_branding()
