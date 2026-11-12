/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Mock Helpers for Testing
 *
 * Provides utilities for creating mock data, API responses, and common test scenarios
 */

import { vi } from 'vitest'
import { QueryClient } from '@tanstack/react-query'
import type { User } from '@/api/auth-api'
import type { AgeGroupLimits } from '@/api/organization-features-api'

// ==================== Mock User Data ====================

export const mockUser: User = {
  id: 1,
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  pronouns: null,
  library_card: 'LSC000001',
  role: 'patron' as const,
  is_active: true,
  phone: null,
  address: null,
  email_verified: true,
  track_reading_history: true,
  created_at: '2024-01-01T00:00:00Z',
  onboarding_completed_at: null,
  onboarding_skipped: false,
  home_branch_id: null,
}

export const mockAdminUser = {
  ...mockUser,
  id: 2,
  email: 'admin@example.com',
  role: 'admin' as const,
}

export const mockStaffUser = {
  ...mockUser,
  id: 3,
  email: 'staff@example.com',
  role: 'staff' as const,
}

// ==================== Mock Catalog Items ====================

export const mockCatalogItem = {
  id: 1,
  title: 'Test Book',
  author: 'Test Author',
  isbn: '9781234567890',
  item_type: 'book',
  status: 'available',
  description: 'A test book for testing',
  cover_url: 'https://example.com/cover.jpg',
  page_count: 300,
  publication_year: 2024,
  created_at: '2024-01-01T00:00:00Z',
}

export const mockAudiobook = {
  ...mockCatalogItem,
  id: 2,
  title: 'Test Audiobook',
  item_type: 'audiobook',
}

export const mockDVD = {
  ...mockCatalogItem,
  id: 3,
  title: 'Test Movie',
  item_type: 'dvd',
  page_count: null,
}

// ==================== Mock Organization Features ====================

export const mockOrganizationFeatures = {
  id: 1,
  gamification_enabled: true,
  reading_programs_enabled: true,
  board_features_enabled: true,
  training_modules_enabled: true,
  community_features_enabled: true,
  email_notifications_enabled: true,
  banned_books_tracking_enabled: true,
  patron_portal_enabled: true,
  self_checkout_enabled: true,
  acquisition_enabled: true,
  indie_platform_enabled: true,
  learning_platform_enabled: true,
  for_teachers_enabled: true,
  home_delivery_enabled: true,
  ai_tools_enabled: true,
  makerspace_enabled: true,
  meeting_rooms_enabled: true,
  events_enabled: true,
  ill_enabled: true,
  genealogy_enabled: true,
  free_ebooks_enabled: true,
  outreach_enabled: true,
  ama_enabled: false,
  reading_shelf_enabled: true,
  reading_goals_enabled: false,
  shelf_data_export_enabled: true,
  saved_searches_enabled: false,
  reading_programs_booklist_enabled: false,
  reading_programs_paper_log_enabled: false,
  circulation_print_slip_enabled: true,
  circulation_hold_trap_card_enabled: true,
  customer_display_enabled: false,
  book_club_history_enabled: false,
  book_club_waitlist_enabled: false,
  community_outcomes_enabled: true,
  impact_measurement_enabled: false,
  home_visit_safety_enabled: false,
  home_visit_day_plan_enabled: false,
  family_card_enabled: true,
  front_desk_enabled: true,
  migration_enabled: true,
  legal_services_enabled: true,
  strategic_planning_enabled: true,
  literacy_programs_enabled: true,
  tech_services_enabled: true,
  emergency_services_enabled: true,
  compliance_enabled: true,
  volunteers_enabled: true,
  notifications_enabled: true,
  marketing_enabled: true,
  streaming_enabled: true,
  staff_scheduling_enabled: true,
  beta_features_enabled: false,
  storytime_enabled: true,
  digital_access_enabled: true,
  collection_management_enabled: true,
  patron_engagement_enabled: true,
  staff_wellness_enabled: true,
  faq_chatbot_enabled: true,
  financial_reports_enabled: true,
  book_clubs_enabled: true,
  sip2_rfid_enabled: true,
  signage_enabled: true,
  printing_enabled: true,
  processing_queue_enabled: true,
  parent_onboarding_enabled: true,
  serials_enabled: true,
  pickup_authorization_enabled: false,
  cohort_enabled: false,
  aggregate_trending_enabled: true,
  enabled_focus_modes: ['deep_dive', 'pomodoro'] as string[],
  enabled_themes: ['light', 'dark', 'forest'] as string[],
  enabled_fonts: ['dyslexic', 'opendyslexic'] as string[],
  default_daily_goal_minutes: 30,
  max_holds_per_patron: 10,
  max_checkouts_per_patron: 5,
  configuration: null as Record<string, unknown> | null,
  age_group_limits: null as AgeGroupLimits | null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: null as string | null,
  updated_by_id: null as number | null,
}

