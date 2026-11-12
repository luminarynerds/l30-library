/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable max-lines */
import { fetchApi } from '@/lib/api-client'

// ==================== Legal Resources Types ====================

export interface LegalTopic {
  id: number
  name: string
  slug: string
  description: string | null
  parent_id: number | null
  display_order: number
  icon: string | null
  color: string | null
  is_active: boolean
  is_featured: boolean
  keywords: string[]
  meta_description: string | null
  related_resources: Record<string, unknown>[]
  view_count: number
  created_at: string
  updated_at: string | null
}

export interface LegalTopicListResponse {
  topics: LegalTopic[]
  total: number
  limit: number
  offset: number
}

export interface LegalGuide {
  id: number
  title: string
  slug: string
  topic_id: number | null
  summary: string | null
  content: string | null
  reading_level: string
  steps: Record<string, unknown>[]
  related_form_ids: number[]
  related_guide_ids: number[]
  flowchart_image_url: string | null
  timeline_description: string | null
  cost_breakdown: Record<string, unknown>[]
  common_scenarios: Record<string, unknown>[]
  when_need_lawyer: string | null
  video_url: string | null
  printable_checklist: Record<string, unknown>[]
  languages_available: string[]
  is_published: boolean
  is_featured: boolean
  view_count: number
  helpful_count: number
  not_helpful_count: number
  topic_name: string | null
  created_at: string
}

export interface LegalGuideSummary {
  id: number
  title: string
  slug: string
  summary: string | null
  reading_level: string
  is_published: boolean
  is_featured: boolean
  topic_id: number | null
  topic_name: string | null
  helpful_count?: number
  not_helpful_count?: number
  last_reviewed_at?: string | null
}

export interface LegalGuideListResponse {
  guides: LegalGuideSummary[]
  total: number
  limit: number
  offset: number
}

export interface LegalForm {
  id: number
  title: string
  form_number: string | null
  plain_language_title: string | null
  jurisdiction: string
  difficulty_level: 'simple' | 'moderate' | 'complex'
  filing_fee: number | null
  languages_available: string[]
  status: string
  topic_id: number | null
  topic_name: string | null
  description: string | null
  when_to_use: string | null
  form_url: string | null
  instructions_url: string | null
  last_reviewed_at?: string | null
}

export interface LegalFormListResponse {
  forms: LegalForm[]
  total: number
  limit: number
  offset: number
}

export interface LegalClinic {
  id: number
  title: string
  topic_id: number | null
  description: string | null
  date: string
  start_time: string
  end_time: string
  is_virtual: boolean
  virtual_link: string | null
  location_name: string | null
  location_address: string | null
  capacity: number
  current_registrations: number
  spots_available: number
  status: string
  eligibility_notes: string | null
  what_to_bring: Record<string, unknown>[]
  languages_available: string[]
  topic_name: string | null
  provider_name: string | null
  latitude: number | null
  longitude: number | null
}

export interface LegalClinicSummary {
  id: number
  title: string
  date: string
  start_time: string
  end_time: string
  is_virtual: boolean
  location_name: string | null
  status: string
  current_registrations: number
  capacity: number
  spots_available: number
  topic_name: string | null
  latitude: number | null
  longitude: number | null
}

export interface LegalClinicListResponse {
  clinics: LegalClinicSummary[]
  total: number
  limit: number
  offset: number
}

export interface LegalProvider {
  id: number
  name: string
  slug: string
  provider_type: string
  description: string | null
  services: Record<string, unknown>[]
  phone: string | null
  email: string | null
  website: string | null
  address_line1: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  hours: Record<string, unknown>
  languages_spoken: string[]
  accepts_walkins: boolean
  virtual_services: boolean
  is_active: boolean
}

export interface LegalProviderSummary {
  id: number
  name: string
  slug: string
  provider_type: string
  city: string | null
  state: string | null
  phone: string | null
  languages_spoken: string[]
  accepts_walkins: boolean
  virtual_services: boolean
  is_active: boolean
}

export interface LegalProviderListResponse {
  providers: LegalProviderSummary[]
  total: number
  limit: number
  offset: number
}

export interface LegalDisclaimer {
  disclaimer_text: string
  emergency_contacts: { name: string; phone: string; description?: string; is_24_7?: boolean }[]
  quick_exit_enabled: boolean
}

// ==================== API Functions ====================

export async function getLegalDisclaimer(): Promise<LegalDisclaimer> {
  return fetchApi<LegalDisclaimer>('/legal/disclaimer')
}

export async function getLegalTopics(params?: {
  parent_id?: number
  is_active?: boolean
  is_featured?: boolean
  offset?: number
  limit?: number
}, lang?: string): Promise<LegalTopicListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.parent_id !== undefined) searchParams.set('parent_id', String(params.parent_id))
  if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active))
  if (params?.is_featured !== undefined) searchParams.set('is_featured', String(params.is_featured))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))
  if (lang && lang !== 'en') searchParams.set('lang', lang)

  const query = searchParams.toString()
  return fetchApi<LegalTopicListResponse>(`/legal/topics${query ? `?${query}` : ''}`)
}

export async function getLegalTopic(topicId: number): Promise<LegalTopic> {
  return fetchApi<LegalTopic>(`/legal/topics/${topicId}`)
}

