# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
from functools import lru_cache
from typing import Any, Callable, Dict, Optional

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en", "es"}
_TRANSLATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "translations"
)


@lru_cache(maxsize=10)
def _load_translations(lang: str) -> Dict[str, Any]:
    filepath = os.path.join(_TRANSLATIONS_DIR, f"{lang}.json")
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_key(data: Dict[str, Any], key: str) -> Optional[str]:
    parts = key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current if isinstance(current, str) else None


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
    # Normalize language code (e.g., "es-ES" -> "es")
    lang_code = lang.split("-")[0].lower() if lang else DEFAULT_LANGUAGE

    # Try target language first
    if lang_code != DEFAULT_LANGUAGE and lang_code in SUPPORTED_LANGUAGES:
        translations = _load_translations(lang_code)
        value = _resolve_key(translations, key)
        if value is not None:
            try:
                return value.format(**kwargs) if kwargs else value
            except (KeyError, IndexError):
                return value

    # Fall back to English
    translations = _load_translations(DEFAULT_LANGUAGE)
    value = _resolve_key(translations, key)
    if value is not None:
        try:
            return value.format(**kwargs) if kwargs else value
        except (KeyError, IndexError):
            return value

    # Key not found in any language
    return key


def get_translator(lang: str = DEFAULT_LANGUAGE) -> Callable[..., str]:
    def translator(key: str, **kwargs: Any) -> str:
        return t(key, lang=lang, **kwargs)
    return translator


def get_user_language(user: Any) -> str:
    lang = None

    # Check common attribute names for language preference
    for attr in ("language_preference", "language", "locale", "preferred_language"):
        lang = getattr(user, attr, None)
        if lang:
            break

    if not lang:
        return DEFAULT_LANGUAGE

    # Normalize
    lang_code = lang.split("-")[0].lower()

    # Map common language names to codes
    name_to_code = {
        "english": "en",
        "spanish": "es",
        "español": "es",
    }
    lang_code = name_to_code.get(lang_code, lang_code)

    return lang_code if lang_code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def is_supported_language(lang: str) -> bool:
    return lang.split("-")[0].lower() in SUPPORTED_LANGUAGES


async def get_patron_language(user: Any, db: Any = None) -> str:
    if db is not None and user is not None:
        try:
            from sqlalchemy import select
            from ..models.learning import UserPreferences

            user_id = getattr(user, "id", None)
            if user_id is not None:
                result = await db.execute(
                    select(UserPreferences.language_preference).where(
                        UserPreferences.user_id == user_id
                    )
                )
                lang = result.scalar_one_or_none()
                if lang:
                    lang_code = lang.split("-")[0].lower()
                    if lang_code in SUPPORTED_LANGUAGES:
                        return lang_code
        except Exception:  # noqa: BLE001 -- a language lookup must never break a notification send
            pass

    return get_user_language(user)
