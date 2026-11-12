/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Linked Data API Service
 *
 * Provides access to BIBFRAME entities and RDF serialization endpoints.
 * Supports content negotiation for JSON-LD and Turtle formats.
 */

import { fetchApi } from '@/lib/api-client'
import { API_BASE } from '@/api/types'

// ==================== BIBFRAME Types ====================

export type WorkType =
  | 'text'
  | 'spoken_word'
  | 'performed_music'
  | 'notated_music'
  | 'still_image'
  | 'two_dimensional_moving_image'
  | 'cartographic_image'
  | 'computer_program'
  | 'computer_dataset'
  | 'other'

export type InstanceType =
  | 'print'
  | 'electronic'
  | 'audio'
  | 'audiovisual'
  | 'tactile'
  | 'microform'
  | 'manuscript'
  | 'archive'

export type CarrierType =
  | 'volume'
  | 'audio_disc'
  | 'computer_disc'
  | 'online_resource'
  | 'videodisc'
  | 'audiocassette'
  | 'videocassette'
  | 'other'

export type MediaType =
  | 'unmediated'
  | 'computer'
  | 'audio'
  | 'video'
  | 'microform'

export type AuthoritySource =
  | 'viaf'
  | 'lcnaf'
  | 'lccn'
  | 'lcsh'
  | 'fast'
  | 'wikidata'
  | 'isni'
  | 'orcid'
  | 'gnd'
  | 'isbn'
  | 'issn'
  | 'doi'
  | 'oclc'

// ==================== Entity Interfaces ====================

export interface BibframeContributor {
  id: number
  uri?: string
  name: string
  contributor_type: 'person' | 'organization' | 'meeting'
  name_inverted?: string
  given_name?: string
  family_name?: string
  birth_date?: string
  death_date?: string
  viaf_id?: string
  lcnaf_id?: string
  wikidata_id?: string
  orcid?: string
  isni?: string
  biography?: string
  created_at: string
  updated_at?: string
}

export interface BibframeSubject {
  id: number
  uri?: string
  label: string
  subject_type: 'topic' | 'place' | 'temporal' | 'person' | 'organization'
  lcsh_id?: string
  fast_id?: string
  wikidata_id?: string
  broader_term?: string
  narrower_terms?: string[]
  related_terms?: string[]
  scope_note?: string
  created_at: string
}

export interface BibframeWork {
  id: number
  uri?: string
  title: string
  subtitle?: string
  title_sort?: string
  title_variant?: string[]
  work_type: WorkType
  language?: string
  original_language?: string
  summary?: string
  table_of_contents?: string
  genre_form?: string[]
  intended_audience?: string
  dewey_classification?: string
  lc_classification?: string
  series_title?: string
  series_number?: string
  origin_date?: string
  origin_place?: string
  notes?: string[]
  source?: string
  source_record_id?: string
  catalog_item_id?: number
  contributors?: ContributorBrief[]
  subjects?: SubjectBrief[]
  instance_count?: number
  linked_data?: Record<string, unknown>
  created_at: string
  updated_at?: string
}

export interface BibframeInstance {
  id: number
  work_id: number
  uri?: string
  title: string
  subtitle?: string
  title_statement?: string
  instance_type: InstanceType
  carrier_type: CarrierType
  media_type: MediaType
  isbn_10?: string
  isbn_13?: string
  issn?: string
  lccn?: string
  oclc_number?: string
  publisher?: string
  publisher_place?: string
  publication_date?: string
  publication_year?: number
  copyright_date?: string
  edition?: string
  edition_number?: number
  extent?: string
  dimensions?: string
  page_count?: number
  digital_format?: string
  file_size?: string
  access_url?: string
  cover_url?: string
  thumbnail_url?: string
  notes?: string[]
  work?: WorkBrief
  contributors?: ContributorBrief[]
  item_count?: number
  source?: string
  linked_data?: Record<string, unknown>
  created_at: string
  updated_at?: string
}

export interface BibframeItem {
  id: number
  instance_id: number
  uri?: string
  barcode?: string
  accession_number?: string
  copy_number: number
  call_number?: string
  shelving_location?: string
  sublocation?: string
  library_branch: string
  collection?: string
  circulation_status: string
  is_holdable: boolean
  is_loanable: boolean
  condition: string
  condition_notes?: string
  acquisition_date?: string
  acquisition_source?: string
  acquisition_price?: number
  fund_code?: string
  electronic_locator?: string
  access_restrictions?: string
  public_note?: string
  staff_note?: string
  instance?: InstanceBrief
  created_at: string
  updated_at?: string
}

