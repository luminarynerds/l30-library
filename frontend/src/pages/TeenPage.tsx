/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Archive, BookOpen, Calendar, Clock, Code2, HandHeart, Mail, MapPin, Sparkles, Trophy, UserPlus, Users } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useAuth } from '@/contexts/AuthContext'
import { useTranslation, getCurrentLocale } from '@/i18n'
import {
  getActiveReadingPrograms,
  getUpcomingYouthEvents,
  getMyReadingProgress,
  type ActiveReadingProgram,
  type UpcomingYouthEvent,
} from '@/api/domains/reading/youth-reading-api'
import { LexilePresetStrip, TEEN_BANDS } from '../components/LexilePresetStrip'

interface TeenProgram {
  title: string
  description: string
  href: string
  icon: React.ReactNode
  ageGroup: string
}

const TEEN_AUDIENCE_LABELS: Record<string, string> = {
  teen: 'Teens',
  family: 'Family',
  all_ages: 'All Ages',
}

// Surface programs whose age_group is teen-coded.
// Heuristic: explicit "teen" mention, or a numeric range that overlaps 13-17.
function isTeenProgram(p: ActiveReadingProgram): boolean {
  const ag = (p.age_group || '').toLowerCase()
  if (!ag) return false
  if (ag.includes('teen') || ag.includes('ya') || ag.includes('young adult')) return true
  const range = ag.match(/(\d+)\s*[-–to]+\s*(\d+)/)
  if (range) {
    const lo = Number(range[1])
    const hi = Number(range[2])
    if (Number.isFinite(lo) && Number.isFinite(hi) && hi >= 13 && lo <= 17) return true
  }
  const plus = ag.match(/(\d+)\s*\+/)
  if (plus) {
    const lo = Number(plus[1])
    if (Number.isFinite(lo) && lo <= 17) return true
  }
  return false
}

// Events teens are likely to attend: explicitly teen-tagged, family, or all_ages.
function isTeenEvent(e: UpcomingYouthEvent): boolean {
  const a = (e.audience || '').toLowerCase()
  return a === 'teen' || a === 'family' || a === 'all_ages'
}

function formatEventDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString(getCurrentLocale(), { weekday: 'short', month: 'short', day: 'numeric' })
}

function formatTimeRange(start: string, end: string | null): string {
  const fmt = (s: string) => {
    const parts = s.split(':').map(Number)
    const h = parts[0] ?? 0
    const m = parts[1] ?? 0
    const suffix = h >= 12 ? 'pm' : 'am'
    const hour = h % 12 || 12
    return m === 0 ? `${hour}${suffix}` : `${hour}:${String(m).padStart(2, '0')}${suffix}`
  }
  if (!end) return fmt(start)
  return `${fmt(start)} - ${fmt(end)}`
}

function ProgramCard({ program }: { program: TeenProgram }) {
  return (
    <Link
      key={program.href}
      to={program.href}
      className="group rounded-xl border border-lsc-border bg-lsc-white p-5 transition hover:border-earth-400 hover:shadow-sm dark:border-earth-700 dark:bg-earth-800"
    >
      <div className="flex items-center justify-between">
        <span className="inline-flex rounded-lg bg-lsc-cream p-2 text-lsc-rose dark:bg-lsc-brown/40 dark:text-lsc-rose-light">
          {program.icon}
        </span>
        <span className="rounded-full bg-lsc-cream px-2.5 py-1 text-xs font-medium text-lsc-dark dark:bg-lsc-brown/50 dark:text-lsc-cream">
          {program.ageGroup}
        </span>
      </div>

      <h3 className="mt-4 font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">{program.title}</h3>
      <p className="mt-2 text-sm text-lsc-dark/75 dark:text-lsc-cream/75">{program.description}</p>

      <div className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light">
        Explore program
        <ArrowRight aria-hidden="true" className="h-4 w-4 transition group-hover:translate-x-0.5" />
      </div>
    </Link>
  )
}

