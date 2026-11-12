# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later


class MetisLibError(Exception):

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class MetisLibUnavailable(MetisLibError):

    pass


class MetisLibTimeout(MetisLibError):

    pass


class MetisLibNotFound(MetisLibError):

    pass


class MetisLibAuthError(MetisLibError):

    pass


class MetisLibForbidden(MetisLibError):
    """MetisLib returned 403 -- the resource exists but this library can't
    access it (e.g. an indie title the library hasn't licensed). Distinct from
    MetisLibAuthError (401, a bad/rejected API key)."""



class MetisLibValidationError(MetisLibError):

    pass
