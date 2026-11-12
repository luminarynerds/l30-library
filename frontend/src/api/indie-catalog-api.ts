/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Indie Catalog API - rewired to owned catalog endpoints (Tier 3)
 * All discovery/detail calls now go through /indie/catalog/* (L30's owned table).
 * MetisLib proxy calls have been removed from discovery, detail, and genre routes.
 */
import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '../utils/tokenStore'

// ==================== Types ====================

export type ContentRating = 'g' | 'pg' | 'pg13' | 't' | 'm' | 'r' | 'nc17' | 'e' | 'e10' | 'ao' | 'explicit' | 'clean' | 'unrated' | 'not_rated' | 'general' | 'teen' | 'mature'
export type BorrowStatus = 'active' | 'returned' | 'expired'

export interface IndieEbookPublic {
  id: number
  /** L30 IndieEbook PK; drives the indie lending endpoints (borrow/reader/review). */
  indie_ebook_id?: number
  title: string
  description: string
  cover_url: string | null
  genre: string | null
  subjects: string[]
  language: string
  word_count: number | null
  publication_year?: number | null
  content_rating: ContentRating
  content_warnings: string[]
  author_id: number
  author_pen_name: string
  available_copies: number
  total_copies: number
  borrow_duration_days: number
  average_rating: number | null
  rating_count: number
  total_borrows: number
  is_preorder?: boolean
  preorder_release_date?: string | null
  hold_count?: number
  demand_level?: 'none' | 'growing' | 'high' | 'card_available'
  demand_progress?: number
  catalog_item_id?: number | null
}

export interface PreorderPublic {
  ebook_id: number
  title: string
  author_pen_name: string
  cover_url: string | null
  description: string
  genre: string | null
  release_date: string | null
  hold_count: number
  content_rating: ContentRating
  is_preorder: boolean
}

export interface PreorderHoldResponse {
  hold_id: number
  ebook_id: number
  title: string
  position: number
  release_date: string | null
  message: string
}

export interface EbookBorrow {
  id: number
  ebook_id: number
  /** L30 IndieEbook PK; the reader/progress key (distinct from the MetisLib ebook_id used for slugs). */
  indie_ebook_id?: number
  ebook_title: string
  ebook_cover_url: string | null
  author_pen_name: string
  borrowed_at: string
  due_at: string
  status: BorrowStatus
  download_count: number
  max_downloads: number
  renewal_count: number
  can_renew: boolean
}

export interface HistoryBorrow {
  id: number
  ebook_id: number
  ebook_title: string
  ebook_cover_url: string | null
  author_pen_name: string
  borrowed_at: string
  returned_at: string | null
  due_at: string
  status: BorrowStatus
  rating: number | null
}

export interface PaginatedHistory {
  items: HistoryBorrow[]
  total: number
  page: number
  per_page: number
}

export interface BorrowResponse {
  id: number
  ebook_id: number
  ebook_title: string
  borrowed_at: string
  due_at: string
  access_token: string
  download_url: string
  status: BorrowStatus
}

export interface WaitlistResponse {
  ebook_id: number
  ebook_title: string
  position: number
  estimated_wait_days: number | null
  created_at: string
}

export interface BookDetailPublic {
  id: number
  /** L30 IndieEbook PK; drives the indie lending endpoints (borrow/reader/review). */
  indie_ebook_id?: number
  slug: string
  title: string
  description: string
  cover_url: string | null
  genre: string | null
  subjects: string[]
  language: string
  word_count: number | null
  isbn: string | null
  publication_year: number | null
  content_rating: ContentRating
  content_warnings: string[]
  author_id: number
  author_pen_name: string
  author_bio: string | null
  author_profile_image: string | null
  author_verified: boolean
  purchase_url: string | null
  available_copies: number
  total_copies: number
  borrow_duration_days: number
  average_rating: number | null
  rating_count: number
  total_borrows: number
  created_at: string
  page_count: number | null
}

export interface AuthorProfilePublic {
  id: number
  slug: string
  pen_name: string
  bio: string | null
  profile_image_url: string | null
  website_url: string | null
  goodreads_url: string | null
  amazon_author_url: string | null
  verified: boolean
  approved_books: number
  total_borrows: number
  follower_count: number
  joined_at: string
}

