/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Genealogy Research Platform API ====================
// API client for the collaborative genealogy research platform

import { api } from '@/lib/api-client'
import { API_BASE } from '@/api/types'

const BASE = `${API_BASE}/genealogy/research`

// ============================================================================
// Types
// ============================================================================

export interface ResearchProject {
  id: number
  name: string
  description: string | null
  owner_id: number
  is_public: boolean
  allow_join_requests: boolean
  default_license: string
  person_count: number
  document_count: number
  generation_count: number
  created_at: string
  updated_at: string
}

export interface ProjectCollaborator {
  id: number
  project_id: number
  user_id: number
  role: 'owner' | 'admin' | 'editor' | 'viewer'
  is_active: boolean
  accepted_at: string | null
  created_at: string
}

export interface Person {
  id: number
  project_id: number
  given_names: string
  surname: string | null
  maiden_name: string | null
  suffix: string | null
  prefix: string | null
  nickname: string | null
  alternate_names: string | null
  birth_date: string | null
  birth_place: string | null
  birth_place_lat: number | null
  birth_place_lng: number | null
  death_date: string | null
  death_place: string | null
  gender: string | null
  is_living: boolean
  occupation: string | null
  religion: string | null
  ethnicity: string | null
  nationality: string | null
  biography: string | null
  profile_photo_url: string | null
  confidence_level: number
  is_verified: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface PersonSummary {
  id: number
  given_names: string
  surname: string | null
  birth_date: string | null
  death_date: string | null
  gender: string | null
  is_living: boolean
  profile_photo_url: string | null
  confidence_level: number
}

export interface Relationship {
  id: number
  project_id: number
  person1_id: number
  person2_id: number
  relationship_type: string
  marriage_date: string | null
  marriage_place: string | null
  divorce_date: string | null
  is_current: boolean
  source_citation: string | null
  confidence_level: number
  notes: string | null
  created_at: string
}

export interface FamilyTreeNode {
  person: PersonSummary
  parents: number[]
  children: number[]
  spouses: number[]
  siblings: number[]
}

export interface FamilyTree {
  project_id: number
  root_person_id: number | null
  nodes: FamilyTreeNode[]
  relationships: Relationship[]
  generation_count: number
  person_count: number
}

export interface GenealogyDocument {
  id: number
  project_id: number
  title: string
  description: string | null
  document_type: string
  source_repository: string | null
  source_citation: string | null
  file_url: string | null
  file_type: string | null
  file_size: number | null
  thumbnail_url: string | null
  ocr_text: string | null
  ocr_confidence: number | null
  ocr_language: string | null
  ocr_processed_at: string | null
  document_date: string | null
  document_location: string | null
  status: string
  annotations: string | null
  tags: string | null
  created_at: string
  updated_at: string
}

export interface TimelineEvent {
  id: number
  project_id: number
  person_id: number
  event_type: string
  title: string
  description: string | null
  event_date: string | null
  end_date: string | null
  location: string | null
  latitude: number | null
  longitude: number | null
  source_document_id: number | null
  source_citation: string | null
  confidence_level: number
  media_url: string | null
  created_at: string
}

export interface ResearchNote {
  id: number
  project_id: number
  author_id: number
  title: string
  content: string
  note_type: string
  person_id: number | null
  document_id: number | null
  sources: string | null
  is_resolved: boolean
  is_pinned: boolean
  priority: number
  tags: string | null
  created_at: string
  updated_at: string
}

export interface RecordLink {
  id: number
  project_id: number
  source_document_id: number | null
  target_document_id: number | null
  source_person_id: number | null
  target_person_id: number | null
  similarity_score: number
  match_reasons: string | null
  matched_fields: string | null
  status: string
  reviewer_notes: string | null
  created_at: string
}

export interface DNAProfile {
  id: number
  person_id: number
  project_id: number
  test_type: string
  testing_company: string | null
  kit_number: string | null
  test_date: string | null
  haplogroup: string | null
  ethnicity_estimate: string | null
  consent_given: boolean
  consent_scope: string | null
  created_at: string
  updated_at: string
}

export interface DNAMatch {
  id: number
  profile1_id: number
  profile2_id: number
  shared_centimorgans: number | null
  shared_segments: number | null
  longest_segment: number | null
  predicted_relationship: string | null
  confidence_level: number | null
  status: string
  notes: string | null
  created_at: string
}

export interface ResearchGuidance {
  id: number
  project_id: number
  person_id: number | null
  suggestion_type: string
  title: string
  description: string
  rationale: string | null
  suggested_database: string | null
  suggested_record_type: string | null
  suggested_search_terms: string | null
  suggested_location: string | null
  suggested_date_range: string | null
  priority: number
  is_dismissed: boolean
  is_completed: boolean
  created_at: string
}

export interface ExternalReference {
  id: number
  project_id: number
  person_id: number | null
  document_id: number | null
  source: string
  external_id: string
  external_url: string | null
  record_title: string | null
  record_type: string | null
  last_synced_at: string | null
  sync_status: string
  created_at: string
}

export interface SearchResult {
  result_type: string
  id: number
  title: string
  snippet: string | null
  project_id: number
  relevance_score: number
}

export interface ProjectDashboard {
  project: ResearchProject
  recent_persons: PersonSummary[]
  recent_documents: GenealogyDocument[]
  pending_record_links: number
  unresolved_notes: number
  active_guidance: ResearchGuidance[]
  collaborator_count: number
}

// ============================================================================
// Projects
// ============================================================================

export const researchProjectsApi = {
  create: (data: { name: string; description?: string; is_public?: boolean }) =>
    api.post<ResearchProject>(`${BASE}/projects`, data),

  list: (skip = 0, limit = 50) =>
    api.get(`${BASE}/projects?skip=${skip}&limit=${limit}`),

  listPublic: (skip = 0, limit = 50) =>
    api.get(`${BASE}/projects/public?skip=${skip}&limit=${limit}`),

  get: (projectId: number) =>
    api.get(`${BASE}/projects/${projectId}`),

  update: (projectId: number, data: Partial<ResearchProject>) =>
    api.put(`${BASE}/projects/${projectId}`, data),

  delete: (projectId: number) =>
    api.delete(`${BASE}/projects/${projectId}`),

  getDashboard: (projectId: number) =>
    api.get(`${BASE}/projects/${projectId}/dashboard`),
}

// ============================================================================
// Collaborators
// ============================================================================

export const collaboratorsApi = {
  invite: (projectId: number, data: { user_id: number; role: string }) =>
    api.post<ProjectCollaborator>(`${BASE}/projects/${projectId}/collaborators`, data),

  list: (projectId: number) =>
    api.get(`${BASE}/projects/${projectId}/collaborators`),

  updateRole: (projectId: number, userId: number, data: { role: string }) =>
    api.put(`${BASE}/projects/${projectId}/collaborators/${userId}`, data),

  remove: (projectId: number, userId: number) =>
    api.delete(`${BASE}/projects/${projectId}/collaborators/${userId}`),
}

// ============================================================================
// Persons
// ============================================================================

export const personsApi = {
  create: (projectId: number, data: Partial<Person>) =>
    api.post<Person>(`${BASE}/projects/${projectId}/persons`, data),

  list: (projectId: number, search?: string, skip = 0, limit = 100) => {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) })
    if (search) params.set('search', search)
    return api.get(`${BASE}/projects/${projectId}/persons?${params}`)
  },

  get: (projectId: number, personId: number) =>
    api.get(`${BASE}/projects/${projectId}/persons/${personId}`),

  update: (projectId: number, personId: number, data: Partial<Person>) =>
    api.put(`${BASE}/projects/${projectId}/persons/${personId}`, data),

  delete: (projectId: number, personId: number) =>
    api.delete(`${BASE}/projects/${projectId}/persons/${personId}`),

  getRelationships: (projectId: number, personId: number) =>
    api.get(`${BASE}/projects/${projectId}/persons/${personId}/relationships`),

  getTimeline: (projectId: number, personId: number) =>
    api.get(`${BASE}/projects/${projectId}/persons/${personId}/timeline`),

  getExternalRefs: (projectId: number, personId: number) =>
    api.get(`${BASE}/projects/${projectId}/persons/${personId}/external-references`),
}

