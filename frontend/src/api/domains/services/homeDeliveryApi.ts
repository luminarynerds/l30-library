/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * HomeDelivery Delivery Service API Client
 */
import { fetchApi } from '@/lib/api-client'


// ============================================================================
// Types
// ============================================================================

export type HomeDeliveryApplicationStatus =
  | 'pending'
  | 'under_review'
  | 'approved'
  | 'denied'
  | 'waitlisted'
  | 'withdrawn';

export type HomeDeliveryEnrollmentStatus =
  | 'active'
  | 'paused'
  | 'suspended'
  | 'terminated';

export type DeliveryFrequency =
  | 'weekly'
  | 'biweekly'
  | 'monthly'
  | 'on_demand';

export type VolunteerStatus =
  | 'active'
  | 'inactive'
  | 'on_leave'
  | 'pending_approval'
  | 'terminated';

export type DeliveryStatus =
  | 'scheduled'
  | 'items_selected'
  | 'packed'
  | 'out_for_delivery'
  | 'delivered'
  | 'delivery_failed'
  | 'picked_up'
  | 'cancelled';

export type RouteStatus =
  | 'draft'
  | 'planned'
  | 'in_progress'
  | 'completed'
  | 'cancelled';

export interface HomeDeliveryApplication {
  id: number;
  patron_id: number;
  patron_name?: string;
  patron_library_card?: string;
  status: HomeDeliveryApplicationStatus;
  reason: string;
  medical_documentation: boolean;
  delivery_address: string;
  delivery_instructions?: string;
  contact_phone: string;
  alternate_contact_name?: string;
  alternate_contact_phone?: string;
  preferred_frequency: DeliveryFrequency;
  preferred_day?: string;
  preferred_time_start?: string;
  preferred_time_end?: string;
  submitted_at: string;
  reviewed_by_id?: number;
  reviewed_by_name?: string;
  reviewed_at?: string;
  review_notes?: string;
  denial_reason?: string;
}

export interface HomeDeliveryEnrollment {
  id: number;
  patron_id: number;
  patron_name?: string;
  patron_library_card?: string;
  application_id?: number;
  status: HomeDeliveryEnrollmentStatus;
  delivery_address: string;
  delivery_instructions?: string;
  contact_phone: string;
  alternate_contact_name?: string;
  alternate_contact_phone?: string;
  delivery_frequency: DeliveryFrequency;
  preferred_day?: string;
  preferred_time_start?: string;
  preferred_time_end?: string;
  next_scheduled_delivery?: string;
  assigned_volunteer_id?: number;
  assigned_volunteer_name?: string;
  enrolled_at: string;
  paused_at?: string;
  pause_reason?: string;
  pause_until?: string;
  total_deliveries: number;
  last_delivery_date?: string;
  reading_preferences?: ReadingPreferenceProfile;
}

export interface ReadingPreferenceProfile {
  id: number;
  enrollment_id: number;
  format_preferences: string[];
  preferred_genres: string[];
  excluded_genres: string[];
  favorite_authors: string[];
  excluded_authors: string[];
  fiction_preference: number;
  content_rating: string;
  language_preference: string;
  interests: string[];
  prefers_large_print: boolean;
  prefers_audiobooks: boolean;
  prefers_short_books: boolean;
  max_pages_preference?: number;
  notes?: string;
  current_series: { series_name: string; last_read_book?: string; next_book?: string }[];
}

export interface DeliveryVolunteer {
  id: number;
  user_id: number;
  user_name?: string;
  user_email?: string;
  status: VolunteerStatus;
  phone: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  has_vehicle: boolean;
  vehicle_type?: string;
  can_transport_large_items: boolean;
  background_check_completed: boolean;
  background_check_date?: string;
  background_check_expiry?: string;
  training_completed: boolean;
  training_date?: string;
  available_days: string[];
  available_time_start?: string;
  available_time_end?: string;
  max_deliveries_per_day: number;
  max_deliveries_per_week: number;
  preferred_areas: string[];
  max_driving_distance?: number;
  total_deliveries: number;
  total_volunteer_hours: number;
  recognition_level: string;
  achievements: { name: string; date: string }[];
  approved_at?: string;
  last_active_at?: string;
  assigned_patrons_count?: number;
}