export interface AuthorityLink {
  id: number
  source: AuthoritySource
  authority_id: string
  authority_uri?: string
  authority_label?: string
  link_type: string
  confidence?: number
  verified: boolean
  verified_by_id?: number
  verified_at?: string
  work_id?: number
  instance_id?: number
  item_id?: number
  contributor_id?: number
  subject_id?: number
  cached_data?: Record<string, unknown>
  created_at: string
}

// Brief versions for embedding
export interface ContributorBrief {
  id: number
  name: string
  contributor_type: string
  viaf_id?: string
}

export interface SubjectBrief {
  id: number
  label: string
  subject_type: string
  lcsh_id?: string
}

export interface WorkBrief {
  id: number
  title: string
  work_type: WorkType
  language?: string
}

export interface InstanceBrief {
  id: number
  title: string
  isbn_13?: string
  publisher?: string
  publication_year?: number
}

// ==================== Request/Response Types ====================

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface WorkSearchParams {
  q?: string
  title?: string
  contributor?: string
  subject?: string
  language?: string
  work_type?: WorkType
  page?: number
  per_page?: number
}

export interface InstanceSearchParams {
  q?: string
  isbn?: string
  publisher?: string
  year_from?: number
  year_to?: number
  work_id?: number
  page?: number
  per_page?: number
}

export interface ItemSearchParams {
  barcode?: string
  call_number?: string
  branch?: string
  status?: string
  instance_id?: number
  page?: number
  per_page?: number
}

export interface WorkCreate {
  title: string
  subtitle?: string
  work_type?: WorkType
  language?: string
  summary?: string
  genre_form?: string[]
  dewey_classification?: string
  lc_classification?: string
  series_title?: string
  series_number?: string
  contributor_ids?: number[]
  subject_ids?: number[]
}

export interface InstanceCreate {
  work_id: number
  title: string
  subtitle?: string
  instance_type?: InstanceType
  carrier_type?: CarrierType
  media_type?: MediaType
  isbn_13?: string
  publisher?: string
  publisher_place?: string
  publication_year?: number
  edition?: string
  page_count?: number
  cover_url?: string
}

export interface ItemCreate {
  instance_id: number
  barcode?: string
  call_number?: string
  shelving_location?: string
  library_branch?: string
  collection?: string
  condition?: string
}

// LC Import types
export interface LocSearchResult {
  uri: string
  title: string
  contributors: string[]
  publication_info?: string
  identifiers: Record<string, string>
  work_type?: string
}

export interface LocSearchResponse {
  results: LocSearchResult[]
  total_results: number
  query: string
}

export interface LocImportResult {
  work: { id: number; uri: string; title: string }
  instances: Array<{ id: number; title: string; isbn?: string }>
  contributors_count: number
  subjects_count: number
  warnings: string[]
}

// MARC conversion types
export interface MarcConversionResult {
  work?: BibframeWork
  instance?: BibframeInstance
  contributors?: BibframeContributor[]
  subjects?: BibframeSubject[]
  warnings: string[]
}

// SPARQL types
export interface SparqlBinding {
  type: 'uri' | 'literal' | 'bnode'
  value: string
  datatype?: string
  'xml:lang'?: string
}

export interface SparqlResults {
  head: { vars: string[] }
  results: { bindings: Array<Record<string, SparqlBinding>> }
  error?: string
}

// Schema.org type (for SEO)
export interface SchemaOrgMarkup {
  '@context': string
  '@type': string
  '@id': string
  name: string
  [key: string]: unknown
}

// ==================== API Functions ====================

const BASE_PATH = '/linked-data'

// --- Works ---

export async function getWorks(
  params: WorkSearchParams = {},
  token?: string
): Promise<PaginatedResponse<BibframeWork>> {
  const searchParams = new URLSearchParams()
  if (params.q) searchParams.set('q', params.q)
  if (params.title) searchParams.set('title', params.title)
  if (params.contributor) searchParams.set('contributor', params.contributor)
  if (params.subject) searchParams.set('subject', params.subject)
  if (params.language) searchParams.set('language', params.language)
  if (params.work_type) searchParams.set('work_type', params.work_type)
  searchParams.set('page', String(params.page || 1))
  searchParams.set('per_page', String(params.per_page || 20))

  return fetchApi<PaginatedResponse<BibframeWork>>(
    `${BASE_PATH}/works?${searchParams}`,
    token ? { token } : {}
  )
}

