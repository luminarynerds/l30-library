/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * CatalogItemPage - Re-exports from the refactored catalog module.
 *
 * The implementation has been decomposed into:
 *   hooks/
 *     useItemDetail.ts    – catalog item data fetching
 *     useItemActions.ts   – favorites, lists, and hold management
 *     useItemReviews.ts   – similar items and preference management
 *   components/
 *     ItemOverview.tsx        – cover image, title, badges, status, description, subjects
 *     ItemDetailsTable.tsx    – ISBN, publisher, format, multimedia fields
 *     ItemActions.tsx         – hold/favorite/list/share/TTS action buttons
 *     ItemReviews.tsx         – similar items with settings panel
 *     RelatedItems.tsx        – "similar available now" cards
 *     PlaceHoldModal.tsx      – hold placement modal dialog
 *
 * See frontend/src/pages/catalog/ for the full source.
 */
export { default } from './catalog/CatalogItemPage'
