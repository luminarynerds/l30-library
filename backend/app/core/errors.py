# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import HTTPException


class APIError(HTTPException):
    
    def __init__(
        self,
        status_code: int,
        user_message: str,
        staff_detail: str,
        next_steps: list[str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=user_message)
        self.staff_detail = staff_detail
        self.next_steps = next_steps or []
