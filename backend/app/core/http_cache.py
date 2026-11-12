# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable

from fastapi import Response

from .cache_strategies import CacheTTL

__all__ = ["cache_for", "CacheTTL"]


def cache_for(ttl_seconds: int, *, public: bool = True) -> Callable[[Response], None]:
    scope = "public" if public else "private"
    header = f"{scope}, max-age={int(ttl_seconds)}"

    def _set_headers(response: Response) -> None:
        response.headers["Cache-Control"] = header
        existing_vary = response.headers.get("Vary")
        if existing_vary:
            if "Accept-Encoding" not in existing_vary:
                response.headers["Vary"] = f"{existing_vary}, Accept-Encoding"
        else:
            response.headers["Vary"] = "Accept-Encoding"

    return _set_headers