export interface Delivery {
  id: number;
  enrollment_id: number;
  patron_id?: number;
  patron_name?: string;
  patron_library_card?: string;
  route_id?: number;
  route_name?: string;
  route_order?: number;
  status: DeliveryStatus;
  scheduled_date: string;
  scheduled_time_start?: string;
  scheduled_time_end?: string;
  delivery_address: string;
  delivery_instructions?: string;
  packed_at?: string;
  out_for_delivery_at?: string;
  delivered_at?: string;
  delivery_failed_at?: string;
  failure_reason?: string;
  reschedule_date?: string;
  pickup_requested: boolean;
  picked_up_at?: string;
  items_count: number;
  items_delivered: number;
  items_picked_up: number;
  staff_notes?: string;
  patron_notes?: string;
  volunteer_notes?: string;
  has_feedback?: boolean;
  created_at: string;
  items?: DeliveryItem[];
  feedback?: DeliveryFeedback;
}

export interface DeliveryItem {
  id: number;
  delivery_id: number;
  item_id?: number;
  item_copy_id?: number;
  item_title: string;
  item_author?: string;
  item_format?: string;
  item_barcode?: string;
  status: string;
  checkout_id?: number;
  checked_out_at?: string;
  due_date?: string;
  returned_at?: string;
  return_condition?: string;
  selection_reason?: string;
  patron_requested: boolean;
}

export interface DeliveryRoute {
  id: number;
  name: string;
  date: string;
  status: RouteStatus;
  volunteer_id?: number;
  volunteer_name?: string;
  estimated_duration_minutes?: number;
  estimated_distance_miles?: number;
  optimized_order: number[];
  planned_start_time?: string;
  planned_end_time?: string;
  actual_start_time?: string;
  actual_end_time?: string;
  total_stops: number;
  completed_stops: number;
  total_items: number;
  notes?: string;
  created_by_id?: number;
  created_at: string;
  deliveries?: Delivery[];
}

export interface DeliveryFeedback {
  id: number;
  delivery_id: number;
  overall_rating: number;
  item_satisfaction?: number;
  volunteer_rating?: number;
  timeliness_rating?: number;
  comments?: string;
  item_feedback?: string;
  suggestions_for_next_delivery?: string;
  would_recommend?: boolean;
  requires_follow_up: boolean;
  follow_up_completed: boolean;
  follow_up_notes?: string;
  follow_up_by_name?: string;
  follow_up_at?: string;
  submitted_at: string;
}

export interface VolunteerHourLog {
  id: number;
  volunteer_id: number;
  volunteer_name?: string;
  date: string;
  hours: number;
  activity_type: string;
  delivery_route_id?: number;
  notes?: string;
  verified: boolean;
  verified_by_id?: number;
  verified_by_name?: string;
  verified_at?: string;
}

export interface HomeDeliveryReportSummary {
  total_enrolled_patrons: number;
  active_enrolled_patrons: number;
  pending_applications: number;
  active_volunteers: number;
  total_deliveries_this_month: number;
  total_items_delivered_this_month: number;
  average_delivery_rating?: number;
  total_volunteer_hours_this_month: number;
}

// ============================================================================
// Applications API
// ============================================================================

export async function createHomeDeliveryApplication(data: {
  reason: string;
  medical_documentation?: boolean;
  delivery_address: string;
  delivery_instructions?: string;
  contact_phone: string;
  alternate_contact_name?: string;
  alternate_contact_phone?: string;
  preferred_frequency?: DeliveryFrequency;
  preferred_day?: string;
  preferred_time_start?: string;
  preferred_time_end?: string;
}): Promise<HomeDeliveryApplication> {
  return fetchApi<HomeDeliveryApplication>(`/home-delivery/applications`, { method: 'POST', body: data });
}

export async function getMyApplications(): Promise<HomeDeliveryApplication[]> {
  return fetchApi(`/home-delivery/applications/my`);
}

export async function getMyEnrollment(): Promise<HomeDeliveryEnrollment | null> {
  return fetchApi(`/home-delivery/enrollment/my`);
}

