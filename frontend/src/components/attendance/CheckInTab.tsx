/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CreditCard, UserPlus, Hash, Mail, Lock, QrCode,
  UserCheck, Loader2, CheckCircle2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getAttendanceSession,
  closeAttendanceSession,
  checkInLibraryCard,
  checkInWalkIn,
  updateHeadCount,
  getSessionCheckIns,
  sendSurveys,
} from '../../api/attendance-api'
import { useTranslation } from '@/i18n'
import { clean } from '@/lib/utils'
import { AGE_RANGES, METHOD_LABELS } from './attendance-data'
import { StatCard } from './StatCard'
import { StatusBadge } from './StatusBadge'

interface CheckInTabProps {
  selectedSessionId: number | null
  onSelectSession: (id: number | null) => void
}

export function CheckInTab({
  selectedSessionId,
  onSelectSession: _onSelectSession,
}: CheckInTabProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [checkInMode, setCheckInMode] = useState<'card' | 'walkin' | 'headcount'>('card')
  const [cardNumber, setCardNumber] = useState('')
  const [walkInName, setWalkInName] = useState('')
  const [walkInEmail, setWalkInEmail] = useState('')
  const [walkInAge, setWalkInAge] = useState('unknown')
  const [headCount, setHeadCount] = useState(0)

  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: ['attendance-session', selectedSessionId],
    queryFn: () => getAttendanceSession(selectedSessionId!),
    enabled: !!selectedSessionId,
  })

  const { data: checkIns, isLoading: checkInsLoading } = useQuery({
    queryKey: ['attendance-checkins', selectedSessionId],
    queryFn: () => getSessionCheckIns(selectedSessionId!),
    enabled: !!selectedSessionId,
  })

  const cardMutation = useMutation({
    mutationFn: (data: { session_id: number; library_card_number: string }) =>
      checkInLibraryCard(data),
    onSuccess: (result) => {
      toast.success(
        result.patron_name
          ? `${result.patron_name} checked in!${result.is_repeat_attendee ? ' (Repeat visitor!)' : ''}`
          : 'Card scanned successfully!'
      )
      setCardNumber('')
      queryClient.invalidateQueries({ queryKey: ['attendance-checkins', selectedSessionId] })
      queryClient.invalidateQueries({ queryKey: ['attendance-session', selectedSessionId] })
    },
    onError: (err: Error) => toast.error(err.message || t('toast.attendanceTracking.checkinFailed')),
  })

  const walkInMutation = useMutation({
    mutationFn: (data: { session_id: number; guest_name?: string; guest_email?: string; age_range: string }) =>
      checkInWalkIn(data),
    onSuccess: (result) => {
      toast.success(t('toast.attendanceTracking.walkinAddedisrepeatattendeerepeatvisitor', { isrepeatattendeeRepeatvisitor: result.is_repeat_attendee ? ' (Repeat visitor!)' : '' }))
      setWalkInName('')
      setWalkInEmail('')
      setWalkInAge('unknown')
      queryClient.invalidateQueries({ queryKey: ['attendance-checkins', selectedSessionId] })
      queryClient.invalidateQueries({ queryKey: ['attendance-session', selectedSessionId] })
    },
    onError: (err: Error) => toast.error(err.message || t('toast.attendanceTracking.failedToAddWalkin')),
  })

  const headCountMutation = useMutation({
    mutationFn: (data: { session_id: number; total: number }) => updateHeadCount(data),
    onSuccess: () => {
      toast.success(t('toast.attendanceTracking.headCountUpdated'))
      queryClient.invalidateQueries({ queryKey: ['attendance-session', selectedSessionId] })
    },
    onError: (err: Error) => toast.error(err.message || t('toast.attendanceTracking.failedToUpdateHeadCount')),
  })

  const closeMutation = useMutation({
    mutationFn: (id: number) => closeAttendanceSession(id),
    onSuccess: () => {
      toast.success(t('toast.attendanceTracking.sessionClosed'))
      queryClient.invalidateQueries({ queryKey: ['attendance-session', selectedSessionId] })
      queryClient.invalidateQueries({ queryKey: ['attendance-sessions'] })
    },
    onError: (err: Error) => toast.error(err.message || t('toast.attendanceTracking.failedToCloseSession')),
  })

  const surveyMutation = useMutation({
    mutationFn: (id: number) => sendSurveys(id),
    onSuccess: (result) => {
      toast.success(t('toast.attendanceTracking.surveysSentToTotalsentAttendees', { totalsent: result.total_sent }))
    },
    onError: (err: Error) => toast.error(err.message || t('toast.attendanceTracking.failedToSendSurveys')),
  })

  if (!selectedSessionId) {
    return (
      <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
        <UserCheck size={40} className="mx-auto text-earth-600 dark:text-earth-600 mb-3" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('attendanceTracking.selectASessionFromThe')}</p>
      </div>
    )
  }

  if (sessionLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" size={24} />
      </div>
    )
  }

  if (!session) {
    return <p className="text-status-danger-500 text-center py-8">Session not found.</p>
  }

  const isOpen = session.status === 'open'

  return (
    <div className="space-y-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">{session.session_name}</h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {session.session_date} &middot; <StatusBadge status={session.status} />
            </p>
          </div>
          <div className="flex items-center gap-2">
            {session.survey_enabled && session.status !== 'open' && !session.survey_sent_at && (
              <button
                onClick={() => surveyMutation.mutate(session.id)}
                disabled={surveyMutation.isPending}
                className="flex items-center gap-1 px-3 py-1.5 text-sm bg-category-600 text-white rounded-lg hover:bg-category-700 disabled:opacity-50"
              >
                <Mail size={14} />
                Send Surveys
              </button>
            )}
            {isOpen && (
              <button
                onClick={() => closeMutation.mutate(session.id)}
                disabled={closeMutation.isPending}
                className="flex items-center gap-1 px-3 py-1.5 text-sm bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 disabled:opacity-50"
              >
                <Lock size={14} />
                Close Session
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mt-4">
          <StatCard label="Total" value={session.effective_total} />
          <StatCard label="Card Scans" value={session.total_card_scans} />
          <StatCard label="Walk-Ins" value={session.total_walk_ins} />
          <StatCard label="QR Scans" value={session.total_qr_scans} />
          <StatCard label="Head Count" value={session.head_count_total} />
        </div>

        {isOpen && (
          <div className="mt-4 p-3 bg-earth-50 dark:bg-earth-800/20 rounded-lg border border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light text-sm">
              <QrCode size={16} />
              <span className="font-medium">Self-Service QR Token:</span>
              <code className="bg-earth-100 dark:bg-earth-800 px-2 py-0.5 rounded text-xs font-mono">
                {session.qr_code_token}
              </code>
            </div>
            <p className="text-xs text-lsc-rose dark:text-lsc-rose-light mt-1">
              Display this token as a QR code at your event for attendees to self-check-in via the patron app.
            </p>
          </div>
        )}
      </div>

      {isOpen && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700">
          <div className="flex gap-2 mb-4">
            {[
              { id: 'card' as const, label: 'Library Card', icon: <CreditCard size={16} /> },
              { id: 'walkin' as const, label: 'Walk-In', icon: <UserPlus size={16} /> },
              { id: 'headcount' as const, label: 'Head Count', icon: <Hash size={16} /> },
            ].map((mode) => (
              <button
                key={mode.id}
                onClick={() => setCheckInMode(mode.id)}
                className={`flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border ${
                  checkInMode === mode.id
                    ? 'bg-earth-50 border-lsc-border text-lsc-rose dark:bg-earth-800/30 dark:border-earth-600 dark:text-lsc-rose-light'
                    : 'border-lsc-border text-lsc-dark/70 hover:bg-lsc-cream dark:border-earth-600 dark:text-lsc-cream/70'
                }`}
              >
                {mode.icon}
                {mode.label}
              </button>
            ))}
          </div>

          {checkInMode === 'card' && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (cardNumber.trim()) {
                  cardMutation.mutate({ session_id: session.id, library_card_number: cardNumber.trim() })
                }
              }}
              className="flex gap-3"
            >
              <div className="flex-1">
                <input
                  type="text"
                  value={cardNumber}
                  onChange={(e) => setCardNumber(e.target.value)}
                  placeholder={t('attendanceTracking.scanOrTypeLibraryCard')}
                  autoFocus
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-sm bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <button
                type="submit"
                disabled={!cardNumber.trim() || cardMutation.isPending}
                className="px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 text-sm font-medium disabled:opacity-50 flex items-center gap-1"
              >
                {cardMutation.isPending ? <Loader2 size={14} className="motion-safe:animate-spin" /> : <CreditCard size={14} />}
                Scan In
              </button>
            </form>
          )}

          {checkInMode === 'walkin' && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                walkInMutation.mutate(clean({
                  session_id: session.id,
                  guest_name: walkInName || undefined,
                  guest_email: walkInEmail || undefined,
                  age_range: walkInAge,
                }))
              }}
              className="space-y-3"
            >
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <input
                  type="text"
                  value={walkInName}
                  onChange={(e) => setWalkInName(e.target.value)}
                  placeholder={t('placeholder.attendanceTracking.nameOptional')}
                  className="px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-sm bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
                <input
                  type="email"
                  value={walkInEmail}
                  onChange={(e) => setWalkInEmail(e.target.value)}
                  placeholder={t('attendanceTracking.emailForSurveyOptional')}
                  className="px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-sm bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
                <select
                  value={walkInAge}
                  onChange={(e) => setWalkInAge(e.target.value)}
                  className="px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-sm bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                >
                  {AGE_RANGES.map((ar) => (
                    <option key={ar.value} value={ar.value}>{ar.label}</option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                disabled={walkInMutation.isPending}
                className="px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 text-sm font-medium disabled:opacity-50 flex items-center gap-1"
              >
                {walkInMutation.isPending ? <Loader2 size={14} className="motion-safe:animate-spin" /> : <UserPlus size={14} />}
                Add Walk-In
              </button>
            </form>
          )}

          {checkInMode === 'headcount' && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                headCountMutation.mutate({ session_id: session.id, total: headCount })
              }}
              className="flex gap-3 items-end"
            >
              <div>
                <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Total Count</label>
                <input
                  type="number"
                  value={headCount}
                  onChange={(e) => setHeadCount(parseInt(e.target.value) || 0)}
                  min={0}
                  className="w-32 px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-sm bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <button
                type="submit"
                disabled={headCountMutation.isPending}
                className="px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 text-sm font-medium disabled:opacity-50 flex items-center gap-1"
              >
                {headCountMutation.isPending ? <Loader2 size={14} className="motion-safe:animate-spin" /> : <Hash size={14} />}
                Update Count
              </button>
            </form>
          )}
        </div>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700">
        <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          Check-Ins ({checkIns?.length || 0})
        </h3>
        {checkInsLoading ? (
          <div className="flex justify-center py-4">
            <Loader2 className="motion-safe:animate-spin text-earth-600 dark:text-earth-600" size={20} />
          </div>
        ) : checkIns && checkIns.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-lsc-dark/70 dark:text-lsc-cream/70 border-b dark:border-earth-700">
                  <th className="py-2 pr-4">Name</th>
                  <th className="py-2 pr-4">Method</th>
                  <th className="py-2 pr-4">Age Range</th>
                  <th className="py-2 pr-4">Time</th>
                  <th className="py-2">Repeat?</th>
                </tr>
              </thead>
              <tbody>
                {checkIns.map((ci) => (
                  <tr key={ci.id} className="border-b dark:border-earth-700 last:border-0">
                    <td className="py-2 pr-4 font-medium text-lsc-dark dark:text-lsc-cream">
                      {ci.patron_name || ci.guest_name || ci.library_card_number || 'Anonymous'}
                    </td>
                    <td className="py-2 pr-4">
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                        {METHOD_LABELS[ci.check_in_method] || ci.check_in_method}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-lsc-dark/70 dark:text-lsc-cream/70">{ci.age_range}</td>
                    <td className="py-2 pr-4 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {new Date(ci.checked_in_at).toLocaleTimeString()}
                    </td>
                    <td className="py-2">
                      {ci.is_repeat_attendee ? (
                        <span className="inline-flex items-center gap-1 text-xs text-status-success-700 dark:text-status-success-400">
                          <CheckCircle2 size={12} />
                          {ci.previous_visit_count} visits
                        </span>
                      ) : (
                        <span className="text-xs text-earth-600 dark:text-earth-400">New</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-4">No check-ins yet.</p>
        )}
      </div>
    </div>
  )
}
