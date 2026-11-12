/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { type CatalogItem } from '@/api/api'
import { type UnifiedSearchResult } from '@/api/domains/catalog/unified-search-api'

export type CatalogDisplayItem = CatalogItem & { source?: string }

export function toDisplayItem(r: UnifiedSearchResult): CatalogDisplayItem {
  return {
    id: r.source === 'indie'
      ? (parseInt(r.source_id.replace(/^indie:/, ''), 10) || Number(r.source_id) || 0)
      : (Number(r.source_id) || 0),
    title: r.title,
    author: r.author,
    item_type: r.format as CatalogItem['item_type'],
    status: r.is_available ? 'available' : 'checked_out',
    available_for_hold: r.is_available !== false,
    isbn: r.isbn,
    publisher: r.publisher,
    publication_year: r.publication_year,
    description: r.description,
    subjects: r.subjects?.join(', ') || null,
    cover_url: r.cover_url,
    page_count: null,
    location: null,
    barcode: null,
    created_at: '',
    updated_at: null,
    is_large_print: false,
    images: [],
    series_name: null,
    series_number: null,
    series_position: null,
    call_number: null,
    dewey_decimal: null,
    total_checkouts: 0,
    director: null,
    actors: null,
    runtime_minutes: null,
    media_format: null,
    content_rating: null,
    disc_count: null,
    studio: null,
    artist: null,
    track_count: null,
    music_genre: null,
    platform: null,
    player_count: null,
    game_genre: null,
    brand: null,
    model_number: null,
    dimensions: null,
    material: null,
    kit_contents: null,
    source: r.source,
  }
}
