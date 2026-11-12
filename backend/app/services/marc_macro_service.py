# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from app.core.logging import get_logger
import re
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem
from app.models.marc_macro import MarcMacro, MarcMacroVisibility
from app.models.user import User, UserRole
from app.schemas.marc_macro import (
    SUPPORTED_TARGETS,
    MarcMacroCreate,
    MarcMacroStep,
    MarcMacroUpdate,
)

logger = get_logger(__name__)


# Subjects is stored as a comma-joined string; treat as a list for append/clear.
LIST_FIELDS = {"subjects"}
# Numeric columns -- value coerced before assignment.
INT_FIELDS = {"publication_year", "page_count"}


class MarcMacroError(Exception):
    pass


class MarcMacroNotFound(MarcMacroError):
    pass


class MarcMacroForbidden(MarcMacroError):
    pass


class MarcMacroService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ----- CRUD --------------------------------------------------------

    async def list_macros(self, *, user: User) -> tuple[list[MarcMacro], int]:
        query = select(MarcMacro).where(
            (MarcMacro.visibility == MarcMacroVisibility.shared)
            | (
                (MarcMacro.visibility == MarcMacroVisibility.private)
                & (MarcMacro.owner_id == user.id)
            )
        ).order_by(MarcMacro.visibility, MarcMacro.name)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, len(items)

    async def get_macro(self, macro_id: int, *, user: User) -> MarcMacro:
        macro = await self.db.get(MarcMacro, macro_id)
        if macro is None:
            raise MarcMacroNotFound(f"macro {macro_id} not found")
        self._check_read(macro, user)
        return macro

    async def create_macro(self, data: MarcMacroCreate, *, user: User) -> MarcMacro:
        if data.visibility == MarcMacroVisibility.shared:
            self._require_admin(user, action="create shared macro")
        macro = MarcMacro(
            name=data.name,
            description=data.description,
            visibility=data.visibility,
            owner_id=user.id if data.visibility == MarcMacroVisibility.private else None,
            steps=[s.model_dump() for s in data.steps],
        )
        self.db.add(macro)
        await self.db.flush()
        await self.db.refresh(macro)
        return macro

    async def update_macro(
        self, macro_id: int, data: MarcMacroUpdate, *, user: User,
    ) -> MarcMacro:
        macro = await self.get_macro(macro_id, user=user)
        self._check_write(macro, user)

        if data.name is not None:
            macro.name = data.name
        if data.description is not None:
            macro.description = data.description
        if data.steps is not None:
            macro.steps = [s.model_dump() for s in data.steps]
        if data.visibility is not None and data.visibility != macro.visibility:
            # Changing visibility re-checks permissions and updates owner.
            if data.visibility == MarcMacroVisibility.shared:
                self._require_admin(user, action="promote macro to shared")
                macro.owner_id = None
            else:
                macro.owner_id = user.id
            macro.visibility = data.visibility

        await self.db.flush()
        await self.db.refresh(macro)
        return macro

    async def delete_macro(self, macro_id: int, *, user: User) -> None:
        macro = await self.get_macro(macro_id, user=user)
        self._check_write(macro, user)
        await self.db.delete(macro)
        await self.db.flush()

    # ----- Run engine --------------------------------------------------

    async def run_macro(
        self, macro_id: int, catalog_item_ids: list[int], *, user: User,
    ) -> list[dict]:
        macro = await self.get_macro(macro_id, user=user)
        steps = [MarcMacroStep(**s) for s in (macro.steps or [])]

        # Validate every step's target before touching any record so partial
        # runs don't leave the catalog in a half-updated state when the macro
        # itself is malformed.
        for step in steps:
            if step.target() not in SUPPORTED_TARGETS:
                raise MarcMacroError(
                    f"unsupported MARC target {step.target()} in macro {macro_id}"
                )

        result_rows = await self.db.execute(
            select(CatalogItem).where(CatalogItem.id.in_(catalog_item_ids))
        )
        items_by_id = {item.id: item for item in result_rows.scalars().all()}

        results: list[dict] = []
        for item_id in catalog_item_ids:
            item = items_by_id.get(item_id)
            if item is None:
                results.append({
                    "catalog_item_id": item_id,
                    "changed_fields": [],
                    "skipped_steps": [],
                    "error": "catalog item not found",
                })
                continue
            # Snapshot fields the macro touches so we can roll back on error
            targets = [SUPPORTED_TARGETS[s.target()] for s in steps]
            snapshot = {col: getattr(item, col) for col in targets}
            try:
                changed, skipped = self._apply_steps(item, steps)
                results.append({
                    "catalog_item_id": item_id,
                    "changed_fields": sorted(set(changed)),
                    "skipped_steps": skipped,
                    "error": None,
                })
            except Exception as exc:  # noqa: BLE001 - surface to caller
                # Restore snapshot so partial step mutations are not flushed
                for col, val in snapshot.items():
                    setattr(item, col, val)
                logger.warning("macro %s on item %s failed: %s", macro_id, item_id, exc)
                results.append({
                    "catalog_item_id": item_id,
                    "changed_fields": [],
                    "skipped_steps": [],
                    "error": str(exc),
                })

        await self.db.flush()
        return results

    # ----- Internals ---------------------------------------------------

    def _apply_steps(
        self, item: CatalogItem, steps: Iterable[MarcMacroStep],
    ) -> tuple[list[str], list[str]]:
        changed: list[str] = []
        skipped: list[str] = []
        for step in steps:
            column = SUPPORTED_TARGETS[step.target()]
            applied = self._apply_single(item, column, step)
            if applied:
                changed.append(column)
            else:
                skipped.append(f"{step.op} {step.target()}")
        return changed, skipped

    def _apply_single(
        self, item: CatalogItem, column: str, step: MarcMacroStep,
    ) -> bool:
        current = getattr(item, column, None)

        if step.op == "set":
            new_value = self._coerce(column, step.value)
            if new_value == current:
                return False
            setattr(item, column, new_value)
            return True

        if step.op == "clear":
            if current in (None, ""):
                return False
            setattr(item, column, None)
            return True

        if step.op == "find_replace":
            if not step.find or current is None:
                return False
            current_str = str(current)
            replaced = current_str.replace(step.find, step.replace or "")
            if replaced == current_str:
                return False
            setattr(item, column, self._coerce(column, replaced))
            return True

        if step.op == "append":
            if step.value is None or step.value == "":
                return False
            if column in LIST_FIELDS:
                items = self._split_list(current)
                if step.value in items:
                    return False
                items.append(step.value)
                setattr(item, column, ", ".join(items))
                return True
            # For non-list fields, append concatenates with a separating space.
            new_value = f"{current} {step.value}".strip() if current else step.value
            if new_value == current:
                return False
            setattr(item, column, self._coerce(column, new_value))
            return True

        return False

    @staticmethod
    def _split_list(value: str | None) -> list[str]:
        if not value:
            return []
        return [v.strip() for v in re.split(r",\s*", value) if v.strip()]

    _INT_RANGE: dict[str, tuple[int, int]] = {
        "publication_year": (1000, 2100),
        "page_count": (1, 999_999),
    }

    @classmethod
    def _coerce(cls, column: str, value: str | None) -> object | None:
        if value is None:
            return None
        if column in INT_FIELDS:
            match = re.search(r"-?\d+", str(value))
            if match is None:
                return None
            num = int(match.group(0))
            lo, hi = cls._INT_RANGE.get(column, (-(2**31), 2**31 - 1))
            if num < lo or num > hi:
                raise ValueError(
                    f"{column} value {num} outside allowed range {lo}–{hi}"
                )
            return num
        return value

    # ----- Permissions ------------------------------------------------

    @staticmethod
    def _is_admin(user: User) -> bool:
        return user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR)

    @classmethod
    def _check_read(cls, macro: MarcMacro, user: User) -> None:
        if macro.visibility == MarcMacroVisibility.shared:
            return
        if macro.owner_id == user.id or cls._is_admin(user):
            return
        raise MarcMacroForbidden("not allowed to view this macro")

    @classmethod
    def _check_write(cls, macro: MarcMacro, user: User) -> None:
        if macro.visibility == MarcMacroVisibility.shared:
            if not cls._is_admin(user):
                raise MarcMacroForbidden("only admins may edit shared macros")
            return
        if macro.owner_id != user.id and not cls._is_admin(user):
            raise MarcMacroForbidden("not allowed to edit this macro")

    @classmethod
    def _require_admin(cls, user: User, *, action: str) -> None:
        if not cls._is_admin(user):
            raise MarcMacroForbidden(f"admin role required to {action}")