export async function getWork(
  id: number,
  options: { includeInstances?: boolean; includeAuthorities?: boolean } = {},
  token?: string
): Promise<BibframeWork> {
  const params = new URLSearchParams()
  if (options.includeInstances !== undefined) {
    params.set('include_instances', String(options.includeInstances))
  }
  if (options.includeAuthorities !== undefined) {
    params.set('include_authorities', String(options.includeAuthorities))
  }

  return fetchApi<BibframeWork>(`${BASE_PATH}/works/${id}?${params}`, token ? { token } : {})
}

export async function getWorkJsonLd(id: number): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}${BASE_PATH}/works/${id}`, {
    headers: { Accept: 'application/ld+json' },
  })
  if (!response.ok) throw new Error('Failed to fetch JSON-LD')
  return response.json()
}

export async function getWorkTurtle(id: number): Promise<string> {
  const response = await fetch(`${API_BASE}${BASE_PATH}/works/${id}`, {
    headers: { Accept: 'text/turtle' },
  })
  if (!response.ok) throw new Error('Failed to fetch Turtle')
  return response.text()
}

export async function createWork(
  data: WorkCreate,
  token: string
): Promise<BibframeWork> {
  return fetchApi<BibframeWork>(`${BASE_PATH}/works`, {
    method: 'POST',
    body: data,
    token,
  })
}

export async function updateWork(
  id: number,
  data: Partial<WorkCreate>,
  token: string
): Promise<BibframeWork> {
  return fetchApi<BibframeWork>(`${BASE_PATH}/works/${id}`, {
    method: 'PATCH',
    body: data,
    token,
  })
}

export async function deleteWork(id: number, token: string): Promise<void> {
  return fetchApi(`${BASE_PATH}/works/${id}`, {
    method: 'DELETE',
    token,
    skipJsonParse: true,
  })
}

// --- Instances ---

export async function getInstances(
  params: InstanceSearchParams = {},
  token?: string
): Promise<PaginatedResponse<BibframeInstance>> {
  const searchParams = new URLSearchParams()
  if (params.q) searchParams.set('q', params.q)
  if (params.isbn) searchParams.set('isbn', params.isbn)
  if (params.publisher) searchParams.set('publisher', params.publisher)
  if (params.year_from) searchParams.set('year_from', String(params.year_from))
  if (params.year_to) searchParams.set('year_to', String(params.year_to))
  if (params.work_id) searchParams.set('work_id', String(params.work_id))
  searchParams.set('page', String(params.page || 1))
  searchParams.set('per_page', String(params.per_page || 20))

  return fetchApi<PaginatedResponse<BibframeInstance>>(
    `${BASE_PATH}/instances?${searchParams}`,
    token ? { token } : {}
  )
}

export async function getInstance(
  id: number,
  options: { includeWork?: boolean; includeItems?: boolean } = {},
  token?: string
): Promise<BibframeInstance> {
  const params = new URLSearchParams()
  if (options.includeWork !== undefined) {
    params.set('include_work', String(options.includeWork))
  }
  if (options.includeItems !== undefined) {
    params.set('include_items', String(options.includeItems))
  }

  return fetchApi<BibframeInstance>(`${BASE_PATH}/instances/${id}?${params}`, token ? { token } : {})
}

export async function createInstance(
  data: InstanceCreate,
  token: string
): Promise<BibframeInstance> {
  return fetchApi<BibframeInstance>(`${BASE_PATH}/instances`, {
    method: 'POST',
    body: data,
    token,
  })
}

// --- Items ---

export async function getItems(
  params: ItemSearchParams = {},
  token?: string
): Promise<PaginatedResponse<BibframeItem>> {
  const searchParams = new URLSearchParams()
  if (params.barcode) searchParams.set('barcode', params.barcode)
  if (params.call_number) searchParams.set('call_number', params.call_number)
  if (params.branch) searchParams.set('branch', params.branch)
  if (params.status) searchParams.set('status', params.status)
  if (params.instance_id) searchParams.set('instance_id', String(params.instance_id))
  searchParams.set('page', String(params.page || 1))
  searchParams.set('per_page', String(params.per_page || 20))

  return fetchApi<PaginatedResponse<BibframeItem>>(
    `${BASE_PATH}/items?${searchParams}`,
    token ? { token } : {}
  )
}

export async function getItem(id: number, token?: string): Promise<BibframeItem> {
  return fetchApi<BibframeItem>(`${BASE_PATH}/items/${id}`, token ? { token } : {})
}

export async function createItem(
  data: ItemCreate,
  token: string
): Promise<BibframeItem> {
  return fetchApi<BibframeItem>(`${BASE_PATH}/items`, {
    method: 'POST',
    body: data,
    token,
  })
}

// --- Contributors ---

export async function getContributor(
  id: number,
  token?: string
): Promise<BibframeContributor> {
  return fetchApi<BibframeContributor>(`${BASE_PATH}/contributors/${id}`, token ? { token } : {})
}

export async function createContributor(
  data: Partial<BibframeContributor>,
  token: string
): Promise<BibframeContributor> {
  return fetchApi<BibframeContributor>(`${BASE_PATH}/contributors`, {
    method: 'POST',
    body: data,
    token,
  })
}

// --- Subjects ---

export async function getSubject(id: number, token?: string): Promise<BibframeSubject> {
  return fetchApi<BibframeSubject>(`${BASE_PATH}/subjects/${id}`, token ? { token } : {})
}

export async function createSubject(
  data: Partial<BibframeSubject>,
  token: string
): Promise<BibframeSubject> {
  return fetchApi<BibframeSubject>(`${BASE_PATH}/subjects`, {
    method: 'POST',
    body: data,
    token,
  })
}

// --- Library of Congress Import ---

export async function searchLoc(
  query: string,
  searchType: 'keyword' | 'title' | 'author' | 'subject' | 'isbn' | 'lccn' = 'keyword',
  maxResults = 10,
  token?: string
): Promise<LocSearchResponse> {
  return fetchApi<LocSearchResponse>(`${BASE_PATH}/import/loc/search`, {
    method: 'POST',
    body: { query, search_type: searchType, max_results: maxResults },
    ...(token ? { token } : {}),
  })
}

export async function importFromLoc(
  uri: string,
  options: {
    createWork?: boolean
    createInstance?: boolean
    linkAuthorities?: boolean
    catalogItemId?: number
  } = {},
  token: string
): Promise<LocImportResult> {
  return fetchApi<LocImportResult>(`${BASE_PATH}/import/loc`, {
    method: 'POST',
    body: {
      uri,
      create_work: options.createWork ?? true,
      create_instance: options.createInstance ?? true,
      link_authorities: options.linkAuthorities ?? true,
      catalog_item_id: options.catalogItemId,
    },
    token,
  })
}

// --- MARC Conversion ---

export async function convertMarcToBibframe(
  data: { marcXml?: string; catalogItemId?: number; createEntities?: boolean },
  token: string
): Promise<MarcConversionResult> {
  return fetchApi<MarcConversionResult>(`${BASE_PATH}/convert/marc-to-bibframe`, {
    method: 'POST',
    body: {
      marc_xml: data.marcXml,
      catalog_item_id: data.catalogItemId,
      create_entities: data.createEntities ?? true,
    },
    token,
  })
}

// --- Schema.org ---

export async function getWorkSchemaOrg(workId: number): Promise<SchemaOrgMarkup> {
  return fetchApi<SchemaOrgMarkup>(`${BASE_PATH}/schema-org/work/${workId}`)
}

export async function getInstanceSchemaOrg(instanceId: number): Promise<SchemaOrgMarkup> {
  return fetchApi<SchemaOrgMarkup>(`${BASE_PATH}/schema-org/instance/${instanceId}`)
}

export async function getCatalogItemSchemaOrg(
  catalogItemId: number
): Promise<SchemaOrgMarkup> {
  return fetchApi<SchemaOrgMarkup>(`${BASE_PATH}/schema-org/catalog/${catalogItemId}`)
}

export async function getLibrarySchemaOrg(): Promise<SchemaOrgMarkup> {
  return fetchApi<SchemaOrgMarkup>(`${BASE_PATH}/schema-org/library`)
}

// --- SPARQL ---

export async function executeSparql(
  query: string,
  format: 'json' | 'xml' | 'csv' = 'json'
): Promise<SparqlResults> {
  const response = await fetch(`${API_BASE}/sparql/query?format=${format}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/sparql-query' },
    body: query,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Query failed' }))
    throw new Error(error.detail || 'SPARQL query failed')
  }

  return response.json()
}

