/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export type ComputerType = "kids" | "teen" | "adult" | "accessible";
export type ComputerStatus = "available" | "in_use" | "maintenance" | "offline" | "reserved";
export type ReservationStatus = "pending" | "confirmed" | "in_session" | "completed" | "cancelled" | "no_show" | "extended";
export type WaitlistStatus = "pending" | "notified" | "expired" | "fulfilled";
export type ExtensionStatus = "pending" | "approved" | "denied" | "expired";

export interface Computer {
  id: number;
  name: string;
  computer_number: string;
  description?: string;
  branch_id?: number;
  branch_name?: string;
  location?: string;
  computer_type: ComputerType;
  os_type?: string;
  os_version?: string;
  processor?: string;
  ram_gb?: number;
  storage_gb?: number;
  installed_software?: string[];
  has_internet: boolean;
  internet_type?: string;
  has_screen_reader: boolean;
  has_magnifier: boolean;
  has_keyboard_options: boolean;
  accessibility_features?: string[];
  has_print_release: boolean;
  max_session_minutes: number;
  is_extendable: boolean;
  max_extension_minutes: number;
  status: ComputerStatus;
  is_active: boolean;
  image_url?: string;
  created_at: string;
  updated_at: string;
}

export interface ComputerReservation {
  id: number;
  computer_id: number;
  patron_id?: number;
  reserved_start_time: string;
  reserved_end_time: string;
  status: ReservationStatus;
  session_duration_minutes: number;
  is_guest_pass: boolean;
  guest_pass_code?: string;
  guest_name?: string;
  guest_email?: string;
  guest_phone?: string;
  checked_in_at?: string;
  actual_start_time?: string;
  actual_end_time?: string;
  extension_requested: boolean;
  extended_until?: string;
  extensions_used: number;
  cancelled_at?: string;
  cancellation_reason?: string;
  five_min_warning_sent_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ComputerSession {
  id: number;
  reservation_id: number;
  computer_id: number;
  patron_id?: number;
  session_start_time: string;
  session_end_time: string;
  actual_end_time?: string;
  is_active: boolean;
  was_extended: boolean;
  extension_count: number;
  warning_sent_at?: string;
  auto_logout_at?: string;
  user_initiated_logout: boolean;
  auto_logout_executed: boolean;
  logoff_reason?: string;
  print_jobs_count: number;
  created_at: string;
  updated_at: string;
}

export interface GuestPass {
  id: number;
  guest_name: string;
  guest_email?: string;
  guest_phone?: string;
  pass_code: string;
  max_sessions: number;
  sessions_used: number;
  max_duration_minutes_per_session: number;
  issued_at: string;
  valid_until: string;
  is_active: boolean;
  allowed_computer_types?: string[];
  first_used_at?: string;
  last_used_at?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ComputerWaitlist {
  id: number;
  computer_id: number;
  patron_id?: number;
  is_guest: boolean;
  guest_phone?: string;
  desired_start_time: string;
  desired_duration_minutes: number;
  status: WaitlistStatus;
  queue_position: number;
  notified_at?: string;
  notification_method?: string;
  created_at: string;
  expires_at: string;
}

export interface SessionExtensionRequest {
  id: number;
  reservation_id: number;
  session_id: number;
  extension_minutes: number;
  status: ExtensionStatus;
  requested_at: string;
  approved_at?: string;
  approved_by?: number;
  denial_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface ComputerUsageStats {
  id: number;
  computer_id: number;
  date: string;
  total_reservations: number;
  completed_sessions: number;
  cancelled_reservations: number;
  no_show_count: number;
  total_minutes_used: number;
  total_extension_minutes: number;
  guest_sessions: number;
  cardholders_sessions: number;
  extension_requests: number;
  extension_requests_granted: number;
  extension_requests_denied: number;
  hourly_usage?: Record<string, number>;
  downtime_minutes: number;
  maintenance_events: number;
  print_jobs_count: number;
}
