/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface ReleaseBook {
  id: string
  title: string
  subtitle?: string
  author_id: string
  author_name?: string
  release_date: string | null
  is_date_exact: boolean
  isbn_13: string | null
  isbn_10?: string | null
  age_rating: string | null
  cover_url: string | null
  description?: string | null
  publisher?: string | null
  page_count?: number | null
  list_price: number | null
  status: string
  raw_categories?: string[]
  source: string
  source_url?: string | null
  blurb?: string | null
  blurb_credit?: string | null
  is_featured: boolean
}

export interface LibrarianRelease {
  book: ReleaseBook
  author_name: string
  library_status: string
  demand_score: number
  catalog_item_id: number | null
}

export interface LibrarianReleasesResponse {
  items: LibrarianRelease[]
  total: number
  page: number
  per_page: number
}

export type SortField = "release_date" | "demand" | "title" | "price"
export type SortDir = "asc" | "desc"
export type DateRange = "all" | "this_week" | "this_month" | "next_3_months" | "past"

export interface Vendor {
  id: number
  name: string
}

export interface Fund {
  id: number
  name: string
  available_amount: number
}
