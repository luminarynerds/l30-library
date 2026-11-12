/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Calendar,
  MapPin,
  Users,
  Download,
  UserPlus,
  Star,
  Sparkles,
  Tag,
  AlertTriangle,
  MessageSquare,
  Clock,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  Accessibility,
  ChevronLeft,
  Hand,
  CheckCircle,
} from 'lucide-react'
import { fetchApi } from '@/lib/api-client'
import { getRelatedEvents, type Event } from '@/api/api'
import { getCategoryColorClasses, getCategoryHeaderGradient, getCategoryDisplayName } from '@/pages/events/utils/eventCategoryColors'
import { getCapacityUrgency as getCapacityUrgencyShared } from '@/pages/events/utils/eventsPageUtils'
import { useTranslation } from '@/i18n/I18nContext'
import { usePageMeta } from '@/hooks/usePageMeta'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import ShareButton from '@/components/ShareButton'
import EventReviewForm from '@/components/EventReviewForm'
import RegistrationModal from '@/components/RegistrationModal'
import { generateGoogleCalendarUrl, generateOutlookCalendarUrl } from '@/utils/calendarExport'
import { useBranding } from '@/contexts/BrandingContext'
import { useAuth } from '@/contexts/AuthContext'
import { getMyEventRegistrations, type MyEventRegistration } from '@/services/api'
import PageContainer from '@/components/layout/PageContainer'

async function getEventById(eventId: number): Promise<Event> {
  return fetchApi<Event>(`/events/${eventId}`)
}