export interface BookCard {
  id: number
  slug: string
  title: string
  description: string
  cover_url: string | null
  genre: string | null
  content_rating: ContentRating
  author_id: number
  author_pen_name: string
  available_copies: number
  total_copies: number
  average_rating: number | null
  rating_count: number
  total_borrows: number
  publication_year?: number | null
}

export interface DiscoveryPageData {
  featured: BookCard[]
  trending: BookCard[]
  new_arrivals: BookCard[]
  staff_picks: BookCard[]
  popular_genres: { name: string; count: number }[]
  total_books: number
  total_authors: number
}

export interface GenrePageData {
  genre: string
  description: string | null
  books: BookCard[]
  total: number
  page: number
  per_page: number
  pages: number
  related_genres: string[]
}

export interface CollectionData {
  id: string
  slug: string
  title: string
  description: string | null
  cover_url: string | null
  curator_name: string
  book_count: number
  books: BookCard[]
  created_at: string
}

export interface PublicReview {
  id: number
  rating: number
  review_text: string | null
  reviewer_name: string
  created_at: string
}

export interface GenreInfo {
  name: string
  slug: string
  count: number
  description: string | null
}

export interface CollectionSummary {
  id: string
  slug: string
  title: string
  description: string | null
  book_count: number
}

export interface AuthorBriefResponse {
  id: number
  pen_name: string
  bio?: string
  profile_image_url?: string
  approved_books: number
  total_borrows: number
  trust_level: number
}

export interface StaffAuthorListItemResponse {
  id: number
  author_id: number
  author: AuthorBriefResponse
  staff_note?: string
  display_order: number
  added_at: string
}

export interface StaffAuthorListDetailResponse {
  id: number
  title: string
  description?: string
  slug: string
  is_active: boolean
  display_order: number
  items_count: number
  items: StaffAuthorListItemResponse[]
  created_at?: string
}

// ==================== Owned Catalog Types ====================

interface OwnedCatalogItem {
  id: number
  title: string
  author_pen_name: string
  description: string | null
  cover_url: string | null
  genre: string | null
  language: string
  content_warnings: string[]
  available_copies: number
  total_copies: number
  publication_year: number | null
}

interface IndieCatalogDetail {
  id: number
  title: string
  author_pen_name: string
  description: string | null
  cover_url: string | null
  genre: string | null
  language: string
  content_warnings: string[]
  available_copies: number
  total_copies: number
  publication_year: number | null
  subjects: string[]
  word_count: number | null
  page_count: number | null
  isbn: string | null
  content_rating: string
  author_id: number | null
  average_rating: number | null
  rating_count: number
  total_borrows: number
}

function ownedToBookCard(item: OwnedCatalogItem): BookCard {
  return {
    id: item.id,
    slug: generateSlug(item.title, item.id),
    title: item.title,
    description: item.description ?? '',
    cover_url: item.cover_url,
    genre: item.genre,
    content_rating: 'unrated' as ContentRating,
    author_id: 0,
    author_pen_name: item.author_pen_name,
    available_copies: item.available_copies,
    total_copies: item.total_copies,
    average_rating: null,
    rating_count: 0,
    total_borrows: 0,
  }
}

// ==================== Public Catalog ====================

