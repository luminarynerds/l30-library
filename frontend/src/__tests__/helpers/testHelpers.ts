/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Global Test Helpers
 *
 * Provides factory functions and utilities for creating test fixtures
 * to ensure type consistency across all test files.
 */

import type { Event } from '@/api/events-api'
import type { Patron } from '@/api/staff-api'
import type {
  LostItem,
  DamagedItem,
  MendingQueueItem,
} from '@/components/staff/BulkItemOperations'

// ==================== Event Factories ====================

export function createMockEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 1,
    title: 'Test Event',
    description: 'Test event description',
    start_time: '2024-01-15T10:00:00Z',
    end_time: '2024-01-15T12:00:00Z',
    location: 'Main Library',
    is_virtual: false,
    audience: 'adults',
    category: 'workshop',
    tags: ['technology', 'learning'],
    max_attendees: 50,
    registration_required: true,
    registration_count: 10,
    spots_remaining: 40,
    image_url: 'https://example.com/event.jpg',
    is_featured: false,
    series_id: null,
    series_name: null,
    created_at: '2024-01-01T00:00:00Z',
    average_rating: 4.5,
    review_count: 12,
    ...overrides,
  }
}

export function createMockEvents(count: number, overrides: Partial<Event> = {}): Event[] {
  return Array.from({ length: count }, (_, index) =>
    createMockEvent({
      id: index + 1,
      title: `Test Event ${index + 1}`,
      ...overrides,
    })
  )
}

// ==================== Patron Factories ====================

export function createMockPatron(overrides: Partial<Patron> = {}): Patron {
  return {
    id: 1,
    email: 'patron@example.com',
    first_name: 'John',
    last_name: 'Doe',
    role: 'patron',
    is_active: true,
    library_card: 'LC001',
    phone: '555-0100',
    address: '123 Main St',
    created_at: '2024-01-01T00:00:00Z',
    fines_balance: 0,
    total_checkouts: 10,
    current_checkouts: 2,
    current_holds: 1,
    patron_status: 'active',
    suspension_reason: null,
    suspended_until: null,
    suspended_at: null,
    block_reason: null,
    blocked_at: null,
    date_of_death: null,
    estate_contact_name: null,
    estate_followup_required: false,
    ...overrides,
  }
}

export function createMockPatrons(count: number, overrides: Partial<Patron> = {}): Patron[] {
  return Array.from({ length: count }, (_, index) =>
    createMockPatron({
      id: index + 1,
      email: `patron${index + 1}@example.com`,
      first_name: `FirstName${index + 1}`,
      last_name: `LastName${index + 1}`,
      library_card: `LC${String(index + 1).padStart(3, '0')}`,
      ...overrides,
    })
  )
}

// ==================== Item Factories ====================

export function createMockLostItem(overrides: Partial<LostItem> = {}): LostItem {
  return {
    id: 1,
    checkout_id: 100,
    item_copy_id: 50,
    catalog_item_id: 25,
    patron_id: 10,
    status: 'lost',
    lost_type: 'patron_declared_lost',
    replacement_cost: 29.99,
    item_title: 'Test Book',
    patron_name: 'John Doe',
    ...overrides,
  }
}

export function createMockLostItems(count: number, overrides: Partial<LostItem> = {}): LostItem[] {
  return Array.from({ length: count }, (_, index) =>
    createMockLostItem({
      id: index + 1,
      checkout_id: 100 + index,
      item_copy_id: 50 + index,
      catalog_item_id: 25 + index,
      item_title: `Test Book ${index + 1}`,
      ...overrides,
    })
  )
}

export function createMockDamagedItem(overrides: Partial<DamagedItem> = {}): DamagedItem {
  return {
    id: 1,
    item_copy_id: 50,
    catalog_item_id: 25,
    patron_id: 10,
    status: 'damaged',
    severity: 'moderate',
    damage_types: ['torn_pages', 'water_damage'],
    estimated_repair_cost: 15.0,
    item_title: 'Test Book',
    patron_name: 'John Doe',
    ...overrides,
  }
}

export function createMockDamagedItems(
  count: number,
  overrides: Partial<DamagedItem> = {}
): DamagedItem[] {
  return Array.from({ length: count }, (_, index) =>
    createMockDamagedItem({
      id: index + 1,
      item_copy_id: 50 + index,
      catalog_item_id: 25 + index,
      item_title: `Test Book ${index + 1}`,
      ...overrides,
    })
  )
}

export function createMockMendingQueueItem(
  overrides: Partial<MendingQueueItem> = {}
): MendingQueueItem {
  return {
    id: 1,
    damaged_item_record_id: 10,
    item_copy_id: 50,
    priority: 2,
    repair_type: 'rebinding',
    is_in_progress: false,
    is_completed: false,
    item_title: 'Test Book',
    assigned_to_name: 'Staff Member',
    ...overrides,
  }
}

export function createMockMendingQueueItems(
  count: number,
  overrides: Partial<MendingQueueItem> = {}
): MendingQueueItem[] {
  return Array.from({ length: count }, (_, index) =>
    createMockMendingQueueItem({
      id: index + 1,
      damaged_item_record_id: 10 + index,
      item_copy_id: 50 + index,
      item_title: `Test Book ${index + 1}`,
      ...overrides,
    })
  )
}

// ==================== Common Test Utilities ====================

export function createMockToken(): string {
  return 'mock-test-token-12345'
}

export function createMockCallback<T extends (...args: unknown[]) => unknown>(): T {
  // @ts-expect-error - vitest global
  return vi.fn() as T
}

export function waitForAsync(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

export function createMockHTMLElement(
  tagName: string = 'div',
  overrides: Partial<HTMLElement> = {}
): HTMLElement {
  const element = document.createElement(tagName)
  Object.assign(element, overrides)
  return element
}

// ==================== Staff Member Factories ====================

export function createMockStaffMembers(
  count: number
): Array<{ id: number; name: string }> {
  return Array.from({ length: count }, (_, index) => ({
    id: index + 1,
    name: `Staff Member ${index + 1}`,
  }))
}

// ==================== Type Guards ====================

export function isLostItem(item: unknown): item is LostItem {
  return item !== null && typeof item === 'object' && 'lost_type' in item
}

export function isDamagedItem(item: unknown): item is DamagedItem {
  return item !== null && typeof item === 'object' && 'severity' in item && 'damage_types' in item
}

export function isMendingQueueItem(item: unknown): item is MendingQueueItem {
  return item !== null && typeof item === 'object' && 'priority' in item && 'repair_type' in item
}
