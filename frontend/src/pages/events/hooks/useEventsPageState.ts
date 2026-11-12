/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import type { Event, EventFilters as Filters } from '@/api/api'
import type { ViewMode } from '@/pages/events/utils/eventsPageUtils'

export function useEventsPageState(seriesSlug?: string) {
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null)
  const [detailEvent, setDetailEvent] = useState<Event | null>(null)
  const [filters, setFilters] = useState<Filters>(() => (seriesSlug ? { series_id: seriesSlug } : {}))
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [showPastEvents, setShowPastEvents] = useState(false)
  const [showPrintModal, setShowPrintModal] = useState(false)
  const [showPreferencesModal, setShowPreferencesModal] = useState(false)
  const [selectedDate, setSelectedDate] = useState<Date | null>(null)
  const [showMiniCalendar, setShowMiniCalendar] = useState(false)

  useEffect(() => {
    if (seriesSlug) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing user-mutable filters to the seriesSlug prop on change
      setFilters(prev => ({ ...prev, series_id: seriesSlug }))
    } else {
      setFilters(prev => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { series_id: _series_id, ...rest } = prev
        return rest
      })
    }
  }, [seriesSlug])

  return {
    selectedEvent, setSelectedEvent,
    detailEvent, setDetailEvent,
    filters, setFilters,
    viewMode, setViewMode,
    showPastEvents, setShowPastEvents,
    showPrintModal, setShowPrintModal,
    showPreferencesModal, setShowPreferencesModal,
    selectedDate, setSelectedDate,
    showMiniCalendar, setShowMiniCalendar,
  }
}