export async function getLegalGuides(params?: {
  topic_id?: number
  is_featured?: boolean
  reading_level?: string
  offset?: number
  limit?: number
}): Promise<LegalGuideListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.topic_id !== undefined) searchParams.set('topic_id', String(params.topic_id))
  if (params?.is_featured !== undefined) searchParams.set('is_featured', String(params.is_featured))
  if (params?.reading_level) searchParams.set('reading_level', params.reading_level)
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))

  const query = searchParams.toString()
  return fetchApi<LegalGuideListResponse>(`/legal/guides${query ? `?${query}` : ''}`)
}

export async function getLegalGuide(guideId: number): Promise<LegalGuide> {
  return fetchApi<LegalGuide>(`/legal/guides/${guideId}`)
}

export async function getLegalGuideBySlug(slug: string): Promise<LegalGuide> {
  return fetchApi<LegalGuide>(`/legal/guides/slug/${slug}`)
}

export async function getLegalForms(params?: {
  topic_id?: number
  jurisdiction?: string
  court_type?: string
  difficulty_level?: string
  language?: string
  query?: string
  offset?: number
  limit?: number
}): Promise<LegalFormListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.topic_id !== undefined) searchParams.set('topic_id', String(params.topic_id))
  if (params?.jurisdiction) searchParams.set('jurisdiction', params.jurisdiction)
  if (params?.court_type) searchParams.set('court_type', params.court_type)
  if (params?.difficulty_level) searchParams.set('difficulty_level', params.difficulty_level)
  if (params?.language) searchParams.set('language', params.language)
  if (params?.query) searchParams.set('query', params.query)
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))

  const query = searchParams.toString()
  return fetchApi<LegalFormListResponse>(`/legal/forms${query ? `?${query}` : ''}`)
}

export async function getLegalForm(formId: number): Promise<LegalForm> {
  return fetchApi<LegalForm>(`/legal/forms/${formId}`)
}

export async function getLegalClinics(params?: {
  topic_id?: number
  provider_id?: number
  from_date?: string
  to_date?: string
  is_virtual?: boolean
  offset?: number
  limit?: number
}): Promise<LegalClinicListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.topic_id !== undefined) searchParams.set('topic_id', String(params.topic_id))
  if (params?.provider_id !== undefined) searchParams.set('provider_id', String(params.provider_id))
  if (params?.from_date) searchParams.set('from_date', params.from_date)
  if (params?.to_date) searchParams.set('to_date', params.to_date)
  if (params?.is_virtual !== undefined) searchParams.set('is_virtual', String(params.is_virtual))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))

  const query = searchParams.toString()
  return fetchApi<LegalClinicListResponse>(`/legal/clinics${query ? `?${query}` : ''}`)
}

export async function getUpcomingLegalClinics(params?: {
  days?: number
  limit?: number
}): Promise<LegalClinicSummary[]> {
  const searchParams = new URLSearchParams()
  if (params?.days !== undefined) searchParams.set('days', String(params.days))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))

  const query = searchParams.toString()
  return fetchApi<LegalClinicSummary[]>(`/legal/clinics/upcoming${query ? `?${query}` : ''}`)
}

export async function getLegalClinic(clinicId: number): Promise<LegalClinic> {
  return fetchApi<LegalClinic>(`/legal/clinics/${clinicId}`)
}

export interface GeocodePreviewResponse {
  latitude: number | null
  longitude: number | null
  status: 'success' | 'failed'
}

export async function geocodePreview(address: string): Promise<GeocodePreviewResponse> {
  return fetchApi(`/legal/clinics/geocode-preview?address=${encodeURIComponent(address)}`, {
    method: 'POST',
  })
}

export async function getLegalProviders(params?: {
  provider_type?: string
  topic_id?: number
  city?: string
  state?: string
  language?: string
  accepts_walkins?: boolean
  virtual_services?: boolean
  is_active?: boolean
  offset?: number
  limit?: number
}): Promise<LegalProviderListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.provider_type) searchParams.set('provider_type', params.provider_type)
  if (params?.topic_id !== undefined) searchParams.set('topic_id', String(params.topic_id))
  if (params?.city) searchParams.set('city', params.city)
  if (params?.state) searchParams.set('state', params.state)
  if (params?.language) searchParams.set('language', params.language)
  if (params?.accepts_walkins !== undefined) searchParams.set('accepts_walkins', String(params.accepts_walkins))
  if (params?.virtual_services !== undefined) searchParams.set('virtual_services', String(params.virtual_services))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))

  const query = searchParams.toString()
  return fetchApi<LegalProviderListResponse>(`/legal/providers${query ? `?${query}` : ''}`)
}

export async function getLegalProvider(providerId: number): Promise<LegalProvider> {
  return fetchApi<LegalProvider>(`/legal/providers/${providerId}`)
}

// ==================== Request Types ====================

export interface LegalTopicCreateRequest {
  name: string
  slug: string
  description?: string | null
  parent_id?: number | null
  display_order?: number
  icon?: string | null
  color?: string | null
  is_active?: boolean
  is_featured?: boolean
  keywords?: string[]
  meta_description?: string | null
  related_resources?: Record<string, unknown>[]
}

export interface LegalTopicUpdateRequest {
  name?: string
  slug?: string
  description?: string | null
  parent_id?: number | null
  display_order?: number
  icon?: string | null
  color?: string | null
  is_active?: boolean
  is_featured?: boolean
  keywords?: string[]
  meta_description?: string | null
  related_resources?: Record<string, unknown>[]
}

