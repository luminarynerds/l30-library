# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum
from typing import Optional

from app.models.user import User, UserRole
from app.schemas.navigation import NavigationItem, NavigationSection, NavigationResponse


class RoleHierarchy(Enum):
    PATRON = 0
    STAFF = 1
    ADMIN = 2
    SUPER_ADMIN = 3
    DIRECTOR = 3  # Director has same level as Super Admin
    LEGAL = 3  # Legal has same level as Super Admin


def get_role_level(role: UserRole) -> int:
    try:
        # RoleHierarchy members are named STAFF/ADMIN/... (uppercase);
        # role.value is the lowercase wire value ("staff"). Enum.__getitem__
        # looks up by member name, so role.value never matched anything
        # except by accident, and every non-PATRON role silently fell back
        # to PATRON's level (0) via the except below. role.name is the
        # member name itself and matches directly.
        return RoleHierarchy[role.name].value
    except KeyError:
        return RoleHierarchy.PATRON.value


def can_access_staff_pages(user: User) -> bool:
    return user.role in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL]


def can_access_admin_pages(user: User) -> bool:
    return user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]


def is_super_admin(user: User) -> bool:
    return user.role == UserRole.SUPER_ADMIN


def should_include_item(item: NavigationItem, user: User) -> bool:
    # If item has no role restrictions, include it
    if not item.roles:
        return not item.requiresAuth or user.id is not None

    # Check if user's role is in the allowed roles
    return user.role in [UserRole[role] for role in item.roles if role in UserRole.__members__]