export async function getSparqlPrefixes(): Promise<{
  prefixes: Record<string, string>
  example_query: string
}> {
  return fetchApi('/sparql/prefixes')
}

export async function getSparqlExamples(): Promise<{
  examples: Array<{ name: string; description: string; query: string }>
}> {
  return fetchApi('/sparql/examples')
}

// --- Authority Links ---

export async function createAuthorityLink(
  data: {
    source: AuthoritySource
    authorityId: string
    authorityUri?: string
    authorityLabel?: string
    linkType?: string
    workId?: number
    instanceId?: number
    contributorId?: number
    subjectId?: number
  },
  token: string
): Promise<AuthorityLink> {
  return fetchApi<AuthorityLink>(`${BASE_PATH}/authority-links`, {
    method: 'POST',
    body: {
      source: data.source,
      authority_id: data.authorityId,
      authority_uri: data.authorityUri,
      authority_label: data.authorityLabel,
      link_type: data.linkType || 'sameAs',
      work_id: data.workId,
      instance_id: data.instanceId,
      contributor_id: data.contributorId,
      subject_id: data.subjectId,
    },
    token,
  })
}

export async function lookupAuthority(
  source: AuthoritySource,
  authorityId: string,
  token?: string
): Promise<{
  source: string
  authority_id: string
  links: Array<{
    id: number
    link_type: string
    work_id?: number
    instance_id?: number
    contributor_id?: number
    subject_id?: number
    verified: boolean
  }>
}> {
  return fetchApi(`${BASE_PATH}/authority-links/lookup/${source}/${authorityId}`,
    token ? { token } : {}
  )
}