export interface LegalFormSearchRequest {
  query?: string
  topic_id?: number
  jurisdiction?: string
  court_type?: string
  difficulty_level?: 'simple' | 'moderate' | 'complex'
  language?: string
  has_fee_waiver?: boolean
  fillable_only?: boolean
}

export interface LegalFormCreateRequest {
  title: string
  form_number?: string | null
  topic_id?: number | null
  category?: string | null
  subcategory?: string | null
  jurisdiction: string
  jurisdiction_code?: string | null
  court_type?: string | null
  court_name?: string | null
  description?: string | null
  when_to_use?: string | null
  who_should_use?: string | null
  plain_language_title?: string | null
  form_url?: string | null
  instructions_url?: string | null
  example_url?: string | null
  page_count?: number | null
  filing_fee?: number | null
  fee_waiver_form_id?: number | null
  difficulty_level?: 'simple' | 'moderate' | 'complex'
  estimated_completion_time?: number | null
  notarization_required?: boolean
  signature_requirements?: string | null
  languages_available?: string[]
  screen_reader_friendly?: boolean
  large_print_available?: boolean
  fillable_pdf?: boolean
  version?: string | null
  effective_date?: string | null
  last_updated?: string | null
  change_notes?: string | null
  status?: string
  superseded_by_id?: number | null
  related_form_ids?: number[]
  common_mistakes?: Record<string, unknown>[]
  tips?: Record<string, unknown>[]
  field_help?: Record<string, unknown>
}

export interface LegalFormUpdateRequest {
  title?: string
  form_number?: string | null
  topic_id?: number | null
  category?: string | null
  subcategory?: string | null
  jurisdiction?: string
  jurisdiction_code?: string | null
  court_type?: string | null
  court_name?: string | null
  description?: string | null
  when_to_use?: string | null
  who_should_use?: string | null
  plain_language_title?: string | null
  form_url?: string | null
  instructions_url?: string | null
  example_url?: string | null
  page_count?: number | null
  filing_fee?: number | null
  fee_waiver_form_id?: number | null
  difficulty_level?: 'simple' | 'moderate' | 'complex'
  estimated_completion_time?: number | null
  notarization_required?: boolean
  signature_requirements?: string | null
  languages_available?: string[]
  screen_reader_friendly?: boolean
  large_print_available?: boolean
  fillable_pdf?: boolean
  version?: string | null
  effective_date?: string | null
  last_updated?: string | null
  change_notes?: string | null
  status?: string
  superseded_by_id?: number | null
  related_form_ids?: number[]
  common_mistakes?: Record<string, unknown>[]
  tips?: Record<string, unknown>[]
  field_help?: Record<string, unknown>
}

export interface LegalFormPacketItemCreate {
  form_id: number
  order?: number
  instructions?: string | null
  is_required?: boolean
  conditional_notes?: string | null
}

export interface LegalFormPacketCreateRequest {
  name: string
  slug: string
  topic_id?: number | null
  description?: string | null
  use_case?: string | null
  who_should_use?: string | null
  checklist?: Record<string, unknown>[]
  filing_sequence?: Record<string, unknown>[]
  total_filing_fee?: number | null
  estimated_total_time?: number | null
  timeline_description?: string | null
  cost_breakdown?: Record<string, unknown>[]
  instructions?: string | null
  related_guide_ids?: number[]
  jurisdiction?: string | null
  court_addresses?: Record<string, unknown>[]
  is_active?: boolean
  forms?: LegalFormPacketItemCreate[]
}

export interface LegalGuideCreateRequest {
  title: string
  slug: string
  topic_id?: number | null
  summary?: string | null
  content?: string | null
  reading_level?: string
  steps?: Record<string, unknown>[]
  related_form_ids?: number[]
  related_guide_ids?: number[]
  related_resource_urls?: Record<string, unknown>[]
  flowchart_data?: Record<string, unknown> | null
  flowchart_image_url?: string | null
  timeline_description?: string | null
  cost_breakdown?: Record<string, unknown>[]
  common_scenarios?: Record<string, unknown>[]
  when_need_lawyer?: string | null
  complexity_warning_signs?: string[]
  video_url?: string | null
  video_transcript?: string | null
  printable_checklist?: Record<string, unknown>[]
  languages_available?: string[]
  is_published?: boolean
  is_featured?: boolean
}

export interface LegalGuideUpdateRequest {
  title?: string
  slug?: string
  topic_id?: number | null
  summary?: string | null
  content?: string | null
  reading_level?: string
  steps?: Record<string, unknown>[]
  related_form_ids?: number[]
  related_guide_ids?: number[]
  related_resource_urls?: Record<string, unknown>[]
  flowchart_data?: Record<string, unknown> | null
  flowchart_image_url?: string | null
  timeline_description?: string | null
  cost_breakdown?: Record<string, unknown>[]
  common_scenarios?: Record<string, unknown>[]
  when_need_lawyer?: string | null
  complexity_warning_signs?: string[]
  video_url?: string | null
  video_transcript?: string | null
  printable_checklist?: Record<string, unknown>[]
  languages_available?: string[]
  is_published?: boolean
  is_featured?: boolean
}

export interface LegalServiceProviderSearchRequest {
  query?: string
  provider_type?: string
  topic_id?: number
  city?: string
  state?: string
  language?: string
  accepts_walkins?: boolean
  virtual_services?: boolean
  special_population?: string
}

