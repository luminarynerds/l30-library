/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Catalog Domain APIs ====================
// APIs for managing catalog, search, cataloging, and recommendations

export * from './catalog-api'
export * from './cataloging-api'
export * from './z3950-cataloging-api'
export * from './recommendations-api'
export * from './linked-data-api'
export * from './lcsh-api'
export * from './unified-search-api'
export * from './gutenberg-api'
export * from './semantic-search-api'
export * from './bibframe-api'

// MetisLib shared ebook catalog
export * from './metislib-api'

// Free ebook sources
export * from './open-library-api'
export * from './free-ebooks-api'
export * from './inventory-api'
export * from './mobile-scanning-api'
export * from './pg-search-api'
export * from './comic-cataloging-api'
export * from './manga-cataloging-api'

// ==================== Conflict Resolutions ====================
// Resolve duplicate exports between catalog API files

// Z3950 types/functions: cataloging-api vs z3950-cataloging-api → prefer cataloging-api
export {
  type Z3950RecordResponse,
  type Z3950SearchParams,
  type Z3950SearchResponse,
  type Z3950SearchResult,
  type Z3950Source,
  type Z3950SourcesResponse,
  getZ3950Sources,
} from './cataloging-api'

// getFormatLabel: unified-search-api vs gutenberg-api → prefer unified-search-api
export { getFormatLabel } from './unified-search-api'

// BibframeInstance, BibframeWork: linked-data-api vs bibframe-api → prefer linked-data-api
export { type BibframeInstance, type BibframeWork } from './linked-data-api'

// UnifiedSearchResponse: unified-search-api vs free-ebooks-api → prefer unified-search-api
export { type UnifiedSearchResponse } from './unified-search-api'

// SearchFacets: catalog-api vs pg-search-api → prefer catalog-api
export { type SearchFacets } from './catalog-api'
