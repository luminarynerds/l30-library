/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Lifecycle Types ====================

export type LifecycleEventType =
  | 'selected' | 'selection_approved' | 'patron_requested'
  | 'ordered' | 'received'
  | 'cataloging_started' | 'cataloged'
  | 'copy_created' | 'shelved'
  | 'checked_out' | 'returned' | 'renewed' | 'hold_placed' | 'hold_filled'
  | 'condition_changed' | 'damaged' | 'repaired'
  | 'inventoried' | 'missing' | 'found'
  | 'marked_for_weeding' | 'weeding_approved' | 'weeding_rejected' | 'weeded' | 'disposed'
  | 'location_changed' | 'transferred'
  | 'note_added' | 'other'

export interface LifecycleEvent {
  id: number
  item_copy_id: number
  event_type: LifecycleEventType
  description: string | null
  metadata: Record<string, unknown>
  performed_by_id: number | null
  related_checkout_id: number | null
  related_po_id: number | null
  related_audit_id: number | null
  related_weeding_id: number | null
  created_at: string
  performed_by_name: string | null
  performed_by_email: string | null
  item_copy_barcode: string | null
  item_title: string | null
  item_author: string | null
}

export interface LifecycleTimeline {
  item_copy_id: number
  item_copy_barcode: string | null
  item_title: string | null
  item_author: string | null
  events: LifecycleEvent[]
  total_events: number
}

export interface LifecycleEventCreate {
  item_copy_id: number
  event_type: LifecycleEventType
  description?: string | null
  metadata?: Record<string, unknown>
  related_checkout_id?: number | null
  related_po_id?: number | null
  related_audit_id?: number | null
  related_weeding_id?: number | null
}

// Lifecycle stage groupings for UI display
export const LIFECYCLE_STAGES = {
  selection: {
    label: 'Selection',
    description: 'Identifying and selecting materials for the collection',
    color: 'teal',
    events: ['selected', 'selection_approved', 'patron_requested'] as LifecycleEventType[],
  },
  acquisition: {
    label: 'Acquisition',
    description: 'Item ordering and receiving',
    color: 'blue',
    events: ['ordered', 'received'] as LifecycleEventType[],
  },
  cataloging: {
    label: 'Cataloging',
    description: 'Item cataloging and processing',
    color: 'purple',
    events: ['cataloging_started', 'cataloged', 'copy_created', 'shelved'] as LifecycleEventType[],
  },
  circulation: {
    label: 'Circulation',
    description: 'Active circulation events',
    color: 'green',
    events: ['checked_out', 'returned', 'renewed', 'hold_placed', 'hold_filled'] as LifecycleEventType[],
  },
  condition: {
    label: 'Condition',
    description: 'Item condition changes',
    color: 'orange',
    events: ['condition_changed', 'damaged', 'repaired'] as LifecycleEventType[],
  },
  inventory: {
    label: 'Inventory',
    description: 'Inventory tracking events',
    color: 'indigo',
    events: ['inventoried', 'missing', 'found'] as LifecycleEventType[],
  },
  weeding: {
    label: 'Weeding',
    description: 'Weeding and disposal',
    color: 'red',
    events: ['marked_for_weeding', 'weeding_approved', 'weeding_rejected', 'weeded', 'disposed'] as LifecycleEventType[],
  },
  location: {
    label: 'Location',
    description: 'Location and transfer changes',
    color: 'gray',
    events: ['location_changed', 'transferred'] as LifecycleEventType[],
  },
  other: {
    label: 'Other',
    description: 'Notes and other events',
    color: 'slate',
    events: ['note_added', 'other'] as LifecycleEventType[],
  },
} as const

export type LifecycleStage = keyof typeof LIFECYCLE_STAGES