export interface LegalServiceProviderCreateRequest {
  name: string
  slug: string
  provider_type: string
  description?: string | null
  services?: Record<string, unknown>[]
  topic_ids?: number[]
  eligibility_criteria?: string | null
  income_limits?: string | null
  income_limit_percentage?: number | null
  geographic_restrictions?: string | null
  other_requirements?: string | null
  phone?: string | null
  phone_toll_free?: string | null
  email?: string | null
  website?: string | null
  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  hours?: Record<string, unknown>
  hours_notes?: string | null
  languages_spoken?: string[]
  accepts_walkins?: boolean
  appointment_required?: boolean
  wheelchair_accessible?: boolean
  virtual_services?: boolean
  specializations?: string[]
  special_populations?: string[]
  is_active?: boolean
}

export interface LegalClinicRegistrationCreateRequest {
  name: string
  email?: string | null
  phone?: string | null
  preferred_contact?: 'email' | 'phone' | 'text'
  accessibility_needs?: string | null
  language_preference?: string
  interpreter_needed?: boolean
  issue_description?: string | null
}

export interface LegalClinicCreateRequest {
  title: string
  topic_id?: number | null
  description?: string | null
  provider_id?: number | null
  date: string
  start_time: string
  end_time: string
  timezone?: string
  is_virtual?: boolean
  virtual_link?: string | null
  virtual_platform?: string | null
  location_name?: string | null
  location_address?: string | null
  location_room?: string | null
  capacity?: number
  waitlist_capacity?: number
  registration_required?: boolean
  registration_opens?: string | null
  registration_closes?: string | null
  eligibility_notes?: string | null
  what_to_bring?: Record<string, unknown>[]
  languages_available?: string[]
  interpreter_available?: boolean
  follow_up_resources?: Record<string, unknown>[]
  wheelchair_accessible?: boolean
  asl_interpreter?: boolean
  attorney_names?: string[]
  public_notes?: string | null
  internal_notes?: string | null
}

export interface CourtLocationCreateRequest {
  name: string
  code?: string | null
  court_type: string
  jurisdiction: string
  jurisdiction_code?: string | null
  address_line1: string
  address_line2?: string | null
  city: string
  state: string
  zip_code: string
  phone?: string | null
  phone_clerk?: string | null
  phone_self_help?: string | null
  fax?: string | null
  email?: string | null
  website?: string | null
  general_hours?: Record<string, unknown>
  filing_hours?: Record<string, unknown>
  self_help_hours?: Record<string, unknown>
  holiday_closures?: Record<string, unknown>[]
  has_self_help_center?: boolean
  self_help_services?: Record<string, unknown>[]
  self_help_appointment_required?: boolean
  self_help_appointment_url?: string | null
  e_filing_available?: boolean
  e_filing_url?: string | null
  e_filing_instructions?: string | null
  what_to_bring?: Record<string, unknown>[]
  dress_code?: string | null
  prohibited_items?: string[]
  parking_info?: string | null
  parking_cost?: number | null
  wheelchair_accessible?: boolean
  accessibility_notes?: string | null
  remote_hearings_available?: boolean
  remote_hearing_platform?: string | null
  remote_hearing_instructions?: string | null
  latitude?: number | null
  longitude?: number | null
  directions_notes?: string | null
  is_active?: boolean
}

export interface FormFinderWizardStartRequest {
  patron_id?: number | null
}

export interface FormFinderAnswerSubmitRequest {
  question_slug: string
  answer: string | string[]
}

export interface LegalGlossaryTermCreateRequest {
  term: string
  slug: string
  definition_simple?: string | null
  definition_standard: string
  definition_legal?: string | null
  pronunciation?: string | null
  pronunciation_audio_url?: string | null
  related_term_slugs?: string[]
  see_also?: string[]
  usage_example?: string | null
  context_notes?: string | null
  translations?: Record<string, unknown>
  translated_definitions?: Record<string, unknown>
  topic_ids?: number[]
  is_active?: boolean
}

export interface DeadlineCalculationRequest {
  rule_id?: number | null
  rule_slug?: string | null
  start_date: string
  reminder_email?: string | null
  reminder_phone?: string | null
  enable_reminders?: boolean
  user_notes?: string | null
}

export interface FeeWaiverEligibilityCheckRequest {
  jurisdiction: string
  household_size: number
  annual_income: number
  receives_public_benefits?: string[]
}

export interface ExpungementEligibilityCheckRequest {
  jurisdiction: string
  offense_category: string
  offense_type?: string | null
  conviction_date: string
  sentence_completed_date?: string | null
}

// ==================== Response Types ====================

export interface LegalClinicRegistration {
  id: number
  clinic_id: number
  patron_id: number | null
  name: string
  email: string | null
  phone: string | null
  preferred_contact: string
  status: string
  waitlist_position: number | null
  accessibility_needs: string | null
  language_preference: string
  interpreter_needed: boolean
  issue_description: string | null
  confirmation_sent: boolean
  reminder_sent: boolean
  checked_in_at: string | null
  created_at: string
  clinic_title: string | null
  clinic_date: string | null
}

export interface FormFinderQuestion {
  id: number
  slug: string
  question_text: string
  help_text: string | null
  question_type: string
  options: Record<string, unknown>[]
  required: boolean
  category: string | null
}