export async function browseIndieCatalog(params: {
  q?: string
  genre?: string
  content_rating?: ContentRating
  author_id?: number
  sort?: string
  page?: number
  per_page?: number
  author?: string
  author_slug?: string
  exclude_warnings?: string[]
}): Promise<{ items: IndieEbookPublic[]; total: number; page: number; per_page: number; pages: number }> {
  // Phase 2: serve from L30's owned indie_ebooks table, not the MetisLib proxy.
  // The id in every item is the L30 IndieEbook PK -- the value that borrow/waitlist/reader
  // endpoints all expect as ebook_id. Do NOT use metislib_ebook_id here; they collide ~1:1
  // with open-access catalog ids and caused the prior Borrow bug.
  //
  // The detail page now has author_id and content_rating via GET /indie/catalog/{id}.
  const searchParams = new URLSearchParams()
  if (params.q) searchParams.append('q', params.q)
  if (params.genre) searchParams.append('genre', params.genre)
  if (params.sort) searchParams.append('sort', params.sort)
  if (params.page) searchParams.append('page', params.page.toString())
  if (params.per_page) searchParams.append('per_page', params.per_page.toString())
  if (params.author) searchParams.append('author', params.author)
  if (params.author_slug) searchParams.append('author_slug', params.author_slug)
  // author_id and content_rating filters not yet supported by the owned catalog endpoint
  const qs = searchParams.toString()
  type OwnedCatalogPage = {
    items: OwnedCatalogItem[]
    total: number
    page: number
    per_page: number
    pages: number
  }
  const raw = await fetchApi<OwnedCatalogPage>(`/indie/catalog${qs ? `?${qs}` : ''}`)
  const items: IndieEbookPublic[] = raw.items.map((item) => ({
    id: item.id,
    indie_ebook_id: item.id,
    title: item.title,
    description: item.description ?? '',
    cover_url: item.cover_url,
    genre: item.genre,
    subjects: [],
    language: item.language,
    word_count: null,
    publication_year: item.publication_year,
    content_rating: 'unrated' as ContentRating,
    content_warnings: item.content_warnings,
    author_id: 0,
    author_pen_name: item.author_pen_name,
    available_copies: item.available_copies,
    total_copies: item.total_copies,
    borrow_duration_days: 21,
    average_rating: null,
    rating_count: 0,
    total_borrows: 0,
    is_preorder: false,
  }))
  return { items, total: raw.total, page: raw.page, per_page: raw.per_page, pages: raw.pages }
}

// ==================== Lending ====================

export async function borrowEbook(ebookId: number): Promise<BorrowResponse> {
  // ebookId is the L30 IndieEbook PK. Borrow through the indie lending system
  // (creates the indie_ebook_borrows row + notifies MetisLib via borrow_indie),
  // NOT the generic shared-catalog checkout -- that can't resolve indie ids and
  // hands back the colliding open-access (Gutenberg) title.
  const token = getAccessToken()
  return fetchApi<BorrowResponse>(`/indie/lending/borrow`, {
    method: 'POST',
    ...(token ? { token } : {}),
    body: { ebook_id: ebookId },
  })
}

export async function borrowEbookByCatalogItem(catalogItemId: number): Promise<BorrowResponse> {
  return borrowEbook(catalogItemId)
}

export async function getActiveBorrows(): Promise<EbookBorrow[]> {
  const token = getAccessToken()
  const result = await fetchApi<EbookBorrow[] | { items: EbookBorrow[] }>('/indie/lending/borrows/active', {
    ...(token ? { token } : {}),
  })
  return Array.isArray(result) ? result : result.items || []
}

export async function getBorrowHistory(page: number = 1, perPage: number = 20): Promise<PaginatedHistory> {
  const token = getAccessToken()
  return fetchApi<PaginatedHistory>(`/indie/lending/borrows/history?page=${page}&per_page=${perPage}`, {
    ...(token ? { token } : {}),
  })
}

export async function returnEbook(borrowId: number, rating?: number, reviewText?: string): Promise<EbookBorrow> {
  const token = getAccessToken()
  const body: Record<string, unknown> = {}
  if (rating !== undefined) body.rating = rating
  if (reviewText !== undefined) body.review_text = reviewText
  return fetchApi<EbookBorrow>(`/indie/lending/borrows/${borrowId}/return`, {
    method: 'POST',
    ...(token ? { token } : {}),
    body,
  })
}



export async function joinWaitlist(ebookId: number): Promise<WaitlistResponse> {
  // Owned waitlist, keyed on the local IndieEbook id the catalog serves.
  // The old /ebooks/{id}/hold route reads ids in the MetisLib id space, which
  // collides with local ids and could waitlist the wrong title.
  const token = getAccessToken()
  return fetchApi<WaitlistResponse>(`/indie/lending/waitlist/${ebookId}`, {
    method: 'POST',
    ...(token ? { token } : {}),
  })
}

// ==================== Public Discovery ====================

export async function getIndieCatalogRails(): Promise<{ featured: OwnedCatalogItem[]; popular: OwnedCatalogItem[]; new: OwnedCatalogItem[] }> {
  return fetchApi<{ featured: OwnedCatalogItem[]; popular: OwnedCatalogItem[]; new: OwnedCatalogItem[] }>('/indie/catalog/rails?limit=12')
}

export async function getIndieCatalogGenres(): Promise<{ genre: string; count: number }[]> {
  return fetchApi<{ genre: string; count: number }[]>('/indie/catalog/genres')
}