// Event type labels for display
export const LIFECYCLE_EVENT_LABELS: Record<LifecycleEventType, string> = {
  selected: 'Added to Selection List',
  selection_approved: 'Selection Approved',
  patron_requested: 'Patron Requested',
  ordered: 'Ordered',
  received: 'Received',
  cataloging_started: 'Cataloging Started',
  cataloged: 'Cataloged',
  copy_created: 'Copy Created',
  shelved: 'Shelved',
  checked_out: 'Checked Out',
  returned: 'Returned',
  renewed: 'Renewed',
  hold_placed: 'Hold Placed',
  hold_filled: 'Hold Filled',
  condition_changed: 'Condition Changed',
  damaged: 'Damaged',
  repaired: 'Repaired',
  inventoried: 'Inventoried',
  missing: 'Missing',
  found: 'Found',
  marked_for_weeding: 'Marked for Weeding',
  weeding_approved: 'Weeding Approved',
  weeding_rejected: 'Weeding Rejected',
  weeded: 'Weeded',
  disposed: 'Disposed',
  location_changed: 'Location Changed',
  transferred: 'Transferred',
  note_added: 'Note Added',
  other: 'Other',
}

export interface LifecycleSearchResult {
  copy_id: number
  barcode: string | null
  condition: string | null
  catalog_item_id: number
  title: string
  author: string | null
  isbn: string | null
  call_number: string | null
}

// ==================== Lifecycle Functions ====================

