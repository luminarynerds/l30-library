# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

# Decimal that serializes as a JSON number (float) rather than a string.
# Use as the type annotation for money fields in response schemas.
# Python-side semantics are unchanged: isinstance(x, Decimal) is still True,
# and model_dump() (non-JSON mode) still returns Decimal.
MoneyDecimal = Annotated[Decimal, PlainSerializer(float, when_used="json")]


class StrictInputSchema(BaseModel):

    model_config = ConfigDict(extra="forbid")