// --- RDF Export ---

export async function exportRdf(
  data: {
    workIds?: number[]
    instanceIds?: number[]
    itemIds?: number[]
    format?: 'jsonld' | 'turtle'
    includeAuthorities?: boolean
  },
  token: string
): Promise<Blob> {
  const response = await fetch(`${API_BASE}${BASE_PATH}/export/rdf`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      work_ids: data.workIds,
      instance_ids: data.instanceIds,
      item_ids: data.itemIds,
      format: data.format || 'jsonld',
      include_authorities: data.includeAuthorities ?? true,
    }),
  })

  if (!response.ok) {
    throw new Error('Export failed')
  }

  return response.blob()
}

// ==================== Utility Functions ====================

export function getAuthorityUrl(source: AuthoritySource, id: string): string {
  // From backend urls_config.ExternalLibraryURLs
  const baseUrls: Record<AuthoritySource, string> = {
    viaf: 'https://viaf.org/viaf/',  // From EXTERNAL_VIAF_BASE
    lcnaf: 'https://id.loc.gov/authorities/names/',  // From EXTERNAL_LOC_AUTHORITIES_NAMES
    lccn: 'https://lccn.loc.gov/',
    lcsh: 'https://id.loc.gov/authorities/subjects/',
    fast: 'https://id.worldcat.org/fast/',  // From EXTERNAL_WORLDCAT_FAST
    wikidata: 'https://www.wikidata.org/entity/',  // From EXTERNAL_WIKIDATA_ENTITY
    isni: 'https://isni.org/isni/',
    orcid: 'https://orcid.org/',  // From EXTERNAL_ORCID
    gnd: 'https://d-nb.info/gnd/',  // From EXTERNAL_GND
    isbn: 'urn:isbn:',
    issn: 'urn:issn:',
    doi: 'https://doi.org/',  // From EXTERNAL_DOI
    oclc: 'https://www.worldcat.org/oclc/',  // From EXTERNAL_OCLC
  }
  return `${baseUrls[source]}${id}`
}

export function formatWorkType(type: WorkType): string {
  const labels: Record<WorkType, string> = {
    text: 'Text',
    spoken_word: 'Spoken Word',
    performed_music: 'Music',
    notated_music: 'Notated Music',
    still_image: 'Image',
    two_dimensional_moving_image: 'Video',
    cartographic_image: 'Map',
    computer_program: 'Software',
    computer_dataset: 'Dataset',
    other: 'Other',
  }
  return labels[type] || type
}

export function formatInstanceType(type: InstanceType): string {
  const labels: Record<InstanceType, string> = {
    print: 'Print',
    electronic: 'Electronic',
    audio: 'Audio',
    audiovisual: 'Audiovisual',
    tactile: 'Tactile',
    microform: 'Microform',
    manuscript: 'Manuscript',
    archive: 'Archive',
  }
  return labels[type] || type
}

export function formatCarrierType(type: CarrierType): string {
  const labels: Record<CarrierType, string> = {
    volume: 'Volume',
    audio_disc: 'Audio Disc',
    computer_disc: 'Computer Disc',
    online_resource: 'Online Resource',
    videodisc: 'Videodisc',
    audiocassette: 'Audiocassette',
    videocassette: 'Videocassette',
    other: 'Other',
  }
  return labels[type] || type
}