function ReadingProgramBanner({ programs }: { programs: ActiveReadingProgram[] }) {
  if (programs.length === 0) return null

  return (
    <section className="mb-10">
      <div className="flex items-center gap-3 mb-4">
        <Trophy aria-hidden="true" className="h-6 w-6 text-lsc-rose" />
        <h2 className="font-serif text-xl md:text-2xl font-semibold text-earth-700 dark:text-lsc-cream">
          Reading Programs for Teens
        </h2>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {programs.map((program) => {
          const today = new Date()
          const start = new Date(program.start_date)
          const end = new Date(program.end_date)
          const totalDays = Math.max(1, Math.ceil((end.getTime() - start.getTime()) / 86_400_000))
          const elapsed = Math.max(0, Math.ceil((today.getTime() - start.getTime()) / 86_400_000))
          const remaining = Math.max(0, Math.ceil((end.getTime() - today.getTime()) / 86_400_000))
          const progress = Math.min(100, Math.round((elapsed / totalDays) * 100))

          return (
            <div
              key={program.id}
              className="rounded-xl border border-lsc-rose/30 bg-gradient-to-br from-lsc-cream to-lsc-white p-5 dark:border-lsc-rose/20 dark:from-earth-800 dark:to-earth-900"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 truncate">
                    {program.name}
                  </h3>
                  {program.description && (
                    <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2">
                      {program.description}
                    </p>
                  )}
                </div>
                {program.age_group && (
                  <span className="shrink-0 rounded-full bg-lsc-rose/10 px-2.5 py-1 text-xs font-medium text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light">
                    {program.age_group}
                  </span>
                )}
              </div>

              <div className="mt-4 flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <span className="inline-flex items-center gap-1.5">
                  <Clock aria-hidden="true" className="h-4 w-4" />
                  {remaining} {remaining === 1 ? 'day' : 'days'} left
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <UserPlus aria-hidden="true" className="h-4 w-4" />
                  {program.enrollment_count} enrolled
                </span>
                {program.reading_goal_type && program.reading_goal_value && (
                  <span className="inline-flex items-center gap-1.5">
                    <BookOpen aria-hidden="true" className="h-4 w-4" />
                    Goal: {program.reading_goal_value} {program.reading_goal_type}
                  </span>
                )}
              </div>

              <div className="mt-3">
                <div className="flex justify-between text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mb-1">
                  <span>{progress}% of program elapsed</span>
                  <span>{remaining}d remaining</span>
                </div>
                <div className="h-2 w-full rounded-full bg-earth-200 dark:bg-earth-700">
                  <div
                    className="h-2 rounded-full bg-lsc-rose transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              <Link
                to="/programs"
                className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-lsc-rose hover:text-lsc-rose/80 dark:text-lsc-rose-light dark:hover:text-lsc-rose-light/80"
              >
                Sign up
                <ArrowRight aria-hidden="true" className="h-4 w-4" />
              </Link>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function UpcomingEvents({ events }: { events: UpcomingYouthEvent[] }) {
  if (events.length === 0) return null

  return (
    <section className="mb-10">
      <div className="flex items-center gap-3 mb-4">
        <Calendar aria-hidden="true" className="h-6 w-6 text-lsc-rose" />
        <h2 className="font-serif text-xl md:text-2xl font-semibold text-earth-700 dark:text-lsc-cream">
          Upcoming Events
        </h2>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {events.map((event) => (
          <div
            key={event.id}
            className="rounded-xl border border-lsc-border bg-lsc-white p-5 dark:border-earth-700 dark:bg-earth-800"
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 line-clamp-1">
                {event.title}
              </h3>
              <span className="shrink-0 rounded-full bg-lsc-cream px-2.5 py-1 text-xs font-medium text-lsc-dark dark:bg-lsc-brown/50 dark:text-lsc-cream">
                {TEEN_AUDIENCE_LABELS[event.audience] || event.audience}
              </span>
            </div>

            <div className="mt-3 space-y-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <div className="flex items-center gap-2">
                <Calendar aria-hidden="true" className="h-4 w-4 shrink-0" />
                <span>{formatEventDate(event.program_date)}</span>
                <span className="text-lsc-dark/40 dark:text-lsc-cream/40">|</span>
                <span>{formatTimeRange(event.start_time, event.end_time)}</span>
              </div>
              {event.location_name && (
                <div className="flex items-center gap-2">
                  <MapPin aria-hidden="true" className="h-4 w-4 shrink-0" />
                  <span>{event.location_name}</span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <UserPlus aria-hidden="true" className="h-4 w-4 shrink-0" />
                <span>
                  {event.registration_count} registered{event.capacity ? ` / ${event.capacity} spots` : ''}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 text-center">
        <Link
          to="/events"
          className="inline-flex items-center gap-2 text-sm font-medium text-lsc-rose hover:text-lsc-rose/80 dark:text-lsc-rose-light dark:hover:text-lsc-rose-light/80"
        >
          View all events
          <ArrowRight aria-hidden="true" className="h-4 w-4" />
        </Link>
      </div>
    </section>
  )
}

function MyReadingProgress() {
  const { user } = useAuth()

  const { data } = useQuery({
    queryKey: ['teen', 'my-reading-progress'],
    queryFn: getMyReadingProgress,
    staleTime: 2 * 60 * 1000,
    enabled: !!user,
  })

  if (!user || !data) return null
  if (data.enrolled_programs.length === 0 && data.books_read_count === 0) return null

  return (
    <section className="mb-10">
      <div className="flex items-center gap-3 mb-4">
        <BookOpen aria-hidden="true" className="h-6 w-6 text-lsc-rose" />
        <h2 className="font-serif text-xl md:text-2xl font-semibold text-earth-700 dark:text-lsc-cream">
          My Reading
        </h2>
      </div>

      <div className="rounded-xl border border-lsc-rose/30 bg-gradient-to-br from-lsc-cream to-lsc-white p-5 dark:border-lsc-rose/20 dark:from-earth-800 dark:to-earth-900">
        <div className="flex flex-wrap gap-6 mb-5">
          <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <BookOpen aria-hidden="true" className="h-4 w-4 text-lsc-rose" />
            <span className="font-semibold text-lsc-dark dark:text-earth-50">{data.books_read_count}</span>
            <span>{data.books_read_count === 1 ? 'book logged' : 'books logged'}</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <Clock aria-hidden="true" className="h-4 w-4 text-lsc-rose" />
            <span className="font-semibold text-lsc-dark dark:text-earth-50">{data.total_reading_minutes}</span>
            <span>minutes read</span>
          </div>
        </div>

        {data.enrolled_programs.length > 0 && (
          <div className="space-y-4">
            {data.enrolled_programs.map((prog, i) => {
              const end = new Date(prog.end_date)
              const today = new Date()
              const remaining = Math.max(0, Math.ceil((end.getTime() - today.getTime()) / 86_400_000))
              const goalTarget = prog.goal_target || 0
              const progressValue = prog.goal_type === 'minutes' ? prog.progress_minutes : prog.log_count
              const progressPct = goalTarget > 0 ? Math.min(100, Math.round((progressValue / goalTarget) * 100)) : 0
              const goalLabel = prog.goal_type === 'minutes' ? 'min' : 'books'

              return (
                <div key={i} className="rounded-lg border border-lsc-border bg-lsc-white/60 p-4 dark:border-earth-700 dark:bg-earth-800/60">
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 truncate">
                      {prog.program_name}
                    </h3>
                    <span className="shrink-0 text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
                      {remaining} {remaining === 1 ? 'day' : 'days'} left
                    </span>
                  </div>
                  {goalTarget > 0 && (
                    <>
                      <div className="flex justify-between text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mb-1">
                        <span>{progressValue} / {goalTarget} {goalLabel}</span>
                        <span>{progressPct}%</span>
                      </div>
                      <div className="h-2.5 w-full rounded-full bg-earth-200 dark:bg-earth-700">
                        <div
                          className="h-2.5 rounded-full bg-lsc-rose transition-all"
                          style={{ width: `${progressPct}%` }}
                        />
                      </div>
                    </>
                  )}
                </div>
              )
            })}
          </div>
        )}

        <Link
          to="/reading-logs"
          className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-lsc-rose hover:text-lsc-rose/80 dark:text-lsc-rose-light dark:hover:text-lsc-rose-light/80"
        >
          Log more reading
          <ArrowRight aria-hidden="true" className="h-4 w-4" />
        </Link>
      </div>
    </section>
  )
}

interface QuickLink {
  title: string
  description: string
  href: string
  icon: React.ReactNode
}

const QUICK_LINKS: QuickLink[] = [
  {
    title: 'Volunteer & Earn Service Hours',
    description: 'Help with library programs, archives, or peer mentoring. Documented hours for school.',
    href: '/volunteer/apply',
    icon: <HandHeart aria-hidden="true" className="h-5 w-5" />,
  },
  {
    title: 'Reading Programs',
    description: 'Join a challenge, track your progress, and earn prizes.',
    href: '/programs',
    icon: <BookOpen aria-hidden="true" className="h-5 w-5" />,
  },
  {
    title: 'Ask a Librarian',
    description: 'Help with a school project, research, or finding your next read.',
    href: '/ask-librarian',
    icon: <Mail aria-hidden="true" className="h-5 w-5" />,
  },
]

function QuickLinks() {
  return (
    <section className="mt-12">
      <div className="flex items-center gap-3 mb-2">
        <Sparkles aria-hidden="true" className="h-6 w-6 text-lsc-rose" />
        <h2 className="font-serif text-xl md:text-2xl font-semibold text-earth-700 dark:text-lsc-cream">
          Get Involved
        </h2>
      </div>
      <p className="mt-1 mb-6 text-lsc-dark/70 dark:text-lsc-cream/70">
        Make the library yours.
      </p>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {QUICK_LINKS.map((link) => (
          <Link
            key={link.href}
            to={link.href}
            className="group rounded-xl border border-lsc-border bg-lsc-white p-5 transition hover:border-earth-400 hover:shadow-sm dark:border-earth-700 dark:bg-earth-800"
          >
            <span className="inline-flex rounded-lg bg-lsc-cream p-2 text-lsc-rose dark:bg-lsc-brown/40 dark:text-lsc-rose-light">
              {link.icon}
            </span>
            <h3 className="mt-4 font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">
              {link.title}
            </h3>
            <p className="mt-2 text-sm text-lsc-dark/75 dark:text-lsc-cream/75">
              {link.description}
            </p>
            <div className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light">
              Learn more
              <ArrowRight aria-hidden="true" className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}

export default function TeenPage(): React.ReactElement {
  const { t } = useTranslation()

  const { data: activePrograms } = useQuery({
    queryKey: ['teen', 'active-reading-programs'],
    queryFn: getActiveReadingPrograms,
    staleTime: 5 * 60 * 1000,
  })

  const { data: upcomingEvents } = useQuery({
    queryKey: ['teen', 'upcoming-events'],
    queryFn: () => getUpcomingYouthEvents(8),
    staleTime: 5 * 60 * 1000,
  })

  const teenPrograms = useMemo(() => activePrograms?.filter(isTeenProgram) ?? [], [activePrograms])
  const teenEvents = useMemo(
    () => (upcomingEvents ?? []).filter(isTeenEvent).slice(0, 4),
    [upcomingEvents],
  )

  const programs: TeenProgram[] = useMemo(
    () => [
      {
        title: t('youth.programs.codingTracks.title', 'Coding Tracks'),
        description: t('youth.programs.codingTracks.description', 'Beginner to advanced coding pathways, from Scratch to Python.'),
        href: '/youth/coding-tracks',
        icon: <Code2 aria-hidden="true" className="h-5 w-5" />,
        ageGroup: t('youth.programs.codingTracks.ageGroup', 'Ages 8-18'),
      },
      {
        title: t('youth.programs.teenMentors.title', 'Teen Mentors'),
        description: t('youth.programs.teenMentors.description', 'Get paired with peer mentors, or become one yourself.'),
        href: '/youth/teen-mentors',
        icon: <Users aria-hidden="true" className="h-5 w-5" />,
        ageGroup: t('youth.programs.teenMentors.ageGroup', 'Ages 13-18'),
      },
      {
        title: t('youth.programs.archives.title', 'Community Archives'),
        description: t('youth.programs.archives.description', 'Collect local stories and help preserve community history.'),
        href: '/youth/archives',
        icon: <Archive aria-hidden="true" className="h-5 w-5" />,
        ageGroup: t('youth.programs.archives.ageGroup', 'Ages 14+'),
      },
    ],
    [t],
  )

  return (
    <StandardPageLayout
      title={t('teen_page_title')}
      subtitle={t('teen_page_intro')}
      icon={Users}
    >
      <ReadingProgramBanner programs={teenPrograms} />

      <UpcomingEvents events={teenEvents} />

      <MyReadingProgress />

      <section className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <BookOpen aria-hidden="true" className="h-6 w-6 text-lsc-rose" />
          <h2 className="font-serif text-xl md:text-2xl font-semibold text-earth-700 dark:text-lsc-cream">
            Find Your Next Read
          </h2>
        </div>
        <p className="mt-1 mb-4 text-lsc-dark/70 dark:text-lsc-cream/70">
          Pick a reading level to browse titles in our catalog.
        </p>
        <LexilePresetStrip bands={TEEN_BANDS} basePath="/catalog" />
      </section>

      <section>
        <div className="flex items-center gap-3 mb-2">
          <Users aria-hidden="true" className="h-6 w-6 text-lsc-rose" />
          <h2 className="font-serif text-xl md:text-2xl font-semibold text-earth-700 dark:text-lsc-cream">
            Programs for Teens
          </h2>
        </div>
        <p className="mt-1 mb-6 text-lsc-dark/70 dark:text-lsc-cream/70">
          Code, mentor, and preserve community history.
        </p>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {programs.map((program) => (
            <ProgramCard key={program.href} program={program} />
          ))}
        </div>
      </section>

      <QuickLinks />
    </StandardPageLayout>
  )
}
