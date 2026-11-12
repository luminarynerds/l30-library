# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any, Callable

from ....core.error_codes import ErrorCode
from ....core.exceptions import ResourceNotFoundError


# TODO(destyle): consolidate with backend/app/core/response_utils.py:paginated_response when frontend can migrate from {key,total,limit,offset} to {data,pagination:{page,per_page,total,...}} shape
def paginated_response(*, key: str, items: list[Any], total: int, limit: int, offset: int, mapper: Callable[[Any], Any] | None = None) -> dict[str, Any]:
    converter = mapper or (lambda item: item)
    return {
        key: [converter(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def require_resource(resource: Any, *, message: str) -> Any:
    if resource is None:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message=message,
        )
    return resource
