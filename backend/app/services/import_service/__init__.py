# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bulk import service package.

Public facade preserving the previous flat-module API. Internal
organization:

    constants.py  -- field sets, REQUIRED_FIELDS / TARGET_FIELDS maps, regexes
    templates.py  -- TEMPLATES dict (CSV import templates per job type)
    helpers.py    -- _detect_file_format, _similarity, _parse_date
    service.py    -- ImportService class (staged pipeline)

All historically-public names are re-exported here so callers and tests
can continue to from app.services.import_service import X.
"""

from app.models.import_job import (
    DuplicateAction,
    ImportFileFormat,
    ImportJob,
    ImportJobStatus,
    ImportJobType,
    ImportRecord,
    ImportRecordStatus,
)

from .constants import (
    BARCODE_PATTERN,
    CATALOG_ALL_FIELDS,
    CATALOG_OPTIONAL_FIELDS,
    CATALOG_REQUIRED_FIELDS,
    CIRC_ALL_FIELDS,
    CIRC_OPTIONAL_FIELDS,
    CIRC_REQUIRED_FIELDS,
    EMAIL_PATTERN,
    FINES_ALL_FIELDS,
    FINES_OPTIONAL_FIELDS,
    FINES_REQUIRED_FIELDS,
    HOLDINGS_ALL_FIELDS,
    HOLDINGS_OPTIONAL_FIELDS,
    HOLDINGS_REQUIRED_FIELDS,
    HOLDS_ALL_FIELDS,
    HOLDS_OPTIONAL_FIELDS,
    HOLDS_REQUIRED_FIELDS,
    ISBN_PATTERN,
    PATRON_ALL_FIELDS,
    PATRON_OPTIONAL_FIELDS,
    PATRON_REQUIRED_FIELDS,
    REQUIRED_FIELDS,
    TARGET_FIELDS,
)
from .helpers import _detect_file_format, _parse_date, _similarity
from .service import ImportService
from .templates import TEMPLATES

__all__ = [
    # Class
    "ImportService",
    # Re-exported model enums (historically importable from this module)
    "DuplicateAction",
    "ImportFileFormat",
    "ImportJob",
    "ImportJobStatus",
    "ImportJobType",
    "ImportRecord",
    "ImportRecordStatus",
    # Templates
    "TEMPLATES",
    # Helpers (underscore-prefixed but part of the public test surface)
    "_detect_file_format",
    "_parse_date",
    "_similarity",
    # Field maps
    "REQUIRED_FIELDS",
    "TARGET_FIELDS",
    # Per-entity field sets
    "PATRON_REQUIRED_FIELDS",
    "PATRON_OPTIONAL_FIELDS",
    "PATRON_ALL_FIELDS",
    "CATALOG_REQUIRED_FIELDS",
    "CATALOG_OPTIONAL_FIELDS",
    "CATALOG_ALL_FIELDS",
    "HOLDINGS_REQUIRED_FIELDS",
    "HOLDINGS_OPTIONAL_FIELDS",
    "HOLDINGS_ALL_FIELDS",
    "CIRC_REQUIRED_FIELDS",
    "CIRC_OPTIONAL_FIELDS",
    "CIRC_ALL_FIELDS",
    "FINES_REQUIRED_FIELDS",
    "FINES_OPTIONAL_FIELDS",
    "FINES_ALL_FIELDS",
    "HOLDS_REQUIRED_FIELDS",
    "HOLDS_OPTIONAL_FIELDS",
    "HOLDS_ALL_FIELDS",
    # Regex patterns
    "ISBN_PATTERN",
    "EMAIL_PATTERN",
    "BARCODE_PATTERN",
]
