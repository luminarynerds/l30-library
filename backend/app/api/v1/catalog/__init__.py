# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from fastapi import APIRouter
from . import authority, authority_reconciliation, availability_watch, batch_update, browse, covers, crud, my_activity, search, shelf_notes, images, opds
from .lexile_bulk import router as lexile_bulk_router

router = APIRouter(prefix="/catalog", tags=["catalog"])
# Order matters: crud/search/images/opds/authority/batch_update before browse because
# browse has catch-all /{item_id} routes that would shadow specific paths.
# covers belongs with the other specific-path routers (covers/{item_id}) so it
# is mounted before browse for the same reason.
router.include_router(crud.router)
router.include_router(search.router)
router.include_router(images.router)
router.include_router(covers.router)
router.include_router(opds.router)
router.include_router(authority.router)
router.include_router(authority_reconciliation.router)
router.include_router(batch_update.router)
router.include_router(my_activity.router)
router.include_router(lexile_bulk_router, tags=["catalog-lexile"])
router.include_router(browse.router)
router.include_router(availability_watch.router)
router.include_router(shelf_notes.router)

__all__ = ["router", "authority", "authority_reconciliation", "batch_update", "browse", "covers", "crud", "my_activity", "search", "images", "opds"]
