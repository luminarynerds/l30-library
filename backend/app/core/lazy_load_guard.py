# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from app.core.logging import get_logger

from sqlalchemy import event
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class AsyncLazyLoadInResponseError(RuntimeError):

    def __init__(self, parent_cls: str, relationship: str):
        self.parent_cls = parent_cls
        self.relationship = relationship
        super().__init__(
            f"Async lazy-load detected on {parent_cls}.{relationship}. "
            f"This will 500 in production (MissingGreenlet). "
            f"Fix: add selectinload({parent_cls}.{relationship}) to the routes "
            f"query options, OR remove the field from the Pydantic response_model."
        )


def install_lazy_load_guard() -> bool:
    from .config import get_settings

    settings = get_settings()
    if settings.environment not in ("development", "test"):
        return False

    if getattr(install_lazy_load_guard, "_installed", False):
        return True

    @event.listens_for(Session, "do_orm_execute")
    def _block_relationship_lazy_load(execute_state):
        if not execute_state.is_select:
            return
        if not execute_state.is_relationship_load:
            return
        # Eager loads (selectinload/joinedload) also fire here; only block
        # implicit lazy-loads, which set lazy_loaded_from on the state.
        if execute_state.lazy_loaded_from is None:
            return
        # loader_strategy_path describes the relationship being loaded.
        path = execute_state.loader_strategy_path
        parent, rel = "<unknown>", "<unknown>"
        try:
            prop = path.prop
            parent = prop.parent.class_.__name__
            rel = prop.key
        except AttributeError:
            if path is not None:
                rel = str(path)
        raise AsyncLazyLoadInResponseError(parent, rel)

    install_lazy_load_guard._installed = True
    logger.warning(
        "AsyncLazyLoad guard ACTIVE (environment=%s). Implicit lazy-loads "
        "will raise. This must NOT be enabled in production.",
        settings.environment,
    )
    return True
