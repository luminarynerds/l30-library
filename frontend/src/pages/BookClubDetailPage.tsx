/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import toast from 'react-hot-toast'
import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Users, BookOpen, Calendar, CalendarPlus, MessageCircle, MapPin,
  ArrowLeft, Clock, UserPlus, UserMinus, Loader2, Link as LinkIcon
} from 'lucide-react'
import { EmptyState } from '../components/ui/EmptyState'
import { Button } from '@/components/ui/Button'
import {
  getBookClub,
  joinBookClub,
  leaveBookClub,
  joinBookClubWaitlist,
  leaveBookClubWaitlist,
  type BookClubDetail,
} from '../api/book-clubs-api'
import { patronCapacityBadge } from '@/utils/bookClubCapacity'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { friendlyErrorMessage } from '@/utils/friendlyError'
import { isApiError } from '@/lib/api-client'

type DetailTab = 'about' | 'discussions' | 'meetings'

export default function BookClubDetailPage(): React.ReactElement {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<DetailTab>('about')
  const [club, setClub] = useState<BookClubDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [joining, setJoining] = useState(false)
  const [waitlistBusy, setWaitlistBusy] = useState(false)
  const { isFeatureEnabled } = useOrganizationFeatures()
  const waitlistEnabled = isFeatureEnabled('book_club_waitlist_enabled')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getBookClub(Number(id))
      .then((data) => {
        setClub(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(friendlyErrorMessage(err))
        setLoading(false)
      })
  }, [id])

  // After any membership/waitlist mutation we re-fetch the detail rather
  // than optimistically patching. The capacity + waitlist-position fields
  // are server-derived (PR #914 computes them via scalar subqueries) and
  // a "join" can resolve to either "joined" or "waitlisted" depending on
  // capacity at request time, so a single source of truth avoids drift.
  const refresh = async () => {
    if (!id) return
    const fresh = await getBookClub(Number(id))
    setClub(fresh)
  }

  const handleJoinLeave = async () => {
    if (!club || !id) return
    setJoining(true)
    try {
      if (club.is_member) {
        const res = await leaveBookClub(Number(id))
        if (res.success) await refresh()
      } else {
        const res = await joinBookClub(Number(id))
        if (res.status === 'waitlisted') {
          await refresh()
          toast.success(
            t('bookClubs.waitlist.joinedToast', { position: res.position ?? 0 }),
          )
        } else if (res.success) {
          await refresh()
        }
      }
    } catch (err) {
      if (isApiError(err) && err.status === 401) return
      toast.error("Failed to update membership. Please try again.")
    } finally {
      setJoining(false)
    }
  }

  const isWaiting =
    club != null &&
    club.patron_waitlist_position != null &&
    club.patron_waitlist_position > 0

  const handleJoinWaitlist = async () => {
    if (!club || !id) return
    setWaitlistBusy(true)
    try {
      const res = await joinBookClubWaitlist(Number(id))
      if (res.success || res.status === 'waitlisted') {
        await refresh()
        toast.success(
          t('bookClubs.waitlist.joinedToast', { position: res.position ?? 0 }),
        )
      }
    } catch (err) {
      if (isApiError(err) && err.status === 401) return
      toast.error(t('bookClubs.waitlist.joinError'))
    } finally {
      setWaitlistBusy(false)
    }
  }

  const handleLeaveWaitlist = async () => {
    if (!club || !id) return
    setWaitlistBusy(true)
    try {
      await leaveBookClubWaitlist(Number(id))
      await refresh()
      toast.success(t('bookClubs.waitlist.leftToast'))
    } catch (err) {
      if (isApiError(err) && err.status === 401) return
      toast.error(t('bookClubs.waitlist.leaveError'))
    } finally {
      setWaitlistBusy(false)
    }
  }

  const tabs = [
    { id: 'about' as const, label: 'About', icon: BookOpen },
    { id: 'discussions' as const, label: 'Discussions', icon: MessageCircle },
    { id: 'meetings' as const, label: 'Meetings', icon: Calendar },
  ]

  if (loading) {
    return (
      <div className="space-y-6">
        <Link
          to="/book-clubs"
          className="inline-flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Book Clubs
        </Link>
        <div
          aria-busy="true"
          aria-live="polite"
          className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700"
        >
          <div className="motion-safe:animate-pulse space-y-4">
            <div className="h-7 w-1/2 bg-lsc-cream dark:bg-earth-700 rounded" />
            <div className="h-4 w-full bg-lsc-cream dark:bg-earth-700 rounded" />
            <div className="h-4 w-3/4 bg-lsc-cream dark:bg-earth-700 rounded" />
            <div className="flex gap-2 pt-2">
              <div className="h-7 w-28 bg-lsc-cream dark:bg-earth-700 rounded-full" />
              <div className="h-7 w-36 bg-lsc-cream dark:bg-earth-700 rounded-full" />
            </div>
          </div>
          <span className="sr-only">Loading book club details</span>
        </div>
      </div>
    )
  }

  if (error || !club) {
    return (
      <div className="space-y-6">
        <Link
          to="/book-clubs"
          className="inline-flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Book Clubs
        </Link>
        <EmptyState
          icon={BookOpen}
          title={t('bookClubDetail.bookClubNotFound')}
          description={error || 'This book club may have been removed or is no longer available.'}
          primaryAction={{ label: 'Browse Book Clubs', href: '/book-clubs' }}
          size="lg"
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <Link
        to="/book-clubs"
        className="inline-flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Book Clubs
      </Link>

      {/* Club Header */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {club.name}
            </h1>
            {club.description && (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 max-w-2xl">
                {club.description}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-3 mt-3">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 rounded-full text-sm">
                <Users className="w-4 h-4" />
                {club.max_members != null ? `${club.member_count} members · capacity ${club.max_members}` : `${club.member_count} members`}
              </span>
              {(() => {
                const badge = patronCapacityBadge(
                  {
                    currentMemberCount: club.current_member_count ?? club.member_count,
                    maxMembers: club.max_members,
                    waitlistCount: club.waitlist_count ?? 0,
                    isFull: club.is_full ?? false,
                  },
                  waitlistEnabled,
                )
                if (!badge || !club.is_full) return null
                return (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300 rounded-full text-sm font-medium">
                    {badge}
                  </span>
                )
              })()}
              {club.meeting_frequency && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 rounded-full text-sm">
                  <Calendar className="w-4 h-4" />
                  {club.meeting_frequency} meetings
                </span>
              )}
            </div>
          </div>
          {/*
            Join button state machine (PR #914 capacity fields):
            - member -> "Leave Club"
            - not member, club not full (or uncapped) -> "Join Club"
            - not member, full, not waiting, flag on -> "Join Waitlist"
            - not member, full, waiting -> position + "Leave waitlist"
            When the waitlist flag is OFF the full+not-member case keeps
            the plain "Join Club" button (server still 409s a full club,
            surfaced via the existing membership-error toast).
          */}
          {club.is_member ? (
            <Button variant="primary" onClick={handleJoinLeave} disabled={joining}>
              {joining ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <UserMinus />
              )}
              Leave Club
            </Button>
          ) : waitlistEnabled && isWaiting ? (
            <div className="flex flex-col items-stretch gap-1.5 sm:items-end">
              <span
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/80 dark:text-lsc-cream/80 rounded-full text-sm"
                aria-live="polite"
              >
                <Clock className="w-4 h-4" aria-hidden="true" />
                {t('bookClubs.waitlist.position', {
                  position: club.patron_waitlist_position ?? 0,
                })}
              </span>
              <Button
                variant="ghost"
                onClick={handleLeaveWaitlist}
                disabled={waitlistBusy}
              >
                {waitlistBusy ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <UserMinus />
                )}
                {waitlistBusy
                  ? t('bookClubs.waitlist.leaving')
                  : t('bookClubs.waitlist.leave')}
              </Button>
            </div>
          ) : waitlistEnabled && club.is_full ? (
            <Button
              variant="primary"
              onClick={handleJoinWaitlist}
              disabled={waitlistBusy}
            >
              {waitlistBusy ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <UserPlus />
              )}
              {waitlistBusy
                ? t('bookClubs.waitlist.joining')
                : t('bookClubs.waitlist.join')}
            </Button>
          ) : (
            <Button variant="primary" onClick={handleJoinLeave} disabled={joining}>
              {joining ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <UserPlus />
              )}
              Join Club
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div
        role="tablist"
        aria-label="Book club sections"
        onKeyDown={(e) => {
          const idx = tabs.findIndex((t) => t.id === activeTab)
          let next = idx
          if (e.key === 'ArrowRight') next = (idx + 1) % tabs.length
          else if (e.key === 'ArrowLeft') next = (idx - 1 + tabs.length) % tabs.length
          else if (e.key === 'Home') next = 0
          else if (e.key === 'End') next = tabs.length - 1
          else return
          e.preventDefault()
          const nextTab = tabs[next]
          if (!nextTab) return
          setActiveTab(nextTab.id)
          document.getElementById(`tab-${nextTab.id}`)?.focus()
        }}
        className="flex gap-2 bg-lsc-white dark:bg-earth-800 rounded-xl p-1.5 shadow-sm border border-lsc-border dark:border-earth-700"
      >
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              role="tab"
              aria-selected={isActive}
              aria-controls={`panel-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-lsc-rose text-white'
                  : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      <div
        role="tabpanel"
        id="panel-about"
        aria-labelledby="tab-about"
        hidden={activeTab !== 'about'}
        className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700"
      >
        {activeTab === 'about' && (
          <div className="space-y-6">
            {/* Members — hidden from anonymous callers (API returns null) */}
            {club.members === null || club.members === undefined ? (
              <EmptyState
                icon={Users}
                title="Sign in to see members"
                description="Sign in to see members and club details."
                size="md"
              />
            ) : (
              <div>
                <h2 className="font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream mb-3">
                  Members ({club.members.length})
                </h2>
                {club.members.length > 0 ? (
                  <div className="grid sm:grid-cols-2 gap-3">
                    {club.members.map((member) => {
                      const name = member.display_name || `Member #${member.user_id}`
                      return (
                        <div
                          key={member.id}
                          className="flex items-center gap-3 p-3 rounded-lg bg-lsc-cream/50 dark:bg-earth-700/50"
                        >
                          <div className="w-9 h-9 rounded-full bg-lsc-rose/20 flex items-center justify-center text-lsc-rose font-bold text-sm">
                            {name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">
                              {name}
                            </p>
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 capitalize">
                              {member.role}
                            </p>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    No members yet. Be the first to join!
                  </p>
                )}
              </div>
            )}
          </div>
        )}

      </div>

      <div
        role="tabpanel"
        id="panel-discussions"
        aria-labelledby="tab-discussions"
        hidden={activeTab !== 'discussions'}
        className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700"
      >
        {activeTab === 'discussions' && (
          <EmptyState
            icon={MessageCircle}
            title="No discussions yet"
            description="Start a conversation about the current book or share your reading thoughts."
            size="md"
            showTip
          />
        )}
      </div>

      <div
        role="tabpanel"
        id="panel-meetings"
        aria-labelledby="tab-meetings"
        hidden={activeTab !== 'meetings'}
        className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700"
      >
        {activeTab === 'meetings' && (() => {
          // Handle both patron (upcoming_meetings) and admin (meetings) response shapes
          const meetingsList = (club.upcoming_meetings || []).map((m) => ({
            id: m.id,
            title: m.title,
            date: m.scheduled_at,
            location: m.location,
          }))
          // Also include raw meetings from admin shape if upcoming_meetings is empty
          const rawMeetings = (!meetingsList.length && club.meetings)
            ? club.meetings
                .filter((m) => m.status !== 'cancelled' && new Date(m.meeting_date) > new Date())
                .map((m) => ({
                  id: m.id,
                  title: m.title,
                  date: m.meeting_date,
                  location: m.location,
                }))
            : []
          const allMeetings = meetingsList.length ? meetingsList : rawMeetings
          allMeetings.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

          // Calendar subscription URLs. webcal:// triggers the OS calendar
          // handoff in most browsers; https:// is the copy-pasteable form
          // for Google Calendar / Outlook web add-by-URL flows.
          const icsPath = `/api/v1/book-clubs/${club.id}/meetings.ics`
          const host = typeof window !== 'undefined' ? window.location.host : 'l30.org'
          const webcalUrl = `webcal://${host}${icsPath}`
          const httpsUrl = `https://${host}${icsPath}`
          const handleCopyIcsUrl = async () => {
            try {
              await navigator.clipboard.writeText(httpsUrl)
              // TODO(i18n): add bookClubs.meetings.copiedToast key
              toast.success('Calendar URL copied to clipboard')
            } catch {
              toast.error('Could not copy. Long-press the URL to copy manually.')
            }
          }

          return (
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-4 pb-4 border-b border-lsc-border dark:border-earth-700">
              <a
                href={webcalUrl}
                className="inline-flex items-center justify-center gap-2 px-3 py-2 text-sm min-h-[44px] bg-lsc-rose hover:bg-lsc-rose/90 text-white shadow-md hover:shadow-lg rounded-xl font-semibold border-2 border-transparent focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 transition-all duration-200"
              >
                <CalendarPlus className="w-4 h-4" aria-hidden="true" />
                Subscribe to calendar
              </a>
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<LinkIcon className="w-4 h-4" />}
                onClick={handleCopyIcsUrl}
              >
                Copy URL
              </Button>
              <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 ml-1">
                Adds upcoming meetings to Apple Calendar, Google Calendar, or Outlook.
              </span>
            </div>
            {allMeetings.length > 0 ? (
              <div className="space-y-3">
                {allMeetings.map((mtg) => (
                  <div
                    key={mtg.id}
                    className="flex items-start gap-4 p-4 rounded-lg bg-lsc-cream/50 dark:bg-earth-700/50"
                  >
                    <div className="w-12 h-12 rounded-xl bg-lsc-rose/10 flex flex-col items-center justify-center text-lsc-rose shrink-0">
                      <span className="text-xs font-medium">
                        {new Date(mtg.date).toLocaleDateString(getCurrentLocale(), { month: 'short' })}
                      </span>
                      <span className="text-lg font-bold leading-tight">
                        {new Date(mtg.date).getDate()}
                      </span>
                    </div>
                    <div>
                      <h2 className="font-medium text-base text-lsc-dark dark:text-lsc-cream">
                        {mtg.title || 'Book Club Meeting'}
                      </h2>
                      <div className="flex flex-wrap items-center gap-3 mt-1">
                        <span className="inline-flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          <Clock className="w-3.5 h-3.5" />
                          {new Date(mtg.date).toLocaleTimeString(getCurrentLocale(), {
                            hour: 'numeric',
                            minute: '2-digit',
                          })}
                        </span>
                        {mtg.location && (
                          <span className="inline-flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            <MapPin className="w-3.5 h-3.5" />
                            {mtg.location}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={Calendar}
                title="No upcoming meetings"
                description="Meeting schedules will appear here once they're set up."
                size="md"
                showTip
              />
            )}
          </div>
          )
        })()}
      </div>
    </div>
  )
}