export interface FormFinderWizardResponse {
  session_token: string
  current_step: string | null
  status: string
  next_question: FormFinderQuestion | null
  progress_percentage: number
}

export interface FormFinderResultsResponse {
  session_token: string
  recommended_forms: LegalForm[]
  recommended_packets: LegalFormPacketSummary[]
  recommended_guides: LegalGuideSummary[]
  jurisdiction_state: string | null
  jurisdiction_county: string | null
  court_type_determined: string | null
  printable_checklist: Record<string, unknown>[]
}

export interface LegalFormPacketSummary {
  id: number
  name: string
  slug: string
  description: string | null
  jurisdiction: string | null
  total_filing_fee: number | null
  form_count: number
  is_active: boolean
  topic_name: string | null
}

export interface LegalFormPacket {
  id: number
  name: string
  slug: string
  topic_id: number | null
  description: string | null
  use_case: string | null
  who_should_use: string | null
  checklist: Record<string, unknown>[]
  filing_sequence: Record<string, unknown>[]
  total_filing_fee: number | null
  estimated_total_time: number | null
  timeline_description: string | null
  cost_breakdown: Record<string, unknown>[]
  instructions: string | null
  related_guide_ids: number[]
  jurisdiction: string | null
  court_addresses: Record<string, unknown>[]
  is_active: boolean
  download_count: number
  view_count: number
  created_at: string
  updated_at: string | null
  created_by_id: number | null
  forms: LegalFormPacketItem[]
  topic_name: string | null
}

export interface LegalFormPacketItem {
  id: number
  packet_id: number
  form_id: number
  order: number
  instructions: string | null
  is_required: boolean
  conditional_notes: string | null
  form_title: string | null
  form_number: string | null
}

export interface LegalGlossaryTerm {
  id: number
  term: string
  slug: string
  definition_simple: string | null
  definition_standard: string
  definition_legal: string | null
  pronunciation: string | null
  pronunciation_audio_url: string | null
  related_term_slugs: string[]
  see_also: string[]
  usage_example: string | null
  context_notes: string | null
  translations: Record<string, unknown>
  translated_definitions: Record<string, unknown>
  topic_ids: number[]
  is_active: boolean
  view_count: number
  created_at: string
  updated_at: string | null
}

export interface DeadlineCalculationResponse {
  id: number
  rule_name: string
  start_date: string
  deadline_date: string
  days_until_deadline: number
  warning_dates: string[]
  reminders_enabled: boolean
  user_notes: string | null
}

export interface FeeWaiverEligibilityResponse {
  is_eligible: boolean
  eligibility_reason: string
  automatic_eligibility: boolean
  partial_waiver_available: boolean
  payment_plan_available: boolean
  form_id: number | null
  form_title: string | null
  required_documentation: string[]
  next_steps: string[]
}

export interface ExpungementEligibilityResponse {
  is_eligible: boolean
  eligibility_notes: string
  waiting_period_met: boolean
  waiting_period_end_date: string | null
  requirements: string[]
  exclusions: string[]
  form_ids: number[]
  estimated_timeline: string | null
  estimated_cost: number | null
}

export interface WizardHelpResponse {
  status: string
  message: string
  next_steps: string[]
}

export interface CourtLocation {
  id: number
  name: string
  code: string | null
  court_type: string
  jurisdiction: string
  jurisdiction_code: string | null
  address_line1: string
  address_line2: string | null
  city: string
  state: string
  zip_code: string
  phone: string | null
  phone_clerk: string | null
  phone_self_help: string | null
  fax: string | null
  email: string | null
  website: string | null
  general_hours: Record<string, unknown>
  filing_hours: Record<string, unknown>
  self_help_hours: Record<string, unknown>
  holiday_closures: Record<string, unknown>[]
  has_self_help_center: boolean
  self_help_services: Record<string, unknown>[]
  self_help_appointment_required: boolean
  self_help_appointment_url: string | null
  e_filing_available: boolean
  e_filing_url: string | null
  e_filing_instructions: string | null
  what_to_bring: Record<string, unknown>[]
  dress_code: string | null
  prohibited_items: string[]
  parking_info: string | null
  parking_cost: number | null
  wheelchair_accessible: boolean
  accessibility_notes: string | null
  remote_hearings_available: boolean
  remote_hearing_platform: string | null
  remote_hearing_instructions: string | null
  latitude: number | null
  longitude: number | null
  directions_notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
  created_by_id: number | null
}

// ==================== Non-GET API Functions ====================