// ============================================================================
// Relationships
// ============================================================================

export const relationshipsApi = {
  create: (projectId: number, data: {
    person1_id: number
    person2_id: number
    relationship_type: string
    marriage_date?: string
    marriage_place?: string
  }) =>
    api.post<Relationship>(`${BASE}/projects/${projectId}/relationships`, data),

  delete: (projectId: number, relationshipId: number) =>
    api.delete(`${BASE}/projects/${projectId}/relationships/${relationshipId}`),
}

// ============================================================================
// Family Tree
// ============================================================================

export const familyTreeApi = {
  get: (projectId: number, rootPersonId?: number) => {
    const params = rootPersonId ? `?root_person_id=${rootPersonId}` : ''
    return api.get(`${BASE}/projects/${projectId}/tree${params}`)
  },
}

// ============================================================================
// Documents
// ============================================================================

export const documentsApi = {
  create: (projectId: number, data: Partial<GenealogyDocument>) =>
    api.post<GenealogyDocument>(`${BASE}/projects/${projectId}/documents`, data),

  list: (projectId: number, params?: { document_type?: string; search?: string; skip?: number; limit?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.document_type) searchParams.set('document_type', params.document_type)
    if (params?.search) searchParams.set('search', params.search)
    searchParams.set('skip', String(params?.skip ?? 0))
    searchParams.set('limit', String(params?.limit ?? 50))
    return api.get(`${BASE}/projects/${projectId}/documents?${searchParams}`)
  },

  get: (projectId: number, documentId: number) =>
    api.get(`${BASE}/projects/${projectId}/documents/${documentId}`),

  update: (projectId: number, documentId: number, data: Partial<GenealogyDocument>) =>
    api.put(`${BASE}/projects/${projectId}/documents/${documentId}`, data),

  triggerOCR: (projectId: number, documentId: number) =>
    api.post(`${BASE}/projects/${projectId}/documents/${documentId}/ocr`),

  linkPerson: (projectId: number, data: {
    person_id: number
    document_id: number
    role_in_document?: string
    excerpt?: string
  }) =>
    api.post(`${BASE}/projects/${projectId}/document-links`, data),
}