def get_navigation_structure() -> dict[str, list[NavigationSection]]:
    return {
        "STAFF": [
            NavigationSection(
                id="staff_main",
                label="Staff Operations",
                items=[
                    NavigationItem(
                        id="staff_home",
                        label="Staff Home",
                        path="/staff",
                        icon="Briefcase",
                        description="Staff dashboard and main operations",
                        requiresAuth=True,
                        roles=["STAFF", "ADMIN", "SUPER_ADMIN", "DIRECTOR", "LEGAL"]
                    ),
                    NavigationItem(
                        id="staff_circulation",
                        label="Circulation",
                        path="/staff/circulation",
                        icon="ArrowRightLeft",
                        description="Manage checkouts and returns",
                        requiresAuth=True,
                        roles=["STAFF", "ADMIN", "SUPER_ADMIN", "DIRECTOR", "LEGAL"]
                    ),
                    NavigationItem(
                        id="staff_patrons",
                        label="Patrons",
                        path="/staff/patrons",
                        icon="Users",
                        description="Manage patron accounts and records",
                        requiresAuth=True,
                        roles=["STAFF", "ADMIN", "SUPER_ADMIN", "DIRECTOR", "LEGAL"]
                    ),
                    NavigationItem(
                        id="staff_catalog",
                        label="Catalog Management",
                        path="/staff/catalog-management",
                        icon="BookOpen",
                        description="Manage library catalog and items",
                        requiresAuth=True,
                        roles=["STAFF", "ADMIN", "SUPER_ADMIN", "DIRECTOR", "LEGAL"]
                    ),
                    NavigationItem(
                        id="staff_acquisition",
                        label="Acquisition",
                        path="/staff/acquisition",
                        icon="ShoppingCart",
                        description="Manage purchase orders and acquisitions",
                        requiresAuth=True,
                        roles=["STAFF", "ADMIN", "SUPER_ADMIN", "DIRECTOR", "LEGAL"]
                    ),
                ]
            ),
            NavigationSection(
                id="staff_tools",
                label="Tools",
                items=[
                    NavigationItem(
                        id="staff_reports",
                        label="Reports",
                        path="/staff/reports",
                        icon="BarChart3",
                        description="View circulation and analytics reports",
                        requiresAuth=True,
                        roles=["STAFF", "ADMIN", "SUPER_ADMIN", "DIRECTOR", "LEGAL"]
                    ),
                    NavigationItem(
                        id="staff_announcements",
                        label="Announcements",
                        path="/staff/announcements",
                        icon="Bell",
                        description="Create and manage library announcements",
                        requiresAuth=True,
                        roles=["STAFF", "ADMIN", "SUPER_ADMIN", "DIRECTOR", "LEGAL"]
                    ),
                ]
            ),
        ],
        "ADMIN": [
            # All staff sections
            *[],  # Will be merged with STAFF sections
            NavigationSection(
                id="admin_settings",
                label="Administration",
                items=[
                    NavigationItem(
                        id="admin_features",
                        label="Feature Flags",
                        path="/admin/features",
                        icon="Settings",
                        description="Enable/disable site features",
                        requiresAuth=True,
                        roles=["ADMIN", "SUPER_ADMIN"]
                    ),
                    NavigationItem(
                        id="admin_site_settings",
                        label="Site Settings",
                        path="/admin/site-settings",
                        icon="Monitor",
                        description="Configure site-wide settings",
                        requiresAuth=True,
                        roles=["ADMIN", "SUPER_ADMIN"]
                    ),
                    NavigationItem(
                        id="admin_users",
                        label="User Management",
                        path="/admin/users",
                        icon="Users",
                        description="Manage user accounts and roles",
                        requiresAuth=True,
                        roles=["ADMIN", "SUPER_ADMIN"]
                    ),
                    NavigationItem(
                        id="admin_roles",
                        label="Roles & Permissions",
                        path="/admin/roles",
                        icon="Shield",
                        description="Configure roles and permissions",
                        requiresAuth=True,
                        roles=["ADMIN", "SUPER_ADMIN"]
                    ),
                    NavigationItem(
                        id="admin_audit",
                        label="Audit Logs",
                        path="/admin/audit-logs",
                        icon="FileText",
                        description="View system audit logs",
                        requiresAuth=True,
                        roles=["ADMIN", "SUPER_ADMIN"]
                    ),
                ]
            ),
        ],
        "SUPER_ADMIN": [
            # All sections available to super admin
            *[],  # Will include everything
            NavigationSection(
                id="super_admin_system",
                label="System Administration",
                items=[
                    NavigationItem(
                        id="admin_system_health",
                        label="System Health",
                        path="/admin/system-health",
                        icon="Activity",
                        description="Monitor system health and performance",
                        requiresAuth=True,
                        roles=["SUPER_ADMIN"]
                    ),
                    NavigationItem(
                        id="admin_database",
                        label="Database",
                        path="/admin/database",
                        icon="Database",
                        description="Database management and optimization",
                        requiresAuth=True,
                        roles=["SUPER_ADMIN"]
                    ),
                    NavigationItem(
                        id="admin_api_keys",
                        label="API Keys",
                        path="/admin/api-keys",
                        icon="Key",
                        description="Manage API keys and integrations",
                        requiresAuth=True,
                        roles=["SUPER_ADMIN"]
                    ),
                ]
            ),
        ],
    }


def get_navigation_for_user(user: User) -> NavigationResponse:
    structure = get_navigation_structure()
    sections: list[NavigationSection] = []

    # Add staff sections if user can access staff pages
    if can_access_staff_pages(user):
        staff_sections = structure.get("STAFF", [])
        sections.extend(staff_sections)

    # Add admin sections if user can access admin pages
    if can_access_admin_pages(user):
        admin_sections = structure.get("ADMIN", [])
        sections.extend(admin_sections)

    # Add super admin sections if user is super admin
    if is_super_admin(user):
        super_sections = structure.get("SUPER_ADMIN", [])
        sections.extend(super_sections)

    # Filter items within sections based on user role
    filtered_sections = []
    for section in sections:
        filtered_items = [
            item for item in section.items
            if should_include_item(item, user)
        ]
        if filtered_items:
            filtered_sections.append(
                NavigationSection(
                    id=section.id,
                    label=section.label,
                    items=filtered_items
                )
            )

    return NavigationResponse(
        sections=filtered_sections,
        role=str(user.role),
        canAccessAdmin=can_access_admin_pages(user),
        canAccessStaff=can_access_staff_pages(user),
    )


def check_route_access(user: User, required_role: Optional[UserRole] = None) -> bool:
    if required_role is None:
        return True

    user_level = get_role_level(user.role)
    required_level = get_role_level(required_role)

    return user_level >= required_level