export async function getPublicBookDetail(slugOrId: string): Promise<BookDetailPublic> {
  const id = extractIdFromSlug(slugOrId)
  const detail = await fetchApi<IndieCatalogDetail>(`/indie/catalog/${id}`)
  return {
    id: detail.id,
    indie_ebook_id: detail.id,
    slug: generateSlug(detail.title, detail.id),
    title: detail.title,
    description: detail.description ?? '',
    cover_url: detail.cover_url,
    genre: detail.genre,
    subjects: detail.subjects,
    language: detail.language,
    word_count: detail.word_count,
    isbn: detail.isbn,
    publication_year: detail.publication_year,
    content_rating: detail.content_rating as ContentRating,
    content_warnings: detail.content_warnings,
    // author_id stays 0 so IndieBookDetailPage renders a plain name, not a link
    author_id: 0,
    author_pen_name: detail.author_pen_name,
    author_bio: null,
    author_profile_image: null,
    author_verified: false,
    purchase_url: null,
    available_copies: detail.available_copies,
    total_copies: detail.total_copies,
    borrow_duration_days: 21,
    average_rating: detail.average_rating,
    rating_count: detail.rating_count,
    total_borrows: detail.total_borrows,
    created_at: '',
    page_count: detail.page_count,
  }
}

export async function getPublicBookReviews(slugOrId: string, _page: number = 1): Promise<PublicReview[]> {
  const id = extractIdFromSlug(slugOrId)
  try {
    return await fetchApi<PublicReview[]>(`/indie/lending/ebooks/${id}/reviews`)
  } catch {
    return []
  }
}

export interface UserBorrowStatus {
  id: number
  ebook_id: number
  status: BorrowStatus
  rating: number | null
  review_text: string | null
  review_submitted_at: string | null
}

export async function getUserBorrowForEbook(ebookId: number): Promise<UserBorrowStatus | null> {
  const token = getAccessToken()
  try {
    return await fetchApi<UserBorrowStatus>(`/indie/lending/borrows/by-ebook/${ebookId}`, {
      ...(token ? { token } : {}),
    })
  } catch {
    return null
  }
}

export async function submitReview(borrowId: number, rating?: number, reviewText?: string): Promise<UserBorrowStatus> {
  const token = getAccessToken()
  const body: Record<string, unknown> = {}
  if (rating !== undefined) body.rating = rating
  if (reviewText !== undefined) body.review_text = reviewText
  return fetchApi<UserBorrowStatus>(`/indie/lending/borrows/${borrowId}/review`, {
    method: 'POST',
    ...(token ? { token } : {}),
    body,
  })
}

export async function getPublicBookRecommendations(_slugOrId: string, _limit: number = 6): Promise<BookCard[]> {
  return []
}

export interface IndieAuthorProfile {
  pen_name: string
  bio: string | null
  profile_image_url: string | null
}

export async function getPublicAuthorDetail(slug: string): Promise<IndieAuthorProfile | null> {
  if (!slug) return null
  try {
    return await fetchApi<IndieAuthorProfile | null>(
      `/indie/catalog/author/profile?slug=${encodeURIComponent(slug)}`,
    )
  } catch {
    return null
  }
}

export async function getPublicAuthorBooks(slug: string, page: number = 1): Promise<BookCard[]> {
  if (!slug) return []
  const result = await browseIndieCatalog({ author_slug: slug, page })
  return result.items.map((item) => ({
    id: item.id,
    slug: generateSlug(item.title, item.id),
    title: item.title,
    description: item.description,
    cover_url: item.cover_url,
    genre: item.genre,
    content_rating: item.content_rating,
    author_id: item.author_id,
    author_pen_name: item.author_pen_name,
    available_copies: item.available_copies,
    total_copies: item.total_copies,
    average_rating: item.average_rating,
    rating_count: item.rating_count,
    total_borrows: item.total_borrows,
    publication_year: item.publication_year ?? null,
  }))
}

