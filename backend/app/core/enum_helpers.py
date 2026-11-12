# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum
from typing import Type

from sqlalchemy import Column
from sqlalchemy import Enum as SQLEnum


def enum_values(enum_cls: Type[Enum]) -> list[str]:
    return [m.value for m in enum_cls]


def EnumColumn(enum_cls: Type[Enum], **kwargs) -> Column:
    pg_type_name = kwargs.pop("pg_type_name", enum_cls.__name__.lower())
    create_type = kwargs.pop("create_type", False)
    return Column(
        SQLEnum(
            enum_cls,
            name=pg_type_name,
            create_type=create_type,
            values_callable=lambda x: [m.value for m in x],
        ),
        **kwargs,
    )