// ==================== Mock Auth Responses ====================

export const mockLoginResponse = {
  access_token: 'mock-access-token',
  token_type: 'bearer',
}

export const mockRefreshResponse = {
  access_token: 'mock-refreshed-token',
  token_type: 'bearer',
}

// ==================== Mock API Functions ====================

export function createMockFetch(responses: Record<string, unknown> = {}) {
  return vi.fn((url: string, options?: RequestInit) => {
    const method = options?.method || 'GET'
    const key = `${method} ${url}`

    const response = responses[key] || responses[url]

    if (response instanceof Error) {
      return Promise.reject(response)
    }

    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(response),
      headers: new Headers(),
    } as Response)
  })
}

export function createMockFailedFetch(status = 500, message = 'Server error') {
  return vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      json: () => Promise.resolve({ detail: message }),
      headers: new Headers(),
    } as Response)
  )
}

// ==================== Timer Mocks ====================

export function setupTimerMocks() {
  vi.useFakeTimers()
  return {
    advanceTimersByTime: (ms: number) => vi.advanceTimersByTime(ms),
    runAllTimers: () => vi.runAllTimers(),
    cleanup: () => vi.useRealTimers(),
  }
}

// ==================== LocalStorage Mocks ====================

export function createMockLocalStorage() {
  const store: Record<string, string> = {}

  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      Object.keys(store).forEach(key => delete store[key])
    }),
    get store() {
      return { ...store }
    },
  }
}

// ==================== Speech Synthesis Mocks ====================

export function createMockSpeechSynthesis() {
  const utterances: SpeechSynthesisUtterance[] = []

  return {
    speak: vi.fn((utterance: SpeechSynthesisUtterance) => {
      utterances.push(utterance)
      // Simulate speaking completion after a short delay
      setTimeout(() => utterance.onend?.(new Event('end') as SpeechSynthesisEvent), 10)
    }),
    cancel: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    getUtterances: () => [...utterances],
  }
}

// ==================== Query Client Helpers ====================

export function createMockQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

// ==================== Wait Helpers ====================

export function waitFor(callback: () => void | boolean, timeout = 1000): Promise<void> {
  return new Promise((resolve, reject) => {
    const startTime = Date.now()

    const check = () => {
      try {
        const result = callback()
        if (result !== false) {
          resolve()
          return
        }
      } catch (error: unknown) {
        if (Date.now() - startTime >= timeout) {
          reject(error)
          return
        }
      }

      setTimeout(check, 50)
    }

    check()
  })
}

// ==================== Form Helpers ====================

export function fillForm(form: HTMLFormElement, values: Record<string, string>) {
  Object.entries(values).forEach(([name, value]) => {
    const input = form.elements.namedItem(name) as HTMLInputElement
    if (input) {
      input.value = value
      input.dispatchEvent(new Event('input', { bubbles: true }))
      input.dispatchEvent(new Event('change', { bubbles: true }))
    }
  })
}

// ==================== Accessibility Helpers ====================

export function checkAccessibility(element: HTMLElement) {
  // Check for basic accessibility requirements
  const checks = {
    hasAriaLabel: !!element.getAttribute('aria-label'),
    hasAriaLabelledBy: !!element.getAttribute('aria-labelledby'),
    hasRole: !!element.getAttribute('role'),
    hasTabIndex: element.getAttribute('tabindex') !== null,
  }

  return checks
}

// ==================== Mock Events ====================

export const mockEvent = {
  id: 1,
  title: 'Test Event',
  description: 'A test event',
  event_type: 'workshop',
  start_time: '2024-12-01T10:00:00Z',
  end_time: '2024-12-01T12:00:00Z',
  location: 'Main Library',
  capacity: 20,
  registration_required: true,
  created_at: '2024-01-01T00:00:00Z',
}

// ==================== Mock Reading Program ====================

export const mockReadingProgram = {
  id: 1,
  title: 'Summer Reading',
  description: 'Annual summer reading program',
  start_date: '2024-06-01',
  end_date: '2024-08-31',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
}

// ==================== Mock Indie Ebook ====================

export const mockIndieEbook = {
  id: 1,
  title: 'My Indie Book',
  description: 'An indie ebook',
  genre: 'Fiction',
  content_rating: 'general' as const,
  submission_status: 'draft' as const,
  author_id: 1,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: null,
}
