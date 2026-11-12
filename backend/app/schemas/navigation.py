# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from pydantic import BaseModel


class NavigationItem(BaseModel):
    id: str
    label: str
    path: str
    icon: Optional[str] = None
    description: Optional[str] = None
    children: Optional[list['NavigationItem']] = None
    requiresAuth: bool = False
    roles: list[str] = []  # Empty = all roles, otherwise restricted to listed roles

    class Config:
        json_schema_extra = {
            "example": {
                "id": "staff_circulation",
                "label": "Circulation",
                "path": "/staff/circulation",
                "icon": "ArrowRightLeft",
                "description": "Manage checkouts and returns",
                "requiresAuth": True,
                "roles": ["STAFF", "ADMIN", "SUPER_ADMIN"],
                "children": None
            }
        }


class NavigationSection(BaseModel):
    id: str
    label: str
    items: list[NavigationItem]

    class Config:
        json_schema_extra = {
            "example": {
                "id": "staff_operations",
                "label": "Staff Operations",
                "items": []
            }
        }


class NavigationResponse(BaseModel):
    sections: list[NavigationSection]
    role: str
    canAccessAdmin: bool
    canAccessStaff: bool

    class Config:
        json_schema_extra = {
            "example": {
                "sections": [],
                "role": "STAFF",
                "canAccessAdmin": False,
                "canAccessStaff": True
            }
        }


# Update forward references
NavigationItem.update_forward_refs()
