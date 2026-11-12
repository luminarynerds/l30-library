# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later


class PaginationDefaults:

    # Standard page size for most list endpoints (20 items)
    DEFAULT_PAGE_SIZE = 20

    # Standard page size for larger list views (50 items)
    DEFAULT_PAGE_SIZE_LARGE = 50

    # Small page size for suggestions, autocomplete, etc (10 items)
    DEFAULT_PAGE_SIZE_SMALL = 10

    # Maximum page size allowed (100 items)
    MAX_PAGE_SIZE = 100

    # Maximum page size for extended exports (200 items)
    MAX_PAGE_SIZE_EXTENDED = 200

    # Default skip/offset value
    DEFAULT_SKIP = 0