export async function listApplications(params?: {
  status?: HomeDeliveryApplicationStatus;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<{ applications: HomeDeliveryApplication[]; total: number }> {
  return fetchApi(`/home-delivery/staff/applications`, { params: params });
}

export async function getApplication(id: number): Promise<HomeDeliveryApplication> {
  return fetchApi(`/home-delivery/staff/applications/${id}`);
}

export async function reviewApplication(id: number, data: {
  status: HomeDeliveryApplicationStatus;
  review_notes?: string;
  denial_reason?: string;
}): Promise<HomeDeliveryApplication> {
  return fetchApi<HomeDeliveryApplication>(`/home-delivery/staff/applications/${id}/review`, { method: 'POST', body: data });
}

// ============================================================================
// Enrollments API
// ============================================================================

export async function createEnrollment(data: {
  application_id: number;
  delivery_address?: string;
  delivery_instructions?: string;
  contact_phone?: string;
  delivery_frequency?: DeliveryFrequency;
  preferred_day?: string;
  assigned_volunteer_id?: number;
  next_scheduled_delivery?: string;
}): Promise<HomeDeliveryEnrollment> {
  return fetchApi<HomeDeliveryEnrollment>(`/home-delivery/staff/enrollments`, { method: 'POST', body: data });
}

export async function listEnrollments(params?: {
  status?: HomeDeliveryEnrollmentStatus;
  search?: string;
  volunteer_id?: number;
  upcoming_delivery?: boolean;
  limit?: number;
  offset?: number;
}): Promise<{ enrollments: HomeDeliveryEnrollment[]; total: number }> {
  return fetchApi(`/home-delivery/staff/enrollments`, { params: params });
}

export async function getEnrollment(id: number): Promise<HomeDeliveryEnrollment> {
  return fetchApi(`/home-delivery/staff/enrollments/${id}`);
}

// Mirrors backend HomeDeliveryEnrollmentUpdate (StrictInputSchema, extra="forbid"):
// sending response-only fields gets the whole request 422'd.
export interface HomeDeliveryEnrollmentUpdate {
  delivery_address?: string;
  delivery_instructions?: string;
  contact_phone?: string;
  alternate_contact_name?: string;
  alternate_contact_phone?: string;
  delivery_frequency?: DeliveryFrequency;
  preferred_day?: string;
  preferred_time_start?: string;
  preferred_time_end?: string;
  assigned_volunteer_id?: number;
  next_scheduled_delivery?: string;
}

export async function updateEnrollment(id: number, data: HomeDeliveryEnrollmentUpdate): Promise<HomeDeliveryEnrollment> {
  return fetchApi<HomeDeliveryEnrollment>(`/home-delivery/staff/enrollments/${id}`, { method: 'PATCH', body: data });
}

export async function updateEnrollmentStatus(id: number, data: {
  status: HomeDeliveryEnrollmentStatus;
  pause_reason?: string;
  pause_until?: string;
  termination_reason?: string;
}): Promise<HomeDeliveryEnrollment> {
  return fetchApi<HomeDeliveryEnrollment>(`/home-delivery/staff/enrollments/${id}/status`, { method: 'POST', body: data });
}

// Mirrors backend ReadingPreferenceProfileUpdate: the profile's editable fields
// only — id/enrollment_id are rejected by strict validation.
export type ReadingPreferencesUpdate = Partial<Omit<ReadingPreferenceProfile, 'id' | 'enrollment_id'>>;

export async function updateReadingPreferences(
  enrollmentId: number,
  data: ReadingPreferencesUpdate
): Promise<ReadingPreferenceProfile> {
  return fetchApi<ReadingPreferenceProfile>(`/home-delivery/staff/enrollments/${enrollmentId}/preferences`, { method: 'PATCH', body: data });
}

// ============================================================================
// Volunteers API
// ============================================================================

export async function registerAsVolunteer(data: {
  user_id: number;
  phone: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  has_vehicle?: boolean;
  vehicle_type?: string;
  can_transport_large_items?: boolean;
  available_days?: string[];
  available_time_start?: string;
  available_time_end?: string;
  max_deliveries_per_day?: number;
  max_deliveries_per_week?: number;
  preferred_areas?: string[];
  max_driving_distance?: number;
}): Promise<DeliveryVolunteer> {
  return fetchApi<DeliveryVolunteer>(`/home-delivery/volunteers/register`, { method: 'POST', body: data });
}

export async function getMyVolunteerProfile(): Promise<DeliveryVolunteer | null> {
  return fetchApi(`/home-delivery/volunteers/my-profile`);
}

export async function listVolunteers(params?: {
  status?: VolunteerStatus;
  search?: string;
  available_on?: string;
  limit?: number;
  offset?: number;
}): Promise<{ volunteers: DeliveryVolunteer[]; total: number }> {
  return fetchApi(`/home-delivery/volunteers`, { params: params });
}

export async function getVolunteer(id: number): Promise<DeliveryVolunteer> {
  return fetchApi(`/home-delivery/volunteers/${id}`);
}

export async function updateVolunteerStatus(id: number, data: {
  status: VolunteerStatus;
  background_check_completed?: boolean;
  background_check_date?: string;
  background_check_expiry?: string;
  training_completed?: boolean;
  training_date?: string;
}): Promise<DeliveryVolunteer> {
  return fetchApi<DeliveryVolunteer>(`/home-delivery/volunteers/${id}/status`, { method: 'POST', body: data });
}

export async function getVolunteerHours(
  volunteerId: number,
  params?: { start_date?: string; end_date?: string; verified_only?: boolean }
): Promise<{ logs: VolunteerHourLog[]; total: number; total_hours: number }> {
  return fetchApi(`/home-delivery/volunteers/${volunteerId}/hours`, { params: params });
}

export async function logVolunteerHours(volunteerId: number, data: {
  date: string;
  hours: number;
  activity_type: string;
  delivery_route_id?: number;
  notes?: string;
}): Promise<VolunteerHourLog> {
  return fetchApi<VolunteerHourLog>(`/home-delivery/volunteers/${volunteerId}/hours`, { method: 'POST', body: data });
}

export async function verifyVolunteerHours(logId: number): Promise<VolunteerHourLog> {
  return fetchApi<VolunteerHourLog>(`/home-delivery/volunteers/hours/${logId}/verify`, { method: 'POST' });
}

// ============================================================================
// Deliveries API
// ============================================================================

export async function createDelivery(data: {
  enrollment_id: number;
  scheduled_date: string;
  scheduled_time_start?: string;
  scheduled_time_end?: string;
  route_id?: number;
  staff_notes?: string;
}): Promise<Delivery> {
  return fetchApi<Delivery>(`/home-delivery/staff/deliveries`, { method: 'POST', body: data });
}

export async function listDeliveries(params?: {
  status?: DeliveryStatus;
  enrollment_id?: number;
  route_id?: number;
  scheduled_from?: string;
  scheduled_to?: string;
  needs_items?: boolean;
  needs_packing?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<{ deliveries: Delivery[]; total: number }> {
  return fetchApi(`/home-delivery/staff/deliveries`, { params: params });
}

export async function getDelivery(id: number): Promise<Delivery> {
  return fetchApi(`/home-delivery/staff/deliveries/${id}`);
}

export async function updateDeliveryStatus(id: number, data: {
  status: DeliveryStatus;
  volunteer_notes?: string;
  delivery_signature?: string;
  delivery_photo?: string;
  failure_reason?: string;
  reschedule_date?: string;
}): Promise<Delivery> {
  return fetchApi<Delivery>(`/home-delivery/staff/deliveries/${id}/status`, { method: 'POST', body: data });
}

export async function addItemToDelivery(deliveryId: number, data: {
  item_id: number;
  item_copy_id?: number;
  selection_reason?: string;
  patron_requested?: boolean;
}): Promise<DeliveryItem> {
  return fetchApi<DeliveryItem>(`/home-delivery/staff/deliveries/${deliveryId}/items`, { method: 'POST', body: data });
}

export async function removeItemFromDelivery(deliveryId: number, itemId: number): Promise<void> {
  await fetchApi(`/home-delivery/staff/deliveries/${deliveryId}/items/${itemId}`, { method: 'DELETE' });
}

export async function updateDelivery(id: number, data: {
  scheduled_date?: string;
  scheduled_time_start?: string;
  scheduled_time_end?: string;
  route_id?: number | null;
  staff_notes?: string;
  patron_notes?: string;
}): Promise<Delivery> {
  return fetchApi<Delivery>(`/home-delivery/staff/deliveries/${id}`, { method: 'PATCH', body: data });
}

export async function getDeliveryItems(deliveryId: number): Promise<DeliveryItem[]> {
  return fetchApi(`/home-delivery/staff/deliveries/${deliveryId}/items`);
}

export async function updateDeliveryItem(deliveryId: number, itemId: number, data: {
  status?: string;
  return_condition?: string;
}): Promise<DeliveryItem> {
  return fetchApi<DeliveryItem>(`/home-delivery/staff/deliveries/${deliveryId}/items/${itemId}`, { method: 'PATCH', body: data });
}

export async function getMyDeliveries(params?: {
  status?: DeliveryStatus;
  limit?: number;
  offset?: number;
}): Promise<{ deliveries: Delivery[]; total: number }> {
  return fetchApi(`/home-delivery/deliveries/my`, { params: params });
}

export async function submitDeliveryFeedback(deliveryId: number, data: {
  overall_rating: number;
  item_satisfaction?: number;
  volunteer_rating?: number;
  timeliness_rating?: number;
  comments?: string;
  item_feedback?: string;
  suggestions_for_next_delivery?: string;
  would_recommend?: boolean;
}): Promise<DeliveryFeedback> {
  return fetchApi<DeliveryFeedback>(`/home-delivery/deliveries/${deliveryId}/feedback`, { method: 'POST', body: data });
}

// ============================================================================
// Routes API
// ============================================================================

export async function createRoute(data: {
  name: string;
  date: string;
  volunteer_id?: number;
  planned_start_time?: string;
  planned_end_time?: string;
  notes?: string;
}): Promise<DeliveryRoute> {
  return fetchApi<DeliveryRoute>(`/home-delivery/staff/routes`, { method: 'POST', body: data });
}

export async function listRoutes(params?: {
  status?: RouteStatus;
  volunteer_id?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}): Promise<{ routes: DeliveryRoute[]; total: number }> {
  return fetchApi(`/home-delivery/staff/routes`, { params: params });
}

export async function getRoute(id: number): Promise<DeliveryRoute> {
  return fetchApi(`/home-delivery/staff/routes/${id}`);
}

export async function assignDeliveriesToRoute(routeId: number, deliveryIds: number[]): Promise<DeliveryRoute> {
  return fetchApi<DeliveryRoute>(`/home-delivery/staff/routes/${routeId}/assign-deliveries`, { method: 'POST', body: deliveryIds });
}

export async function optimizeRoute(routeId: number, startLocation?: string): Promise<DeliveryRoute> {
  return fetchApi<DeliveryRoute>(`/home-delivery/staff/routes/${routeId}/optimize`, { method: 'POST', body: { start_location: startLocation } });
}

export async function updateRouteStatus(routeId: number, data: {
  status: RouteStatus;
  actual_start_time?: string;
  actual_end_time?: string;
}): Promise<DeliveryRoute> {
  return fetchApi<DeliveryRoute>(`/home-delivery/staff/routes/${routeId}/status`, { method: 'POST', body: data });
}

export async function updateRoute(routeId: number, data: {
  name?: string;
  volunteer_id?: number | null;
  planned_start_time?: string;
  planned_end_time?: string;
  notes?: string;
}): Promise<DeliveryRoute> {
  return fetchApi<DeliveryRoute>(`/home-delivery/staff/routes/${routeId}`, { method: 'PATCH', body: data });
}
export async function reorderRouteStops(routeId: number, deliveryIds: number[]): Promise<DeliveryRoute> {
  return fetchApi<DeliveryRoute>(`/home-delivery/staff/routes/${routeId}/order`, { method: 'PUT', body: { optimized_order: deliveryIds } });
}


export async function getReadingPreferences(enrollmentId: number): Promise<ReadingPreferenceProfile> {
  return fetchApi(`/home-delivery/staff/enrollments/${enrollmentId}/preferences`);
}

export type ItemRequestType = 'specific_title' | 'author' | 'subject' | 'genre' | 'surprise_me';

export interface HomeDeliveryItemRequest {
  id: number;
  enrollment_id: number;
  request_type: ItemRequestType;
  title?: string;
  author?: string;
  description?: string;
  item_id?: number;
  item_title?: string;
  fulfilled: boolean;
  fulfilled_in_delivery_id?: number;
  staff_notes?: string;
  created_at: string;
}

export async function getEnrollmentItemRequests(
  enrollmentId: number,
  params?: { fulfilled?: boolean; limit?: number; offset?: number }
): Promise<{ requests: HomeDeliveryItemRequest[]; total: number }> {
  return fetchApi(`/home-delivery/staff/enrollments/${enrollmentId}/item-requests`, { params: params });
}

// ============================================================================
// Reports API
// ============================================================================

export async function getHomeDeliverySummary(): Promise<HomeDeliveryReportSummary> {
  return fetchApi(`/home-delivery/reports/summary`);
}

export async function getVolunteerRecognition(): Promise<{
  top_by_hours: { volunteer_id: number; name: string; hours: number; recognition_level: string }[];
  top_by_deliveries: { volunteer_id: number; name: string; deliveries: number; recognition_level: string }[];
  recent_milestones: { volunteer_id: number; volunteer_name: string; milestone: string; total_hours: number }[];
  recognition_levels: Record<string, number>;
}> {
  return fetchApi(`/home-delivery/reports/volunteer-recognition`);
}

export async function getSatisfactionMetrics(): Promise<{
  overall_ratings: {
    overall?: number;
    item_satisfaction?: number;
    volunteer_rating?: number;
    timeliness_rating?: number;
    total_responses: number;
  };
  would_recommend_rate?: number;
  rating_distribution: Record<number, number>;
  monthly_trend: { period: string; average_rating?: number }[];
  follow_up_stats: { pending_follow_up: number; completed_follow_up: number };
}> {
  return fetchApi(`/home-delivery/reports/satisfaction-metrics`);
}

export async function getFeedbackRequiringFollowup(): Promise<DeliveryFeedback[]> {
  return fetchApi(`/home-delivery/staff/feedback/requiring-followup`);
}

export async function completeFeedbackFollowup(feedbackId: number, notes: string): Promise<DeliveryFeedback> {
  return fetchApi<DeliveryFeedback>(`/home-delivery/staff/feedback/${feedbackId}/follow-up`, { method: 'POST', body: { follow_up_notes: notes } });
}

// ============================================================================
// Patron Self-Service: Item Requests
// ============================================================================

export async function createItemRequest(data: {
  request_type: ItemRequestType;
  title?: string;
  author?: string;
  description?: string;
  item_id?: number;
}): Promise<HomeDeliveryItemRequest> {
  return fetchApi<HomeDeliveryItemRequest>(`/home-delivery/item-requests`, { method: 'POST', body: data });
}

export async function getMyItemRequests(params?: {
  fulfilled?: boolean;
  limit?: number;
  offset?: number;
}): Promise<{ requests: HomeDeliveryItemRequest[]; total: number }> {
  return fetchApi(`/home-delivery/item-requests/my`, { params: params });
}

// ============================================================================
// Patron Self-Service: Enrollment Management
// ============================================================================

export async function updateMyReadingPreferences(
  data: ReadingPreferencesUpdate
): Promise<ReadingPreferenceProfile> {
  return fetchApi<ReadingPreferenceProfile>(`/home-delivery/enrollment/my/preferences`, { method: 'PATCH', body: data });
}

export async function pauseMyEnrollment(params?: {
  pause_until?: string;
  reason?: string;
}): Promise<HomeDeliveryEnrollment> {
  return fetchApi<HomeDeliveryEnrollment>(`/home-delivery/enrollment/my/pause`, { method: 'POST', params: params });
}

export async function resumeMyEnrollment(): Promise<HomeDeliveryEnrollment> {
  return fetchApi<HomeDeliveryEnrollment>(`/home-delivery/enrollment/my/resume`, { method: 'POST' });
}

export async function updateMyEnrollment(params: {
  delivery_instructions?: string;
  contact_phone?: string;
  alternate_contact_name?: string;
  alternate_contact_phone?: string;
  preferred_day?: string;
  preferred_time_start?: string;
  preferred_time_end?: string;
}): Promise<HomeDeliveryEnrollment> {
  return fetchApi<HomeDeliveryEnrollment>('/home-delivery/enrollment/my', { method: 'PATCH', params });
}

// ============================================================================
// Patron Self-Service: Delivery Tracking
// ============================================================================

export async function getMyDelivery(deliveryId: number): Promise<Delivery> {
  return fetchApi(`/home-delivery/deliveries/my/${deliveryId}`);
}

export async function rescheduleMyDelivery(
  deliveryId: number,
  params: { new_date: string; reason?: string }
): Promise<Delivery> {
  return fetchApi<Delivery>(`/home-delivery/deliveries/my/${deliveryId}/reschedule`, { method: 'POST', params: params });
}

export interface DeliveryTrackingInfo {
  delivery_id: number;
  status: DeliveryStatus;
  status_display: string;
  scheduled_date: string;
  time_window?: string;
  delivery_address: string;
  items_count: number;
  estimated_arrival?: string;
  volunteer_name?: string;
  is_out_for_delivery: boolean;
  can_reschedule: boolean;
  timeline: {
    event: string;
    timestamp?: string;
    description: string;
    completed: boolean;
  }[];
}

export async function trackMyDelivery(deliveryId: number): Promise<DeliveryTrackingInfo> {
  return fetchApi(`/home-delivery/deliveries/my/tracking/${deliveryId}`);
}

export interface UpcomingDeliveriesInfo {
  upcoming: {
    id: number;
    scheduled_date: string;
    time_window?: string;
    status: DeliveryStatus;
    items_count: number;
    is_out_for_delivery: boolean;
  }[];
  next_delivery?: {
    id: number;
    scheduled_date: string;
    time_window?: string;
    status: DeliveryStatus;
    items_count: number;
    is_out_for_delivery: boolean;
  };
  enrollment_status: HomeDeliveryEnrollmentStatus;
  total_deliveries: number;
}

export async function getMyUpcomingDeliveries(): Promise<UpcomingDeliveriesInfo> {
  return fetchApi(`/home-delivery/deliveries/my/upcoming`);
}

// ============================================================================
// Volunteer Self-Service
// ============================================================================

// Mirrors backend DeliveryVolunteerUpdate: contact/availability fields only.
// Status, background-check, training, and computed fields go through
// updateVolunteerStatus or are read-only.
export interface DeliveryVolunteerUpdate {
  phone?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  has_vehicle?: boolean;
  vehicle_type?: string;
  can_transport_large_items?: boolean;
  available_days?: string[];
  available_time_start?: string;
  available_time_end?: string;
  max_deliveries_per_day?: number;
  max_deliveries_per_week?: number;
  preferred_areas?: string[];
  max_driving_distance?: number;
}

export async function updateMyVolunteerProfile(
  data: DeliveryVolunteerUpdate
): Promise<DeliveryVolunteer> {
  return fetchApi<DeliveryVolunteer>(`/home-delivery/volunteers/my-profile`, { method: 'PATCH', body: data });
}

export async function getMyVolunteerHours(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}): Promise<{ logs: VolunteerHourLog[]; total: number; total_hours: number }> {
  return fetchApi(`/home-delivery/volunteers/my-hours`, { params: params });
}

// ============================================================================
// Staff: Volunteer Management Extensions
// ============================================================================

export async function updateVolunteer(
  id: number,
  data: DeliveryVolunteerUpdate
): Promise<DeliveryVolunteer> {
  return fetchApi<DeliveryVolunteer>(`/home-delivery/volunteers/${id}`, { method: 'PATCH', body: data });
}

// Field names match the backend/database: time_start/time_end, not start_time/end_time.
export interface VolunteerSchedule {
  id: number;
  volunteer_id: number;
  date: string;
  is_available: boolean;
  time_start?: string;
  time_end?: string;
  notes?: string;
}

export async function getVolunteerSchedule(
  volunteerId: number,
  params?: { start_date?: string; end_date?: string }
): Promise<VolunteerSchedule[]> {
  return fetchApi(`/home-delivery/volunteers/${volunteerId}/schedule`, { params: params });
}

export async function createScheduleEntry(
  volunteerId: number,
  data: {
    date: string;
    is_available?: boolean;
    time_start?: string;
    time_end?: string;
    notes?: string;
  }
): Promise<VolunteerSchedule> {
  return fetchApi<VolunteerSchedule>(`/home-delivery/volunteers/${volunteerId}/schedule`, { method: 'POST', body: data });
}

export async function deleteScheduleEntry(
  volunteerId: number,
  scheduleDate: string
): Promise<void> {
  await fetchApi(`/home-delivery/volunteers/${volunteerId}/schedule/${scheduleDate}`, { method: 'DELETE' });
}

// ============================================================================
// Reports: Patron & Volunteer Reports
// ============================================================================

export interface HomeDeliveryPatronReport {
  patron_id: number;
  patron_name: string;
  patron_library_card: string;
  enrollment_id: number;
  enrollment_status: HomeDeliveryEnrollmentStatus;
  enrolled_at: string;
  total_deliveries: number;
  total_items_delivered: number;
  average_items_per_delivery: number;
  last_delivery_date?: string;
  next_scheduled_delivery?: string;
  average_rating?: number;
  assigned_volunteer_name?: string;
}

export async function getPatronReports(params?: {
  limit?: number;
  offset?: number;
}): Promise<HomeDeliveryPatronReport[]> {
  return fetchApi(`/home-delivery/reports/patrons`, { params: params });
}

export interface HomeDeliveryVolunteerReport {
  volunteer_id: number;
  volunteer_name: string;
  volunteer_status: VolunteerStatus;
  total_deliveries: number;
  total_hours: number;
  average_rating?: number;
  assigned_patrons_count: number;
  last_active_at?: string;
  recognition_level: string;
}

export async function getVolunteerReports(params?: {
  limit?: number;
  offset?: number;
}): Promise<HomeDeliveryVolunteerReport[]> {
  return fetchApi(`/home-delivery/reports/volunteers`, { params: params });
}

export interface HomeDeliveryDeliveryReport {
  period: string;
  total_deliveries: number;
  completed_deliveries: number;
  failed_deliveries: number;
  total_items_delivered: number;
  total_items_picked_up: number;
  average_items_per_delivery: number;
  average_rating?: number;
}

export async function getDeliveryReports(params?: {
  period_type?: 'week' | 'month';
  periods?: number;
}): Promise<HomeDeliveryDeliveryReport[]> {
  return fetchApi(`/home-delivery/reports/deliveries`, { params: params });
}

export interface HomeDeliveryFullReport {
  summary: HomeDeliveryReportSummary;
  patron_reports: HomeDeliveryPatronReport[];
  volunteer_reports: HomeDeliveryVolunteerReport[];
  delivery_reports: HomeDeliveryDeliveryReport[];
  generated_at: string;
}

export async function getFullReport(params?: {
  limit?: number;
}): Promise<HomeDeliveryFullReport> {
  return fetchApi(`/home-delivery/reports/full`, { params: params });
}

// ============================================================================
// Reports: Application Pipeline
// ============================================================================

export interface ApplicationPipelineStats {
  by_status: Record<string, number>;
  average_processing_days?: number;
  weekly_trend: {
    week: string;
    submitted: number;
    approved: number;
  }[];
}

export async function getApplicationPipeline(): Promise<ApplicationPipelineStats> {
  return fetchApi(`/home-delivery/reports/application-pipeline`);
}

// ============================================================================
// Reports: Analytics
// ============================================================================

export interface DeliveryAnalytics {
  period_start: string;
  period_end: string;
  total_deliveries: number;
  successful_deliveries: number;
  failed_deliveries: number;
  success_rate: number;
  average_items_per_delivery: number;
  average_rating?: number;
  total_items_delivered: number;
  total_items_picked_up: number;
  unique_patrons_served: number;
  deliveries_by_day: Record<string, number>;
  deliveries_by_status: Record<string, number>;
  ratings_distribution: Record<number, number>;
}

export async function getDeliveryAnalytics(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<DeliveryAnalytics> {
  return fetchApi(`/home-delivery/reports/analytics/deliveries`, { params: params });
}

export interface VolunteerAnalytics {
  period_start: string;
  period_end: string;
  total_active_volunteers: number;
  total_hours_logged: number;
  average_hours_per_volunteer: number;
  total_deliveries_made: number;
  average_deliveries_per_volunteer: number;
  top_volunteers: {
    volunteer_id: number;
    name: string;
    hours: number;
  }[];
  volunteers_by_status: Record<string, number>;
  hours_by_activity_type: Record<string, number>;
}

export async function getVolunteerAnalytics(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<VolunteerAnalytics> {
  return fetchApi(`/home-delivery/reports/analytics/volunteers`, { params: params });
}

export interface ServiceAnalytics {
  period_start: string;
  period_end: string;
  delivery_analytics: DeliveryAnalytics;
  volunteer_analytics: VolunteerAnalytics;
  patron_metrics: {
    active_patrons: number;
    paused_patrons: number;
    new_enrollments_in_period: number;
  };
  trends: {
    delivery_count_change_pct: number;
    period_length_days: number;
    compared_to_previous_period: string;
  };
}

export async function getServiceAnalytics(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<ServiceAnalytics> {
  return fetchApi(`/home-delivery/reports/analytics/service`, { params: params });
}

// ============================================================================
// Reports: Route Suggestions
// ============================================================================

export interface RouteSuggestion {
  cluster_id: number;
  delivery_ids: number[];
  estimated_distance_miles: number;
  estimated_duration_minutes: number;
  center_point?: { lat: number; lng: number };
  coverage_area: string;
}

export interface RouteSuggestionsResponse {
  date: string;
  suggestions: RouteSuggestion[];
  unassigned_delivery_count: number;
}

export async function getRouteSuggestions(params: {
  target_date: string;
}): Promise<RouteSuggestionsResponse> {
  return fetchApi(`/home-delivery/reports/route-suggestions`, { params: params });
}

// ============================================================================
// Reports: Data Export
// ============================================================================

export interface ExportRequest {
  report_type: 'deliveries' | 'patrons' | 'volunteers' | 'hours' | 'feedback';
  format: 'csv' | 'json' | 'xlsx';
  start_date?: string;
  end_date?: string;
  filters?: Record<string, unknown>;
}

export interface ExportResponse {
  export_id: string;
  status: 'processing' | 'completed' | 'failed';
  download_url?: string;
  file_name: string;
  record_count?: number;
  created_at: string;
  expires_at: string;
}

export async function requestExport(data: ExportRequest): Promise<ExportResponse> {
  return fetchApi<ExportResponse>(`/home-delivery/reports/export`, { method: 'POST', body: data });
}

export async function getExportStatus(exportId: string): Promise<ExportResponse> {
  return fetchApi(`/home-delivery/reports/export/${exportId}`);
}

export async function downloadExport(exportId: string): Promise<Blob> {
  // Note: The API client doesn't support responseType: 'blob', so this may need special handling
  return fetchApi(`/home-delivery/reports/export/${exportId}/download`);
}