function formatDate(dateStr: string, locale = 'en'): string {
  return new Date(dateStr).toLocaleDateString(locale, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function formatTime(dateStr: string, locale = 'en'): string {
  return new Date(dateStr).toLocaleTimeString(locale, {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function truncateDescription(text: string | null, maxLen = 160, fallback = 'Event at this library'): string {
  if (!text) return fallback
  if (text.length <= maxLen) return text
  return text.slice(0, maxLen - 3) + '...'
}

function buildGoogleMapsUrl(location: string): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(location)}`
}

function RelatedEventsSection({ eventId }: { eventId: number }) {
  const { t, language } = useTranslation()
  const { data, isLoading } = useQuery({
    queryKey: ['related-events', eventId],
    queryFn: () => getRelatedEvents(eventId, 3),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <section aria-label={t('events.detail.loadingRelatedEvents')}>
        <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Star className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          {t('events.detail.youMayAlsoLike')}
        </h2>
        <div className="space-y-3" aria-hidden="true">
          {[1, 2, 3].map((i) => (
            <div key={i} className="motion-safe:animate-pulse flex gap-3 p-3 bg-lsc-cream/50 dark:bg-earth-800/50 rounded-xl">
              <div className="w-12 h-12 bg-lsc-border dark:bg-earth-700 rounded-lg" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-lsc-border dark:bg-earth-700 rounded w-3/4" />
                <div className="h-3 bg-lsc-border dark:bg-earth-700 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      </section>
    )
  }

  if (!data || data.items.length === 0) return null

  return (
    <section aria-label={t('aria.eventDetailModal.relatedEvents')}>
      <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <Star className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        {t('events.detail.youMayAlsoLike')}
      </h2>
      <div className="space-y-3">
        {data.items.map((relatedEvent) => (
          <Link
            key={relatedEvent.id}
            to={`/events/detail/${relatedEvent.id}`}
            className="flex items-center gap-3 p-3 bg-lsc-cream/50 dark:bg-earth-800/50 rounded-xl hover:bg-lsc-cream dark:hover:bg-earth-800 transition-colors group"
            aria-label={t('events.detail.relatedEventLabel', { title: relatedEvent.title })}
          >
            <div className="w-12 h-12 flex-shrink-0 bg-lsc-white dark:bg-earth-700 rounded-lg flex flex-col items-center justify-center">
              <span className="text-xs text-lsc-rose dark:text-lsc-rose-light font-medium leading-none">
                {new Date(relatedEvent.start_time).toLocaleDateString(language, { month: 'short' })}
              </span>
              <span className="text-lg font-bold text-lsc-dark dark:text-lsc-cream leading-none">
                {new Date(relatedEvent.start_time).getDate()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream line-clamp-1 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">
                {relatedEvent.title}
              </h3>
              <div className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                <span className="flex items-center gap-1">
                  <Clock aria-hidden="true" className="w-3 h-3" />
                  {formatTime(relatedEvent.start_time, language)}
                </span>
                {relatedEvent.category && (
                  <span className={`px-1.5 py-0.5 rounded text-xs ${getCategoryColorClasses(relatedEvent.category)}`}>
                    {getCategoryDisplayName(relatedEvent.category)}
                  </span>
                )}
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors" aria-hidden="true" />
          </Link>
        ))}
      </div>
    </section>
  )
}

// eslint-disable-next-line complexity
export default function EventDetailPage() {
  const branding = useBranding()
  const { eventId } = useParams<{ eventId: string }>()
  const { t, language } = useTranslation()
  const { settings } = useAccessibility()
  const { isAuthenticated } = useAuth()
  const [showRegistration, setShowRegistration] = useState(false)
  const [showReviewForm, setShowReviewForm] = useState(false)
  const [showCalendarMenu, setShowCalendarMenu] = useState(false)
  const [imageError, setImageError] = useState(false)
  const [now] = useState(() => Date.now())
  const calendarMenuRef = useRef<HTMLDivElement>(null)
  const calendarButtonRef = useRef<HTMLButtonElement>(null)

  const {
    data: event,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['event', eventId],
    queryFn: () => getEventById(Number(eventId)),
    enabled: !!eventId && !isNaN(Number(eventId)),
  })

  const { data: myRegistrations } = useQuery<MyEventRegistration[]>({
    queryKey: ['my-registrations'],
    queryFn: getMyEventRegistrations,
    enabled: isAuthenticated,
    staleTime: 60 * 1000,
  })

  usePageMeta({
    ...(event?.title && { title: event.title }),
    ...(event && { description: truncateDescription(event.description, 160, `Event at ${branding.library_name}`) }),
    ...(event && { canonicalPath: `/events/detail/${event.id}` }),
    ...(event?.title && { ogTitle: event.title }),
    ...(event && { ogDescription: truncateDescription(event.description, 160, `Event at ${branding.library_name}`) }),
    ...(event?.image_url && { ogImage: event.image_url }),
    ogType: 'event',
  })

  if (isLoading) {
    return (
      <PageContainer className="py-8" role="status" aria-label={t('events.detail.loadingEvent')}>
        <div className="motion-safe:animate-pulse space-y-6">
          <div className="h-6 w-32 bg-earth-200 dark:bg-earth-700 rounded" />
          <div className="h-48 bg-earth-200 dark:bg-earth-700 rounded-xl" />
          <div className="h-8 w-3/4 bg-earth-200 dark:bg-earth-700 rounded" />
          <div className="space-y-3">
            <div className="h-4 w-full bg-earth-100 dark:bg-earth-800 rounded" />
            <div className="h-4 w-5/6 bg-earth-100 dark:bg-earth-800 rounded" />
            <div className="h-4 w-4/6 bg-earth-100 dark:bg-earth-800 rounded" />
          </div>
        </div>
      </PageContainer>
    )
  }

  if (isError || !event) {
    return (
      <PageContainer className="py-8">
        <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
          <AlertTriangle className="w-10 h-10 text-earth-600 dark:text-earth-500" aria-hidden="true" />
          <p className="text-lsc-dark/80 dark:text-lsc-cream/80 text-lg">{t('events.detail.eventNotFound')}</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{t('events.detail.eventNotFoundHint')}</p>
          <Link
            to="/events"
            className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors"
          >
            {t('events.detail.backToEvents')}
          </Link>
        </div>
      </PageContainer>
    )
  }

  const isPastEvent = new Date(event.start_time) < new Date()
  const isNew = event.created_at && !isPastEvent && (() => {
    const created = new Date(event.created_at)
    const sevenDaysAgo = new Date(now - 7 * 24 * 60 * 60 * 1000)
    return created >= sevenDaysAgo
  })()
  const capacityInfo = getCapacityUrgencyShared(event.spots_remaining, event.max_attendees, t, settings.noUrgentLanguage)
  const isFull = capacityInfo.level === 'full'
  const spotsInfo = event.max_attendees !== null
    ? capacityInfo.message || t('events.unlimitedCapacity')
    : t('events.unlimitedCapacity')
  const canRegister = event.registration_required
  const myRegistration = myRegistrations?.find((r) => r.event_id === event.id)
  const headerGradient = getCategoryHeaderGradient(event.category)
  const eventDetailUrl = `${window.location.origin}/events/detail/${event.id}`

  const handleAddToCalendar = (service: 'google' | 'outlook' | 'ical') => {
    switch (service) {
      case 'google':
        window.open(generateGoogleCalendarUrl(event), '_blank', 'noopener,noreferrer')
        break
      case 'outlook':
        window.open(generateOutlookCalendarUrl(event), '_blank', 'noopener,noreferrer')
        break
      case 'ical': {
        // PR #999: download from backend endpoint so the file matches the
        // server-side calendar feed (consistent UID, escapes, tz handling).
        const a = document.createElement('a')
        a.href = `/api/v1/events/${event.id}/calendar.ics`
        a.download = `event-${event.id}.ics`
        a.rel = 'noopener'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        break
      }
    }
    setShowCalendarMenu(false)
  }

  const handleCalendarMenuKeyDown = (e: React.KeyboardEvent) => {
    const items = calendarMenuRef.current?.querySelectorAll('[role="menuitem"]') as NodeListOf<HTMLElement> | undefined
    if (!items?.length) return
    const currentIndex = Array.from(items).indexOf(document.activeElement as HTMLElement)
    switch (e.key) {
      case 'ArrowDown': e.preventDefault(); items[(currentIndex + 1) % items.length]!.focus(); break
      case 'ArrowUp': e.preventDefault(); items[(currentIndex - 1 + items.length) % items.length]!.focus(); break
      case 'Home': e.preventDefault(); items[0]!.focus(); break
      case 'End': e.preventDefault(); items[items.length - 1]!.focus(); break
      case 'Escape': e.preventDefault(); setShowCalendarMenu(false); calendarButtonRef.current?.focus(); break
    }
  }

  return (
    <>
      <PageContainer className="py-8">
        {/* Back link */}
        <Link
          to="/events"
          className="inline-flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors mb-6"
        >
          <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          {t('events.detail.backToEvents')}
        </Link>

        {/* Hero: image or gradient header */}
        {event.image_url && !imageError ? (
          <div className="relative h-56 sm:h-72 md:h-80 rounded-xl overflow-hidden mb-8">
            <img
              src={event.image_url}
              alt={`Image for ${event.title}`}
              className="w-full h-full object-cover"
              onError={() => setImageError(true)}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-6">
              <div className="flex items-start gap-2 mb-2">
                <h1 className="text-2xl sm:text-3xl font-serif font-bold text-white">
                  {event.title}
                </h1>
                {isNew && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-gradient-to-r from-status-warning-400 to-orange-500 text-white shadow-sm flex-shrink-0">
                    <Sparkles className="w-3 h-3" aria-hidden="true" />
                    {t('events.new')}
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {event.category && (
                  <span className="text-xs px-3 py-1 rounded-full font-medium bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream backdrop-blur-sm">
                    {getCategoryDisplayName(event.category)}
                  </span>
                )}
                {event.audience && (
                  <span className="text-xs px-3 py-1 bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream rounded-full backdrop-blur-sm font-medium">
                    {event.audience}
                  </span>
                )}
                {isPastEvent && (
                  <span className="text-xs px-3 py-1 bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream rounded-full backdrop-blur-sm font-medium">
                    {t('events.pastEvent')}
                  </span>
                )}
                {event.tags && event.tags.length > 0 && event.tags.slice(0, 3).map((tag) => (
                  <span key={tag} className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream backdrop-blur-sm font-medium">
                    <Tag className="w-2.5 h-2.5" aria-hidden="true" />
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className={`bg-gradient-to-r ${headerGradient} p-6 sm:p-8 rounded-xl mb-8`}>
            <div className="flex items-start gap-2 mb-3">
              <h1 className="text-2xl sm:text-3xl font-serif font-bold text-white">
                {event.title}
              </h1>
              {isNew && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-gradient-to-r from-status-warning-400 to-orange-500 text-white shadow-sm flex-shrink-0">
                  <Sparkles className="w-3 h-3" aria-hidden="true" />
                  {t('events.new')}
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {event.category && (
                <span className="text-xs px-3 py-1 bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream rounded-full font-medium">
                  {getCategoryDisplayName(event.category)}
                </span>
              )}
              {event.audience && (
                <span className="text-xs px-3 py-1 bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream rounded-full font-medium">
                  {event.audience}
                </span>
              )}
              {isPastEvent && (
                <span className="text-xs px-3 py-1 bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream rounded-full font-medium">
                  {t('events.pastEvent')}
                </span>
              )}
              {event.tags && event.tags.length > 0 && event.tags.slice(0, 3).map((tag) => (
                <span key={tag} className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-lsc-white/90 dark:bg-earth-800/70 text-lsc-dark dark:text-lsc-cream font-medium">
                  <Tag className="w-2.5 h-2.5" aria-hidden="true" />
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Two-column layout: main content + sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Rating for past events */}
            {isPastEvent && event.average_rating !== undefined && event.average_rating !== null && event.review_count > 0 && (
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-0.5" aria-label={t('events.rating.outOf', { rating: event.average_rating })}>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <Star
                      key={star}
                      className={`w-5 h-5 ${star <= Math.round(event.average_rating!) ? 'text-status-warning-400 fill-status-warning-400' : 'text-earth-300'}`}
                      aria-hidden="true"
                    />
                  ))}
                </div>
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {event.average_rating.toFixed(1)} ({t('events.rating.reviewCount', { count: event.review_count })})
                </span>
              </div>
            )}

            {/* Capacity urgency alert */}
            {!isPastEvent && (capacityInfo.level === 'critical' || capacityInfo.level === 'urgent') && (
              <div
                className={`flex items-center gap-2 px-4 py-3 rounded-xl font-semibold ${
                  capacityInfo.level === 'critical'
                    ? 'bg-status-danger-100 dark:bg-status-danger-900/40 text-status-danger-700 dark:text-status-danger-300 motion-safe:animate-pulse'
                    : 'bg-status-warning-100 dark:bg-status-warning-900/40 text-status-warning-700 dark:text-status-warning-300'
                }`}
                role="status"
                aria-live="polite"
                aria-label={capacityInfo.ariaLabel || undefined}
              >
                <AlertTriangle aria-hidden="true" className="w-5 h-5" />
                <span>{capacityInfo.message}</span>
              </div>
            )}

            {/* Drop-in indicator */}
            {!canRegister && !isPastEvent && (
              <div className="flex items-center gap-2 px-4 py-3 bg-status-success-50 dark:bg-status-success-900/20 rounded-xl text-status-success-700 dark:text-status-success-300">
                <CheckCircle className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                <span className="text-sm font-medium">{t('events.dropInEvent')}</span>
              </div>
            )}

            {/* Description */}
            {event.description && (
              <section>
                <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('events.detail.aboutThisEvent')}</h2>
                <div className="text-lsc-dark/80 dark:text-lsc-cream/80 whitespace-pre-wrap leading-relaxed">
                  {event.description}
                </div>
              </section>
            )}

            {/* Accessibility & what to expect */}
            {(() => {
              const provisions: { key: string; icon: React.ElementType; label: string }[] = []
              if (event.wheelchair_accessible) provisions.push({ key: 'wheelchair', icon: Accessibility, label: t('events.affordances.wheelchair', 'Wheelchair accessible') })
              if (event.asl_provided) provisions.push({ key: 'asl', icon: Hand, label: t('events.affordances.asl', 'ASL provided') })
              if (event.captioning_provided) provisions.push({ key: 'captions', icon: CheckCircle, label: t('events.affordances.captioning', 'Captioning provided') })
              if (event.assistive_listening) provisions.push({ key: 'listening', icon: CheckCircle, label: t('events.affordances.assistiveListening', 'Assistive listening') })
              if (event.sensory_friendly) provisions.push({ key: 'sensory', icon: CheckCircle, label: t('events.affordances.sensory', 'Sensory-friendly') })
              if (event.large_print_available) provisions.push({ key: 'largePrint', icon: CheckCircle, label: t('events.affordances.largePrint', 'Large print available') })

              const sensory: { key: string; label: string; value: string }[] = []
              if (event.lighting) sensory.push({ key: 'lighting', label: t('events.sensory.lighting.label', 'Lighting'), value: t(`events.sensory.lighting.${event.lighting}`, event.lighting) })
              if (event.noise_level) sensory.push({ key: 'noise', label: t('events.sensory.noise.label', 'Noise level'), value: t(`events.sensory.noise.${event.noise_level}`, event.noise_level) })
              if (event.crowd_size) sensory.push({ key: 'crowd', label: t('events.sensory.crowd.label', 'Expected crowd'), value: t(`events.sensory.crowd.${event.crowd_size}`, event.crowd_size) })

              const hasInfo =
                provisions.length > 0 ||
                sensory.length > 0 ||
                event.quiet_space_available === true ||
                Boolean(event.accessibility_notes)

              if (!hasInfo) return null

              return (
                <section aria-labelledby="a11y-section-heading" className="border-t border-lsc-border dark:border-earth-700 pt-8">
                  <h2
                    id="a11y-section-heading"
                    className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2"
                  >
                    <Accessibility className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                    {t('events.whatToExpect.title', 'Accessibility & what to expect')}
                  </h2>
                  {provisions.length > 0 && (
                    <ul className="flex flex-wrap gap-2 mb-4" aria-label={t('events.whatToExpect.provisionsLabel', 'Accessibility provisions')}>
                      {provisions.map(({ key, icon: Icon, label }) => (
                        <li
                          key={key}
                          className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full bg-forest-100 dark:bg-forest-900/40 text-forest-800 dark:text-forest-200 font-medium"
                        >
                          <Icon className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
                          {label}
                        </li>
                      ))}
                    </ul>
                  )}
                  {sensory.length > 0 && (
                    <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-3">
                      {sensory.map(({ key, label, value }) => (
                        <div key={key} className="flex items-center gap-1.5">
                          <dt className="font-medium">{label}:</dt>
                          <dd>{value}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  {event.quiet_space_available && (
                    <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-2">
                      {t('events.sensory.quietSpace', 'A quiet space is available')}
                    </p>
                  )}
                  {event.accessibility_notes && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-pre-wrap">
                      {event.accessibility_notes}
                    </p>
                  )}
                </section>
              )
            })()}

            {/* Related events */}
            {!isPastEvent && (
              <div className="border-t border-lsc-border dark:border-earth-700 pt-8">
                <RelatedEventsSection eventId={event.id} />
              </div>
            )}
          </div>

          {/* Sidebar */}
          <aside className="space-y-6">
            {/* Date & time card */}
            <div className="bg-lsc-cream dark:bg-earth-800 rounded-xl p-5 space-y-4">
              <div className="flex items-start gap-3">
                <Calendar className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light mt-0.5 flex-shrink-0" aria-hidden="true" />
                <div>
                  <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                    {formatDate(event.start_time, language)}
                  </p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {formatTime(event.start_time, language)}
                    {event.end_time && ` - ${formatTime(event.end_time, language)}`}
                  </p>
                </div>
              </div>

              {/* Location */}
              {event.location && (
                <div className="flex items-start gap-3">
                  <MapPin className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light mt-0.5 flex-shrink-0" aria-hidden="true" />
                  <div>
                    <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{event.location}</p>
                    {event.is_virtual && (
                      <span className="inline-block mt-1 text-xs px-2 py-1 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded">
                        {t('events.detail.virtualEvent')}
                      </span>
                    )}
                    <a
                      href={buildGoogleMapsUrl(event.location)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block mt-1 text-sm text-lsc-rose hover:underline dark:text-lsc-rose-light"
                    >
                      {t('events.detail.viewOnMap')}
                    </a>
                  </div>
                </div>
              )}

              {/* Capacity */}
              {event.max_attendees !== null && (
                <div className="flex items-start gap-3">
                  <Users className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light mt-0.5 flex-shrink-0" aria-hidden="true" />
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('events.detail.capacity')}</p>
                      {!isPastEvent && isFull && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-status-danger-100 dark:bg-status-danger-900/40 text-status-danger-700 dark:text-status-danger-300 font-semibold" role="status">
                          {t('events.full')}
                        </span>
                      )}
                    </div>
                    <p className={`text-sm ${
                      !isPastEvent && (capacityInfo.level === 'critical' || capacityInfo.level === 'urgent')
                        ? capacityInfo.level === 'critical'
                          ? 'text-status-danger-600 dark:text-status-danger-400 font-semibold'
                          : 'text-status-warning-600 dark:text-status-warning-400 font-medium'
                        : capacityInfo.level === 'full'
                        ? 'text-lsc-dark/70 dark:text-lsc-cream/70 font-medium'
                        : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                    }`}>
                      {spotsInfo}
                    </p>
                  </div>
                </div>
              )}

              {/* Series info */}
              {event.series_name && (
                <div className="flex items-start gap-3">
                  <Sparkles className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light mt-0.5 flex-shrink-0" aria-hidden="true" />
                  <div>
                    <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('events.detail.partOfSeries')}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{event.series_name}</p>
                  </div>
                </div>
              )}
            </div>

            {/* Action buttons */}
            <div className="space-y-3">
              {/* Register / Waitlist. The registration form (RegistrationModal)
                  renders the Cloudflare Turnstile widget and passes the
                  turnstile_token through to POST /events/{id}/register. */}
              {canRegister && !isPastEvent && myRegistration ? (
                <div
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium bg-status-success-50 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-300 border-2 border-status-success-200 dark:border-status-success-800"
                  role="status"
                  aria-live="polite"
                >
                  <CheckCircle className="w-5 h-5" aria-hidden="true" />
                  {myRegistration.status === 'waitlisted'
                    ? t('events.detail.youAreOnWaitlist', "You're on the waitlist")
                    : t('events.detail.youAreRegistered', "You're registered")}
                </div>
              ) : canRegister && !isPastEvent && (
                <button
                  onClick={() => setShowRegistration(true)}
                  aria-label={isFull ? t('events.detail.joinEventWaitlist') : t('events.detail.registerForThisEvent')}
                  className={`w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium transition-colors ${
                    isFull
                      ? 'bg-lsc-cream hover:bg-lsc-cream/90 dark:bg-lsc-dark/30 dark:hover:bg-lsc-dark/50 text-lsc-rose dark:text-lsc-rose-light border-2 border-lsc-rose'
                      : 'bg-lsc-rose hover:bg-lsc-rose/90 text-white'
                  }`}
                >
                  <UserPlus className="w-5 h-5" aria-hidden="true" />
                  {isFull ? t('events.waitlist') : t('events.registerForEvent')}
                </button>
              )}

              {/* Add to Calendar dropdown */}
              {!isPastEvent && (
                <div className="relative">
                  <button
                    ref={calendarButtonRef}
                    onClick={() => setShowCalendarMenu(!showCalendarMenu)}
                    className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium bg-lsc-cream hover:bg-lsc-border dark:bg-lsc-brown dark:hover:bg-lsc-brown/90 text-lsc-dark dark:text-lsc-cream transition-colors"
                    aria-expanded={showCalendarMenu}
                    aria-haspopup="menu"
                    aria-label={t('events.detail.addToCalendarAriaLabel')}
                  >
                    <Calendar className="w-5 h-5" aria-hidden="true" />
                    {t('events.detail.addToCalendar')}
                    <ChevronDown className="w-4 h-4" aria-hidden="true" />
                  </button>

                  {showCalendarMenu && (
                    <>
                      <div className="fixed inset-0 z-10" onClick={() => setShowCalendarMenu(false)} aria-hidden="true" />
                      <div
                        ref={calendarMenuRef}
                        className="absolute left-0 top-full mt-2 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-1 z-20 w-full"
                        role="menu"
                        aria-label={t('events.agenda.calendarOptions')}
                        onKeyDown={handleCalendarMenuKeyDown}
                      >
                        <button
                          onClick={() => handleAddToCalendar('google')}
                          className="w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10"
                          role="menuitem"
                          tabIndex={-1}
                          aria-label={t('events.detail.addToGoogleCalendar')}
                        >
                          <ExternalLink className="w-4 h-4" aria-hidden="true" />
                          {t('events.agenda.googleCalendar')}
                        </button>
                        <button
                          onClick={() => handleAddToCalendar('outlook')}
                          className="w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10"
                          role="menuitem"
                          tabIndex={-1}
                          aria-label={t('events.detail.addToOutlookCalendar')}
                        >
                          <ExternalLink className="w-4 h-4" aria-hidden="true" />
                          {t('events.agenda.outlookCalendar')}
                        </button>
                        <button
                          onClick={() => handleAddToCalendar('ical')}
                          className="w-full text-left px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors flex items-center gap-2 focus-visible:outline-none focus-visible:bg-lsc-rose/10"
                          role="menuitem"
                          tabIndex={-1}
                          aria-label={t('events.detail.downloadICalFile')}
                        >
                          <Download className="w-4 h-4" aria-hidden="true" />
                          {t('events.detail.downloadIcsFile')}
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Leave a Review for past events */}
              {isPastEvent && (
                <button
                  onClick={() => setShowReviewForm(true)}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white transition-colors"
                  aria-label={t('events.detail.leaveReviewForEvent')}
                >
                  <MessageSquare className="w-5 h-5" aria-hidden="true" />
                  {t('events.detail.leaveReview')}
                </button>
              )}

              {/* Share */}
              <ShareButton
                resourceType="event"
                resourceId={event.id}
                title={event.title}
                {...(event.description ? { description: event.description } : {})}
                date={new Date(event.start_time).toLocaleDateString(language, { month: 'short', day: 'numeric', year: 'numeric' })}
                {...(event.image_url ? { imageUrl: event.image_url } : {})}
                customUrl={eventDetailUrl}
                variant="default"
                showCount={true}
                platforms={['copy_link', 'bluesky', 'mastodon', 'email']}
              />
            </div>
          </aside>
        </div>
      </PageContainer>

      {/* Registration modal */}
      {showRegistration && (
        <RegistrationModal
          event={event}
          onClose={() => setShowRegistration(false)}
        />
      )}

      {/* Review form modal */}
      {showReviewForm && (
        <EventReviewForm
          event={event}
          onClose={() => setShowReviewForm(false)}
        />
      )}
    </>
  )
}