export async function getDiscoveryPage(): Promise<DiscoveryPageData> {
  const [rails, genres, staffPicks] = await Promise.allSettled([
    getIndieCatalogRails(),
    getIndieCatalogGenres(),
    fetchApi<OwnedCatalogItem[]>('/indie/catalog/staff-picks'),
  ])

  const railsData = rails.status === 'fulfilled'
    ? rails.value
    : { featured: [], popular: [], new: [] }

  const genreList = genres.status === 'fulfilled'
    ? (Array.isArray(genres.value) ? genres.value : [])
    : []

  const featured = railsData.featured.map(ownedToBookCard)
  const popular = railsData.popular.map(ownedToBookCard)
  const newArrivals = railsData.new.map(ownedToBookCard)

  const authorSet = new Set<string>()
  for (const item of [...railsData.featured, ...railsData.popular, ...railsData.new]) {
    if (item.author_pen_name) authorSet.add(item.author_pen_name)
  }

  const staffPicksList =
    staffPicks.status === 'fulfilled' && Array.isArray(staffPicks.value)
      ? staffPicks.value.map(ownedToBookCard)
      : []

  return {
    featured,
    trending: popular,
    new_arrivals: newArrivals,
    staff_picks: staffPicksList,
    popular_genres: genreList.map((g) => ({ name: g.genre, count: g.count })),
    total_books: 0,
    total_authors: authorSet.size,
  }
}

export async function getGenrePage(genre: string, params?: {
  page?: number
  per_page?: number
  sort?: 'popular' | 'new' | 'rating'
}): Promise<GenrePageData> {
  const result = await browseIndieCatalog({
    genre,
    ...(params?.page != null ? { page: params.page } : {}),
    ...(params?.per_page != null ? { per_page: params.per_page } : {}),
  })
  return {
    genre,
    description: null,
    books: result.items as unknown as BookCard[],
    total: result.total,
    page: result.page,
    per_page: result.per_page,
    pages: result.pages,
    related_genres: [],
  }
}

export async function getGenreList(): Promise<GenreInfo[]> {
  try {
    const result = await getIndieCatalogGenres()
    return Array.isArray(result)
      ? result.map((g) => ({ name: g.genre, slug: g.genre.toLowerCase().replace(/\s+/g, '-'), count: g.count, description: null }))
      : []
  } catch {
    return []
  }
}

type OwnedCollection = {
  id: number
  title: string
  description: string | null
  items: OwnedCatalogItem[]
}

export async function getCollectionList(): Promise<CollectionSummary[]> {
  try {
    // Owned-table collections; items carry local IndieEbook ids.
    const result = await fetchApi<OwnedCollection[]>('/indie/catalog/collections')
    return (result || []).map((c) => ({
      id: String(c.id),
      slug: c.title.toLowerCase().replace(/\s+/g, '-'),
      title: c.title,
      description: c.description,
      book_count: c.items?.length || 0,
    }))
  } catch {
    return []
  }
}

export async function getCollection(slug: string, _page: number = 1): Promise<CollectionData> {
  const result = await fetchApi<OwnedCollection[]>('/indie/catalog/collections')
  const match = result?.find(c => String(c.id) === slug || c.title.toLowerCase().replace(/\s+/g, '-') === slug)
  if (!match) throw new Error('Collection not found')
  const books = (match.items || []).map(ownedToBookCard)
  return {
    id: String(match.id),
    slug: match.title.toLowerCase().replace(/\s+/g, '-'),
    title: match.title,
    description: match.description,
    cover_url: null,
    curator_name: 'Library Staff',
    book_count: books.length,
    books,
    created_at: '',
  }
}

export function getBookEmbedUrl(bookId: number, theme: 'light' | 'dark' = 'light'): string {
  return `/indie/public/embed/book/${bookId}?theme=${theme}`
}

export function getAuthorEmbedUrl(authorId: number, theme: 'light' | 'dark' = 'light'): string {
  return `/indie/public/embed/author/${authorId}?theme=${theme}`
}

export function getRssFeedUrl(genre?: string): string {
  return genre ? `/indie/public/feed.rss?genre=${encodeURIComponent(genre)}` : '/indie/public/feed.rss'
}

export function penNameToSlug(penName: string | null | undefined): string {
  return (penName ?? '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
}

export function generateSlug(title: string | null | undefined, id: number): string {
  const safeTitle = typeof title === 'string' ? title : ''
  const slug = safeTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50)
  return `${slug || 'item'}-${id}`
}

// ==================== Author Lists & Preorders ====================

export async function getPublicAuthorLists(): Promise<StaffAuthorListDetailResponse[]> {
  return []
}

export async function getPreorderEbooks(): Promise<PreorderPublic[]> {
  return []
}