export async function createLegalTopic(data: LegalTopicCreateRequest): Promise<LegalTopic> {
  return fetchApi<LegalTopic>('/legal/topics', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateLegalTopic(topicId: number, data: LegalTopicUpdateRequest): Promise<LegalTopic> {
  return fetchApi<LegalTopic>(`/legal/topics/${topicId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function searchLegalForms(
  searchRequest: LegalFormSearchRequest,
  params?: { offset?: number; limit?: number }
): Promise<LegalFormListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))

  const query = searchParams.toString()
  return fetchApi<LegalFormListResponse>(`/legal/forms/search${query ? `?${query}` : ''}`, {
    method: 'POST',
    body: JSON.stringify(searchRequest),
  })
}

export async function trackFormDownload(formId: number): Promise<{ status: string }> {
  return fetchApi<{ status: string }>(`/legal/forms/${formId}/download`, {
    method: 'POST',
  })
}

export async function createLegalForm(data: LegalFormCreateRequest): Promise<LegalForm> {
  return fetchApi<LegalForm>('/legal/forms', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateLegalForm(formId: number, data: LegalFormUpdateRequest): Promise<LegalForm> {
  return fetchApi<LegalForm>(`/legal/forms/${formId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function createFormPacket(data: LegalFormPacketCreateRequest): Promise<LegalFormPacket> {
  return fetchApi<LegalFormPacket>('/legal/packets', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function recordGuideHelpful(guideId: number, wasHelpful: boolean): Promise<{ status: string }> {
  return fetchApi<{ status: string }>(`/legal/guides/${guideId}/helpful?was_helpful=${wasHelpful}`, {
    method: 'POST',
  })
}

export async function createLegalGuide(data: LegalGuideCreateRequest): Promise<LegalGuide> {
  return fetchApi<LegalGuide>('/legal/guides', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateLegalGuide(guideId: number, data: LegalGuideUpdateRequest): Promise<LegalGuide> {
  return fetchApi<LegalGuide>(`/legal/guides/${guideId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function publishLegalGuide(guideId: number): Promise<LegalGuide> {
  return fetchApi<LegalGuide>(`/legal/guides/${guideId}/publish`, {
    method: 'POST',
  })
}

export async function searchLegalProviders(
  searchRequest: LegalServiceProviderSearchRequest,
  params?: { offset?: number; limit?: number }
): Promise<LegalProviderListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))

  const query = searchParams.toString()
  return fetchApi<LegalProviderListResponse>(`/legal/providers/search${query ? `?${query}` : ''}`, {
    method: 'POST',
    body: JSON.stringify(searchRequest),
  })
}

export async function createLegalProvider(data: LegalServiceProviderCreateRequest): Promise<LegalProvider> {
  return fetchApi<LegalProvider>('/legal/providers', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function registerForClinic(
  clinicId: number,
  data: LegalClinicRegistrationCreateRequest
): Promise<LegalClinicRegistration> {
  return fetchApi<LegalClinicRegistration>(`/legal/clinics/${clinicId}/register`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function cancelClinicRegistration(registrationId: number): Promise<void> {
  return fetchApi<void>(`/legal/clinics/registrations/${registrationId}`, {
    method: 'DELETE',
  })
}

export async function createLegalClinic(data: LegalClinicCreateRequest): Promise<LegalClinic> {
  return fetchApi<LegalClinic>('/legal/clinics', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createCourt(data: CourtLocationCreateRequest): Promise<CourtLocation> {
  return fetchApi<CourtLocation>('/legal/courts', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function startFormFinderWizard(data?: FormFinderWizardStartRequest): Promise<FormFinderWizardResponse> {
  return fetchApi<FormFinderWizardResponse>('/legal/wizard/start', {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  })
}

export async function submitWizardAnswer(
  sessionToken: string,
  data: FormFinderAnswerSubmitRequest
): Promise<FormFinderWizardResponse> {
  return fetchApi<FormFinderWizardResponse>(`/legal/wizard/${sessionToken}/answer`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function completeWizard(sessionToken: string): Promise<FormFinderResultsResponse> {
  return fetchApi<FormFinderResultsResponse>(`/legal/wizard/${sessionToken}/complete`, {
    method: 'POST',
  })
}

export async function requestWizardHelp(sessionToken: string, reason: string): Promise<WizardHelpResponse> {
  return fetchApi<WizardHelpResponse>(`/legal/wizard/${sessionToken}/help?reason=${encodeURIComponent(reason)}`, {
    method: 'POST',
  })
}

export async function createGlossaryTerm(data: LegalGlossaryTermCreateRequest): Promise<LegalGlossaryTerm> {
  return fetchApi<LegalGlossaryTerm>('/legal/glossary', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function calculateDeadline(data: DeadlineCalculationRequest): Promise<DeadlineCalculationResponse> {
  return fetchApi<DeadlineCalculationResponse>('/legal/deadlines/calculate', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function checkFeeWaiverEligibility(
  data: FeeWaiverEligibilityCheckRequest
): Promise<FeeWaiverEligibilityResponse> {
  return fetchApi<FeeWaiverEligibilityResponse>('/legal/fee-waiver/check', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function checkExpungementEligibility(
  data: ExpungementEligibilityCheckRequest
): Promise<ExpungementEligibilityResponse> {
  return fetchApi<ExpungementEligibilityResponse>('/legal/expungement/check', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ==================== Legal Collections (Phase 1 Expansion) ====================

export interface LegalCollection {
  id: number
  title: string
  slug: string
  description: string
  situation: string
  guide_ids: number[]
  form_ids: number[]
  clinic_ids: number[]
  provider_ids: number[]
  glossary_term_ids: number[]
  estimated_time_minutes: number | null
  complexity_level: 'beginner' | 'intermediate' | 'advanced' | null
  success_outcomes: string[]
  reading_level: string
  step_by_step_summary: Record<string, unknown>[]
  icon: string | null
  color_code: string | null
  available_languages: string[]
  // Librarian recommendations - Priority 1
  estimated_cost_min: number
  estimated_cost_max: number | null
  cost_description: string | null
  fee_waiver_available: boolean
  resource_details: Record<string, unknown>[]
  last_reviewed_date: string | null
  view_count: number
  click_through_count: number
  completion_count: number
  helpful_count: number
  unhelpful_count: number
  is_published: boolean
  is_featured: boolean
  display_order: number
  created_at: string
  updated_at: string | null
  created_by_id: number | null
}

export interface LegalCollectionListResponse {
  collections: LegalCollection[]
  total: number
  limit: number
  offset: number
}

export async function getLegalCollections(params?: {
  situation?: string
  is_featured?: boolean
  limit?: number
  offset?: number
}): Promise<LegalCollectionListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.situation) searchParams.append('situation', params.situation)
  if (params?.is_featured !== undefined) searchParams.append('is_featured', String(params.is_featured))
  if (params?.limit) searchParams.append('limit', String(params.limit))
  if (params?.offset) searchParams.append('offset', String(params.offset))

  const query = searchParams.toString()
  return fetchApi<LegalCollectionListResponse>(`/legal/collections${query ? `?${query}` : ''}`)
}

export async function getLegalCollection(collectionId: number): Promise<LegalCollection> {
  return fetchApi<LegalCollection>(`/legal/collections/${collectionId}`)
}

export async function getLegalCollectionBySlug(slug: string): Promise<LegalCollection> {
  return fetchApi<LegalCollection>(`/legal/collections/slug/${slug}`)
}

export async function recordCollectionFeedback(
  collectionId: number,
  wasHelpful: boolean
): Promise<{ status: string }> {
  return fetchApi<{ status: string }>(`/legal/collections/${collectionId}/helpful`, {
    method: 'POST',
    body: JSON.stringify({ was_helpful: wasHelpful }),
  })
}

// ==================== Glossary API Functions ====================

export interface LegalGlossaryListResponse {
  terms: LegalGlossaryTerm[]
  total: number
  limit: number
  offset: number
}

export async function getLegalGlossaryTerms(params?: {
  query?: string
  letter?: string
  offset?: number
  limit?: number
}): Promise<LegalGlossaryListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.query) searchParams.set('query', params.query)
  if (params?.letter) searchParams.set('letter', params.letter)
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))
  const query = searchParams.toString()
  return fetchApi<LegalGlossaryListResponse>(`/legal/glossary${query ? `?${query}` : ''}`)
}

export async function getLegalGlossaryTerm(slug: string): Promise<LegalGlossaryTerm> {
  return fetchApi<LegalGlossaryTerm>(`/legal/glossary/${slug}`)
}

export async function updateGlossaryTerm(slug: string, data: Partial<LegalGlossaryTermCreateRequest>): Promise<LegalGlossaryTerm> {
  return fetchApi<LegalGlossaryTerm>(`/legal/glossary/${slug}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// ==================== Courts API Functions ====================

export interface CourtLocationListResponse {
  courts: CourtLocation[]
  total: number
  limit: number
  offset: number
}

export async function getLegalCourts(params?: {
  court_type?: string
  jurisdiction?: string
  city?: string
  state?: string
  has_self_help?: boolean
  e_filing?: boolean
  offset?: number
  limit?: number
}): Promise<CourtLocationListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.court_type) searchParams.set('court_type', params.court_type)
  if (params?.jurisdiction) searchParams.set('jurisdiction', params.jurisdiction)
  if (params?.city) searchParams.set('city', params.city)
  if (params?.state) searchParams.set('state', params.state)
  if (params?.has_self_help !== undefined) searchParams.set('has_self_help', String(params.has_self_help))
  if (params?.e_filing !== undefined) searchParams.set('e_filing', String(params.e_filing))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))
  const query = searchParams.toString()
  return fetchApi<CourtLocationListResponse>(`/legal/courts${query ? `?${query}` : ''}`)
}

export async function getLegalCourt(courtId: number): Promise<CourtLocation> {
  return fetchApi<CourtLocation>(`/legal/courts/${courtId}`)
}

export async function updateCourt(courtId: number, data: Partial<CourtLocationCreateRequest>): Promise<CourtLocation> {
  return fetchApi<CourtLocation>(`/legal/courts/${courtId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// ==================== Provider Update ====================

export async function updateLegalProvider(
  providerId: number,
  data: Partial<LegalServiceProviderCreateRequest>
): Promise<LegalProvider> {
  return fetchApi<LegalProvider>(`/legal/providers/${providerId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// ==================== Clinic Update ====================

export async function updateLegalClinic(
  clinicId: number,
  data: Partial<LegalClinicCreateRequest>
): Promise<LegalClinic> {
  return fetchApi<LegalClinic>(`/legal/clinics/${clinicId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// ==================== Deadline Rules ====================

export interface DeadlineRule {
  id: number
  name: string
  slug: string
  description: string | null
  deadline_type: string
  days: number
  use_business_days: boolean
  exclude_holidays: boolean
  start_event: string | null
  legal_citation: string | null
  jurisdiction: string | null
  court_type: string | null
}

export async function getDeadlineRules(params?: {
  deadline_type?: string
  jurisdiction?: string
  topic_id?: number
}): Promise<DeadlineRule[]> {
  const searchParams = new URLSearchParams()
  if (params?.deadline_type) searchParams.set('deadline_type', params.deadline_type)
  if (params?.jurisdiction) searchParams.set('jurisdiction', params.jurisdiction)
  if (params?.topic_id !== undefined) searchParams.set('topic_id', String(params.topic_id))
  const query = searchParams.toString()
  return fetchApi<DeadlineRule[]>(`/legal/deadlines/rules${query ? `?${query}` : ''}`)
}

// ==================== Packets API Functions ====================

export interface LegalFormPacketListResponse {
  packets: LegalFormPacketSummary[]
  total: number
  limit: number
  offset: number
}

export async function getLegalFormPackets(params?: {
  topic_id?: number
  jurisdiction?: string
  is_active?: boolean
  offset?: number
  limit?: number
}): Promise<LegalFormPacketListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.topic_id !== undefined) searchParams.set('topic_id', String(params.topic_id))
  if (params?.jurisdiction) searchParams.set('jurisdiction', params.jurisdiction)
  if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))
  const query = searchParams.toString()
  return fetchApi<LegalFormPacketListResponse>(`/legal/packets${query ? `?${query}` : ''}`)
}

export async function getLegalFormPacket(packetId: number): Promise<LegalFormPacket> {
  return fetchApi<LegalFormPacket>(`/legal/packets/${packetId}`)
}


export async function downloadPacketPdf(packetId: number): Promise<Blob> {
  const resp = await fetch(`/api/v1/legal/packets/${packetId}/pdf`)
  if (!resp.ok) throw new Error('Failed to download packet PDF')
  return resp.blob()
}

// ==================== Reviews / Audit ====================

export interface LegalReviewCycle {
  id: number
  document: { id: number; title: string; document_number?: string | null } | null
  status: string
  due_date: string | null
  scheduled_date: string | null
  assigned_to: { id: number; name: string } | null
  review_count: number
}

export interface LegalReviewCycleListResponse {
  review_cycles: LegalReviewCycle[]
  total: number
}

export async function getLegalReviewCycles(params?: {
  status?: string
  overdue?: boolean
  upcoming_days?: number
  limit?: number
  offset?: number
}): Promise<LegalReviewCycleListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.overdue !== undefined) searchParams.set('overdue', String(params.overdue))
  if (params?.upcoming_days !== undefined) searchParams.set('upcoming_days', String(params.upcoming_days))
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit))
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset))
  const query = searchParams.toString()
  return fetchApi<LegalReviewCycleListResponse>(`/legal/reviews/cycles${query ? `?${query}` : ''}`)
}


// ==================== Eligibility Check ====================

export interface EligibilityResult {
  provider_id: number
  provider_name: string
  phone: string | null
  virtual_services: boolean
  status: 'likely_eligible' | 'may_be_eligible' | 'over_limit'
  income_limit: number
  percentage_of_fpl: number
}

export interface EligibilityCheckResponse {
  results: EligibilityResult[]
  household_size: number
  income: number
}

export async function checkEligibility(
  params: { household_size: number; income: number }
): Promise<EligibilityCheckResponse> {
  const searchParams = new URLSearchParams({
    household_size: params.household_size.toString(),
    income: params.income.toString(),
  })
  return fetchApi(`/legal/eligibility/check?${searchParams}`)
}


// ==================== Eligibility Threshold Admin ====================

export interface EligibilityThreshold {
  id: number
  provider_id: number
  provider_name: string | null
  household_size: number
  income_limit: number
  percentage_of_fpl: number
  effective_date: string
  expires_date: string | null
  created_by_id: number | null
  updated_at: string | null
}

export interface EligibilityThresholdListResponse {
  thresholds: EligibilityThreshold[]
  total: number
}

export interface EligibilityThresholdCreateRequest {
  provider_id: number
  household_size: number
  income_limit: number
  percentage_of_fpl: number
  effective_date: string
  expires_date?: string | null
}

export interface EligibilityThresholdUpdateRequest {
  household_size?: number
  income_limit?: number
  percentage_of_fpl?: number
  effective_date?: string
  expires_date?: string | null
}

export interface EligibilityFPGImportRequest {
  provider_id: number
  percentage_of_fpl?: number
  effective_date: string
  expire_existing?: boolean
}

export interface EligibilityFPGImportResponse {
  created: EligibilityThreshold[]
  count: number
}

export async function listEligibilityThresholds(
  params?: { provider_id?: number; include_expired?: boolean }
): Promise<EligibilityThresholdListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.provider_id !== undefined) {
    searchParams.set('provider_id', String(params.provider_id))
  }
  if (params?.include_expired) {
    searchParams.set('include_expired', 'true')
  }
  const query = searchParams.toString()
  return fetchApi<EligibilityThresholdListResponse>(
    `/legal/eligibility/thresholds${query ? `?${query}` : ''}`
  )
}

export async function createEligibilityThreshold(
  data: EligibilityThresholdCreateRequest
): Promise<EligibilityThreshold> {
  return fetchApi<EligibilityThreshold>('/legal/eligibility/thresholds', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateEligibilityThreshold(
  thresholdId: number,
  data: EligibilityThresholdUpdateRequest
): Promise<EligibilityThreshold> {
  return fetchApi<EligibilityThreshold>(`/legal/eligibility/thresholds/${thresholdId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteEligibilityThreshold(thresholdId: number): Promise<void> {
  return fetchApi<void>(`/legal/eligibility/thresholds/${thresholdId}`, {
    method: 'DELETE',
  })
}

export async function importFPG2026(
  data: EligibilityFPGImportRequest
): Promise<EligibilityFPGImportResponse> {
  return fetchApi<EligibilityFPGImportResponse>(
    '/legal/eligibility/thresholds/import-fpg-2026',
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )
}
