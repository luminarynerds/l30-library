/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  Clock, Loader, Globe,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'

interface TimelineEvent {
  id: number;
  event_type: string;
  event_date?: string;
  title: string;
  location?: string;
  person_name?: string;
}


export default function TimelineTab({ projectId }: { projectId: number }) {
  const { t } = useTranslation();
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [loading, setLoading] = useState(true)

  async function loadTimeline() {
    try {
      setLoading(true)
      const { personsApi } = await import('@/api/genealogy-research-api')
      const persons = await personsApi.list(projectId)
      // Load timelines for all persons
      const allEvents: TimelineEvent[] = []
      for (const person of persons.slice(0, 20)) {
        try {
          const timeline = await personsApi.getTimeline(projectId, person.id)
          if (timeline.events) {
            allEvents.push(...(timeline.events as TimelineEvent[]).map((e) => ({
              ...e,
              person_name: `${person.given_names} ${person.surname || ''}`.trim(),
            })))
          }
        } catch {
          // Skip persons without timeline events
        }
      }
      allEvents.sort((a, b) => (a.event_date || '').localeCompare(b.event_date || ''))
      setEvents(allEvents)
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToLoadTimeline'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    loadTimeline()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const eventTypeColors: Record<string, string> = {
    birth: 'bg-status-success-500',
    death: 'bg-earth-500',
    marriage: 'bg-pink-500',
    immigration: 'bg-earth-500',
    military_service: 'bg-status-danger-500',
    education: 'bg-category-500',
    occupation: 'bg-status-warning-500',
    residence: 'bg-teal-500',
  }

  if (loading) {
    return <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin" /></div>
  }

  return (
    <div className="space-y-4">
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Family Timeline</h2>
      {events.length === 0 ? (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <Clock className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyResearchPageContent.noTimelineEventsYetAdd')}</p>
        </div>
      ) : (
        <div className="relative">
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-earth-200 dark:bg-earth-700" />
          <div className="space-y-6">
            {events.map((event, i) => (
              <div key={`${event.id}-${i}`} className="relative flex gap-4 pl-4">
                <div className={`w-5 h-5 rounded-full ${eventTypeColors[event.event_type] || 'bg-earth-400'} flex-shrink-0 z-10 ring-4 ring-white dark:ring-earth-900`} />
                <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-status-warning-600 dark:text-status-warning-400">
                      {event.event_date || 'Unknown date'}
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-earth-100 dark:bg-earth-700 rounded-full text-lsc-dark/70 dark:text-lsc-cream/70">
                      {event.event_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{event.title}</p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{event.person_name}</p>
                  {event.location && (
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 flex items-center gap-1">
                      <Globe className="w-3 h-3" /> {event.location}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