// ============================================================================
// Timeline
// ============================================================================

export const timelineApi = {
  createEvent: (projectId: number, data: Partial<TimelineEvent>) =>
    api.post<TimelineEvent>(`${BASE}/projects/${projectId}/timeline-events`, data),

  getPersonTimeline: (projectId: number, personId: number) =>
    api.get(`${BASE}/projects/${projectId}/persons/${personId}/timeline`),

  getFamilyTimeline: (projectId: number, personIds: number[]) =>
    api.get(`${BASE}/projects/${projectId}/family-timeline?person_ids=${personIds.join(',')}`),

  updateEvent: (projectId: number, eventId: number, data: Partial<TimelineEvent>) =>
    api.put(`${BASE}/projects/${projectId}/timeline-events/${eventId}`, data),

  deleteEvent: (projectId: number, eventId: number) =>
    api.delete(`${BASE}/projects/${projectId}/timeline-events/${eventId}`),
}

// ============================================================================
// Research Notes
// ============================================================================

export const researchNotesApi = {
  create: (projectId: number, data: Partial<ResearchNote>) =>
    api.post<ResearchNote>(`${BASE}/projects/${projectId}/notes`, data),

  list: (projectId: number, params?: { note_type?: string; person_id?: number; unresolved_only?: boolean }) => {
    const searchParams = new URLSearchParams()
    if (params?.note_type) searchParams.set('note_type', params.note_type)
    if (params?.person_id) searchParams.set('person_id', String(params.person_id))
    if (params?.unresolved_only) searchParams.set('unresolved_only', 'true')
    return api.get(`${BASE}/projects/${projectId}/notes?${searchParams}`)
  },

  update: (projectId: number, noteId: number, data: Partial<ResearchNote>) =>
    api.put(`${BASE}/projects/${projectId}/notes/${noteId}`, data),
}

// ============================================================================
// Record Linking
// ============================================================================

export const recordLinkingApi = {
  analyze: (projectId: number, threshold = 0.6) =>
    api.post<RecordLink[]>(`${BASE}/projects/${projectId}/record-links/analyze?threshold=${threshold}`),

  list: (projectId: number, status?: string) => {
    const params = status ? `?status=${status}` : ''
    return api.get(`${BASE}/projects/${projectId}/record-links${params}`)
  },

  review: (projectId: number, linkId: number, data: { status: string; reviewer_notes?: string }) =>
    api.put(`${BASE}/projects/${projectId}/record-links/${linkId}`, data),
}

// ============================================================================
// DNA
// ============================================================================

export const dnaApi = {
  createProfile: (projectId: number, data: Partial<DNAProfile>) =>
    api.post<DNAProfile>(`${BASE}/projects/${projectId}/dna-profiles`, data),

  listProfiles: (projectId: number, personId?: number) => {
    const params = personId ? `?person_id=${personId}` : ''
    return api.get(`${BASE}/projects/${projectId}/dna-profiles${params}`)
  },

  createMatch: (projectId: number, data: Partial<DNAMatch>) =>
    api.post<DNAMatch>(`${BASE}/projects/${projectId}/dna-matches`, data),

  getMatches: (projectId: number, profileId: number) =>
    api.get(`${BASE}/projects/${projectId}/dna-profiles/${profileId}/matches`),
}

// ============================================================================
// Research Guidance
// ============================================================================

export const guidanceApi = {
  generate: (projectId: number) =>
    api.post<ResearchGuidance[]>(`${BASE}/projects/${projectId}/guidance/generate`),

  list: (projectId: number, personId?: number) => {
    const params = personId ? `?person_id=${personId}` : ''
    return api.get(`${BASE}/projects/${projectId}/guidance${params}`)
  },

  dismiss: (projectId: number, suggestionId: number) =>
    api.put(`${BASE}/projects/${projectId}/guidance/${suggestionId}/dismiss`, {}),

  complete: (projectId: number, suggestionId: number) =>
    api.put(`${BASE}/projects/${projectId}/guidance/${suggestionId}/complete`, {}),
}

// ============================================================================
// External References
// ============================================================================

export const externalRefsApi = {
  create: (projectId: number, data: Partial<ExternalReference>) =>
    api.post<ExternalReference>(`${BASE}/projects/${projectId}/external-references`, data),

  getForPerson: (projectId: number, personId: number) =>
    api.get(`${BASE}/projects/${projectId}/persons/${personId}/external-references`),
}

// ============================================================================
// Search
// ============================================================================

export const genealogySearchApi = {
  search: (projectId: number, query: string, options?: {
    search_persons?: boolean
    search_documents?: boolean
    search_notes?: boolean
  }) =>
    api.post(`${BASE}/projects/${projectId}/search`, {
      query,
      search_persons: options?.search_persons ?? true,
      search_documents: options?.search_documents ?? true,
      search_notes: options?.search_notes ?? true,
    }),
}