export async function searchItemsForLifecycle(token: string, query: string): Promise<LifecycleSearchResult[]> {
  try {
    return await fetchApi<LifecycleSearchResult[]>(`/lifecycle/search?q=${encodeURIComponent(query)}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Search failed')
    }
    throw error
  }
}

export async function getItemCopyLifecycle(token: string, copyId: number): Promise<LifecycleTimeline> {
  try {
    return await fetchApi<LifecycleTimeline>(`/lifecycle/item-copy/${copyId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch lifecycle')
    }
    throw error
  }
}

export async function getCatalogItemLifecycle(token: string, itemId: number): Promise<LifecycleTimeline[]> {
  try {
    return await fetchApi<LifecycleTimeline[]>(`/lifecycle/item/${itemId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch lifecycle')
    }
    throw error
  }
}

export async function createLifecycleEvent(
  token: string,
  eventData: LifecycleEventCreate
): Promise<LifecycleEvent> {
  try {
    return await fetchApi<LifecycleEvent>('/lifecycle/events', {
      token,
      method: 'POST',
      body: JSON.stringify(eventData),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create lifecycle event')
    }
    throw error
  }
}

export function filterEventsByType(
  events: LifecycleEvent[],
  eventTypes: LifecycleEventType[]
): LifecycleEvent[] {
  return events.filter(event => eventTypes.includes(event.event_type))
}

export function filterEventsByStage(
  events: LifecycleEvent[],
  stage: LifecycleStage
): LifecycleEvent[] {
  const stageEvents = LIFECYCLE_STAGES[stage].events
  return events.filter(event => stageEvents.includes(event.event_type))
}

export function getCurrentStage(events: LifecycleEvent[]): LifecycleStage | null {
  if (!events || events.length === 0) return null

  // Sort by created_at descending to get most recent
  const sortedEvents = [...events].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )

  const mostRecentEvent = sortedEvents[0]!

  // Find which stage this event belongs to
  for (const [stage, stageInfo] of Object.entries(LIFECYCLE_STAGES)) {
    if (stageInfo.events.includes(mostRecentEvent.event_type)) {
      return stage as LifecycleStage
    }
  }

  return 'other'
}

export function getLifecycleStats(timeline: LifecycleTimeline) {
  const events = timeline.events
  const stats: Record<LifecycleStage, number> = {
    selection: 0,
    acquisition: 0,
    cataloging: 0,
    circulation: 0,
    condition: 0,
    inventory: 0,
    weeding: 0,
    location: 0,
    other: 0,
  }

  for (const event of events) {
    for (const [stage, stageInfo] of Object.entries(LIFECYCLE_STAGES)) {
      if (stageInfo.events.includes(event.event_type)) {
        stats[stage as LifecycleStage]++
        break
      }
    }
  }

  return stats
}

export function formatEventType(eventType: LifecycleEventType): string {
  return LIFECYCLE_EVENT_LABELS[eventType] || eventType
}

export function getStageForEventType(eventType: LifecycleEventType): LifecycleStage {
  for (const [stage, stageInfo] of Object.entries(LIFECYCLE_STAGES)) {
    if (stageInfo.events.includes(eventType)) {
      return stage as LifecycleStage
    }
  }
  return 'other'
}

// ==================== Alert Detection ====================

// Alert thresholds
export const ALERT_STUCK_CONDITION_DAYS = 30
export const ALERT_STUCK_ACQUISITION_DAYS = 60
export const ALERT_OVERDUE_CHECK_DAYS = 180
export const ALERT_OVERDUE_CHECK_MIN_CIRC = 5
export const ALERT_LONG_MISSING_DAYS = 90

export interface LifecycleAlert {
  type: 'stuck_stage' | 'overdue_check' | 'long_missing'
  stage: LifecycleStage
  message: string
  since: string
}

function daysSince(dateStr: string): number {
  const then = new Date(dateStr)
  const now = new Date()
  return Math.floor((now.getTime() - then.getTime()) / (1000 * 60 * 60 * 24))
}

export function getLifecycleAlerts(timeline: LifecycleTimeline): LifecycleAlert[] {
  const alerts: LifecycleAlert[] = []
  const events = timeline.events

  if (!events || events.length === 0) return alerts

  // stuck_stage: check if most recent event's stage has been idle too long
  const sorted = [...events].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
  const mostRecent = sorted[0]
  if (!mostRecent) return alerts
  const currentStage = getStageForEventType(mostRecent.event_type)
  const age = daysSince(mostRecent.created_at)

  if (currentStage === 'condition' && age > ALERT_STUCK_CONDITION_DAYS) {
    alerts.push({
      type: 'stuck_stage',
      stage: 'condition',
      message: `Item stuck in condition stage for ${age} days`,
      since: mostRecent.created_at,
    })
  } else if (currentStage === 'acquisition' && age > ALERT_STUCK_ACQUISITION_DAYS) {
    alerts.push({
      type: 'stuck_stage',
      stage: 'acquisition',
      message: `Item stuck in acquisition stage for ${age} days`,
      since: mostRecent.created_at,
    })
  }

  // overdue_check: high-circulation items without recent condition check
  const circEvents = filterEventsByStage(events, 'circulation')
  if (circEvents.length >= ALERT_OVERDUE_CHECK_MIN_CIRC) {
    const conditionEvents = filterEventsByStage(events, 'condition')
    const sortedCondition = [...conditionEvents].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
    const lastCondition = sortedCondition[0]

    if (!lastCondition || daysSince(lastCondition.created_at) > ALERT_OVERDUE_CHECK_DAYS) {
      const oldest = sorted[sorted.length - 1]
      const sinceDate = lastCondition
        ? lastCondition.created_at
        : oldest?.created_at ?? mostRecent.created_at
      alerts.push({
        type: 'overdue_check',
        stage: 'condition',
        message: lastCondition
          ? `No condition check in ${daysSince(lastCondition.created_at)} days with ${circEvents.length} circulations`
          : `Never checked condition despite ${circEvents.length} circulations`,
        since: sinceDate,
      })
    }
  }

  // long_missing: item reported missing with no subsequent found event
  const missingEvents = filterEventsByType(events, ['missing'])
  if (missingEvents.length > 0) {
    const sortedMissing = [...missingEvents].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
    const lastMissing = sortedMissing[0]
    if (lastMissing) {
      const foundEvents = filterEventsByType(events, ['found'])
      const hasFoundAfter = foundEvents.some(
        (f) => new Date(f.created_at).getTime() > new Date(lastMissing.created_at).getTime()
      )

      if (!hasFoundAfter && daysSince(lastMissing.created_at) > ALERT_LONG_MISSING_DAYS) {
        alerts.push({
          type: 'long_missing',
          stage: 'inventory',
          message: `Item missing for ${daysSince(lastMissing.created_at)} days`,
          since: lastMissing.created_at,
        })
      }
    }
  }

  return alerts
}

// ==================== Batch API ====================

export interface BatchEventItem {
  item_copy_id: number
}

export interface BatchResultItem {
  item_copy_id: number
  status: 'success' | 'error'
  event_id?: number
  message?: string
}

export interface BatchEventResponse {
  results: BatchResultItem[]
  total_processed: number
  total_success: number
  total_errors: number
}

export async function createBatchLifecycleEvents(
  token: string,
  data: { event_type: LifecycleEventType; description?: string | null; items: BatchEventItem[] }
): Promise<BatchEventResponse> {
  try {
    return await fetchApi<BatchEventResponse>('/lifecycle/events/batch', {
      token,
      method: 'POST',
      body: JSON.stringify(data),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Batch event creation failed')
    }
    throw error
  }
}