export async function placePreorderHold(_ebookId: number, _pickupLocationId?: number): Promise<PreorderHoldResponse> {
  throw new Error('Preorders are no longer available')
}

// ==================== Patron & Holds ====================

export type PatronType = 'resident_cardholder' | 'out_of_county_subscriber' | 'authenticated_visitor' | 'anonymous'

export interface PatronTypeInfo {
  patron_type: PatronType
  is_resident: boolean | null
}

export interface BuyNowStatus {
  show_buy_now: boolean
  price: number
  active_holds: number
  total_copies: number
  demand_level: string
  demand_progress: number
}

export async function placeIndieHold(catalogItemId: number): Promise<{ message: string; item_id: number }> {
  const token = getAccessToken()
  return fetchApi<{ message: string; item_id: number }>('/circulation/holds', {
    method: 'POST',
    ...(token ? { token } : {}),
    body: { item_id: catalogItemId },
  })
}

export async function getPatronType(): Promise<PatronTypeInfo> {
  return { patron_type: 'anonymous' as PatronType, is_resident: null }
}

export async function getBuyNowStatus(_ebookId: number): Promise<BuyNowStatus> {
  return { show_buy_now: false, price: 0, active_holds: 0, total_copies: 0, demand_level: 'none', demand_progress: 0 }
}

export async function purchaseDigitalAccess(
  _ebookId: number,
  _utmSource?: string,
  _utmMedium?: string,
  _utmCampaign?: string,
): Promise<{
  order_number: string
  card_number: string | null
  collectible_card_serial: string | null
  amount: number
  status: string
}> {
  throw new Error('Digital access purchases are no longer available')
}

// ======================= Recommendations ========================

export interface IndieRecommendation {
  ebook_id: number
  title: string
  author_pen_name: string
  cover_url: string | null
  genre: string | null
  average_rating: number | null
  score: number
  reason: string
}

export interface IndieRecommendationsResponse {
  items: IndieRecommendation[]
  algorithm: string
}

export async function getIndieRecommendations(ebookId: number, limit = 6): Promise<IndieRecommendationsResponse> {
  return fetchApi<IndieRecommendationsResponse>(`/indie/books/${ebookId}/recommendations?limit=${limit}`)
}


// ==================== Helpers ====================
function extractIdFromSlug(slugOrId: string): string {
  if (/^\d+$/.test(slugOrId)) return slugOrId
  const match = slugOrId.match(/-(\d+)$/)
  return match && match[1] ? match[1] : slugOrId
}

// ==================== Preview ====================

export interface EbookPreview {
  ebook_id: number
  title: string
  author_name: string
  preview_html: string
  preview_pct: number
}

export async function getEbookPreview(ebookId: number): Promise<EbookPreview> {
  return fetchApi<EbookPreview>(`/indie/lending/preview/${ebookId}`)
}

// ==================== Author Spotlight ====================

export interface FeaturedAuthorResponse {
  id: number
  pen_name: string
  bio: string
  profile_image_url: string | null
  book_count: number
}

export async function getFeaturedAuthor(): Promise<FeaturedAuthorResponse> {
  return fetchApi<FeaturedAuthorResponse>("/ebooks/featured-author")
}

export interface JustAvailableEbook {
  ebook_id: number
  title: string
  author_pen_name: string
  cover_url: string | null
  description: string | null
  genre: string | null
  returned_at: string
  available_copies: number
}

export async function getJustAvailableEbooks(limit = 8, days = 7): Promise<JustAvailableEbook[]> {
  return fetchApi<JustAvailableEbook[]>(`/indie/lending/just-available?limit=${limit}&days=${days}`)
}

export interface UpcomingIndieEvent {
  id: number
  title: string
  start_time: string
  end_time: string | null
  category: string | null
  author_id: number | null
  author_pen_name: string | null
}

export async function getUpcomingIndieEvents(limit = 5): Promise<UpcomingIndieEvent[]> {
  return fetchApi<UpcomingIndieEvent[]>(`/indie/authors/events/upcoming?limit=${limit}`)
}

export interface PublicReadingList {
  id: number
  name: string
  description: string | null
  is_public: boolean
  share_token: string | null
  item_count: number
  created_at: string
  updated_at: string
}

export async function getPublicReadingLists(limit = 6): Promise<PublicReadingList[]> {
  return fetchApi<PublicReadingList[]>(`/indie/reading-lists/public?limit=${limit}`)
}
