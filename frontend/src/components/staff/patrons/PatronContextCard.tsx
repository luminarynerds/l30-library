/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useEffect, useState } from "react"
import { fetchApi } from '@/api/fetchApi';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Heart,
  AlertCircle,
  Phone,
  Mail,
  Loader2,
  Globe,
  Accessibility,
  BookOpen,
  Trophy,
} from "lucide-react"
import { useTranslation, formatCurrency } from '@/i18n'

interface PatronContextCardProps {
  patronId: number
}

interface AccountAlert {
  alert_type: string
  severity: "info" | "warning" | "critical"
  message: string
  details?: Record<string, unknown>
}

interface StaffNote {
  category: string
  content: string
  priority: string
  created_at?: string
}

interface CheckoutItem {
  id: number
  item_id: number
  title: string
  author?: string
  due_date: string
}

interface HoldItem {
  id: number
  item_id: number
  title: string
  author?: string
  status: string
  position?: number
  expires_at?: string
}

interface PatronContextCardData {
  id: number
  first_name: string
  last_name: string
  preferred_name?: string
  pronouns?: string
  photo_url?: string
  library_card?: string
  patron_status: string
  account_alerts: AccountAlert[]
  email: string
  phone?: string
  language_preference?: string
  accessibility_needs?: string
  created_at: string
  last_login?: string
  checkout_frequency: string
  total_checkouts_lifetime: number
  checkouts: {
    total_count: number
    active_count: number
    overdue_count: number
    due_soon_count: number
    due_soon_items: CheckoutItem[]
  }
  holds: {
    total_pending: number
    ready_for_pickup_count: number
    ready_items: HoldItem[]
  }
  fines?: {
    total_owed: number
    unpaid_count: number
  }
  reading_preferences: Array<{ genre: string; count: number }>
  staff_notes: StaffNote[]
  loyalty_status: {
    total_xp: number
    current_level: string
    achievements_earned: number
    achievements_list: Array<{ name: string; icon?: string; earned_at: string }>
  }
}

const severityColors: Record<string, { bg: string; border: string; icon: React.ReactNode }> = {
  critical: {
    bg: "bg-status-danger-50 dark:bg-status-danger-900/20",
    border: "border-status-danger-200 dark:border-status-danger-800",
    icon: <AlertTriangle className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" />,
  },
  warning: {
    bg: "bg-status-warning-50 dark:bg-status-warning-900/20",
    border: "border-status-warning-200 dark:border-status-warning-800",
    icon: <AlertCircle className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400" />,
  },
  info: {
    bg: "bg-earth-50 dark:bg-earth-800/20",
    border: "border-lsc-border dark:border-earth-700",
    icon: <CheckCircle className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />,
  },
}

const priorityColors: Record<string, string> = {
  urgent: "bg-status-danger-100 dark:bg-status-danger-900 text-status-danger-800 dark:text-status-danger-200 border border-status-danger-300 dark:border-status-danger-700",
  high: "bg-status-warning-100 dark:bg-status-warning-900 text-status-warning-800 dark:text-status-warning-200 border border-status-warning-300 dark:border-status-warning-700",
  normal: "bg-earth-100 dark:bg-earth-800 text-earth-800 dark:text-lsc-rose-light/80 border border-lsc-border dark:border-earth-600",
  low: "bg-earth-100 dark:bg-earth-800 text-earth-800 dark:text-earth-200 border border-lsc-border dark:border-earth-700",
}

export function PatronContextCard({ patronId }: PatronContextCardProps) {
  const { t, language } = useTranslation()
  const [data, setData] = useState<PatronContextCardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchContextCard = async () => {
      try {
        setLoading(true)
        const contextData = await fetchApi(`/staff/patrons/${patronId}/context-card`)
        setData(contextData)
        setError(null)
      } catch (err: unknown) {
        const message =
          err instanceof Error
            ? err.message
            : (err as { message?: string })?.message ||
              "We couldn't load patron details. Please try again."
        setError(message)
      } finally {
        setLoading(false)
      }
    }

    fetchContextCard()
  }, [patronId])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6 text-status-danger-700 dark:text-status-danger-400">
        <p className="font-medium">{t('components.staff.patronContextCard.errorLoadingPatronContext')}</p>
        <p className="text-sm mt-1">{error || "Patron not found"}</p>
      </div>
    )
  }

  const displayName = data.preferred_name || `${data.first_name} ${data.last_name}`
  const patronStatusColor =
    data.patron_status === "active"
      ? "text-status-success-600 dark:text-status-success-400"
      : data.patron_status === "blocked"
        ? "text-status-danger-600 dark:text-status-danger-400"
        : data.patron_status === "suspended"
          ? "text-status-warning-600 dark:text-status-warning-400"
          : "text-lsc-dark/70 dark:text-lsc-cream/70"

  const frequencyEmoji =
    data.checkout_frequency === "very_active"
      ? "🔥"
      : data.checkout_frequency === "active"
        ? "⭐"
        : data.checkout_frequency === "moderate"
          ? "📚"
          : "😴"

  return (
    <div className="space-y-4">
      {/* Header with Photo and Identity */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row gap-6">
          {/* Photo */}
          {data.photo_url && (
            <div className="flex-shrink-0">
              <img
                src={data.photo_url}
                alt={displayName}
                className="w-24 h-24 rounded-full object-cover border-2 border-lsc-rose"
              />
            </div>
          )}

          {/* Identity Info */}
          <div className="flex-1">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                  {displayName}
                </h2>
                {data.pronouns && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    {data.pronouns}
                  </p>
                )}
              </div>
              <div className="text-right">
                <span
                  className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${patronStatusColor} capitalize`}
                >
                  {data.patron_status}
                </span>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
              <div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Member Since</p>
                <p className="text-sm font-medium">
                  {new Date(data.created_at).toLocaleDateString()}
                </p>
              </div>
              <div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Activity</p>
                <p className="text-sm font-medium">
                  {frequencyEmoji} {data.checkout_frequency}
                </p>
              </div>
              <div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Lifetime Checkouts</p>
                <p className="text-sm font-medium">{data.total_checkouts_lifetime}</p>
              </div>
              {data.library_card && (
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Card #</p>
                  <p className="text-sm font-mono font-medium">{data.library_card}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Account Alerts - Prominently Displayed */}
      {data.account_alerts.length > 0 && (
        <div className="space-y-2">
          {data.account_alerts.map((alert, idx) => {
            const colors = severityColors[alert.severity]!
            return (
              <div
                key={idx}
                className={`${colors.bg} border-l-4 border-current ${colors.border} rounded-lg p-3 flex items-start gap-3`}
              >
                {colors.icon}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">
                    {alert.message}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Current Checkouts */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="w-5 h-5 text-lsc-rose" />
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Checkouts</h3>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Active</span>
              <span className="font-medium">{data.checkouts.active_count}</span>
            </div>
            {data.checkouts.overdue_count > 0 && (
              <div className="flex justify-between text-sm text-status-danger-600 dark:text-status-danger-400">
                <span>Overdue</span>
                <span className="font-medium">{data.checkouts.overdue_count}</span>
              </div>
            )}
            {data.checkouts.due_soon_count > 0 && (
              <div className="flex justify-between text-sm text-status-warning-600 dark:text-status-warning-400">
                <span>Due Soon (3 days)</span>
                <span className="font-medium">{data.checkouts.due_soon_count}</span>
              </div>
            )}

            {data.checkouts.due_soon_items.length > 0 && (
              <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700 space-y-2">
                <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Due Soon:</p>
                {data.checkouts.due_soon_items.slice(0, 3).map((item) => (
                  <div key={item.id} className="text-xs bg-status-warning-50 dark:bg-status-warning-900/20 p-2 rounded border border-status-warning-200 dark:border-status-warning-800">
                    <p className="font-medium truncate" title={item.title}>{item.title}</p>
                    <p className="text-status-warning-700 dark:text-status-warning-300">
                      Due: {new Date(item.due_date).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Holds Ready for Pickup */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <Heart className="w-5 h-5 text-lsc-rose" />
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Holds</h3>
          </div>
          <div className="space-y-2">
            {data.holds.ready_for_pickup_count > 0 && (
              <div className="flex justify-between text-sm text-status-success-600 dark:text-status-success-400">
                <span>Ready for Pickup</span>
                <span className="font-medium">{data.holds.ready_for_pickup_count}</span>
              </div>
            )}
            {data.holds.total_pending > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Pending</span>
                <span className="font-medium">{data.holds.total_pending}</span>
              </div>
            )}

            {data.holds.ready_items.length > 0 && (
              <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700 space-y-2">
                <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Ready:</p>
                {data.holds.ready_items.slice(0, 3).map((item) => (
                  <div key={item.id} className="text-xs bg-status-success-50 dark:bg-status-success-900/20 p-2 rounded border border-status-success-200 dark:border-status-success-800">
                    <p className="font-medium truncate" title={item.title}>{item.title}</p>
                    <p className="text-status-success-700 dark:text-status-success-300">{t('components.staff.patronContextCard.readyToPickUp')}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Fines */}
      {data.fines && data.fines.total_owed > 0 && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
            <h3 className="font-serif font-semibold text-status-danger-900 dark:text-status-danger-100">Outstanding Fines</h3>
          </div>
          <p className="text-lg font-bold text-status-danger-700 dark:text-status-danger-300">
            {formatCurrency(Number(data.fines.total_owed), language, 'USD')}
          </p>
          <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">
            {data.fines.unpaid_count} unpaid fine(s)
          </p>
        </div>
      )}

      {/* Reading Preferences */}
      {data.reading_preferences.length > 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="w-5 h-5 text-lsc-rose" />
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Reading Preferences</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {data.reading_preferences.map((pref) => (
              <span
                key={pref.genre}
                className="px-3 py-1 bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose rounded-full text-sm font-medium"
              >
                {pref.genre} ({pref.count})
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Loyalty Status */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <Trophy className="w-5 h-5 text-lsc-rose" />
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Loyalty Status</h3>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Level</p>
            <p className="text-lg font-bold text-lsc-rose">{data.loyalty_status.current_level}</p>
          </div>
          <div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">XP</p>
            <p className="text-lg font-bold">{data.loyalty_status.total_xp}</p>
          </div>
          {data.loyalty_status.achievements_earned > 0 && (
            <div>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Achievements</p>
              <p className="text-lg font-bold">{data.loyalty_status.achievements_earned}</p>
            </div>
          )}
        </div>

        {data.loyalty_status.achievements_list.length > 0 && (
          <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700">
            <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Recent Achievements:</p>
            <div className="space-y-1">
              {data.loyalty_status.achievements_list.slice(0, 3).map((ach, idx) => (
                <div key={idx} className="text-xs">
                  <p className="font-medium">{ach.name}</p>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    {new Date(ach.earned_at).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Staff Notes */}
      {data.staff_notes.length > 0 && (
        <div className="space-y-2">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-lsc-rose" />
            Staff Notes
          </h3>
          {data.staff_notes.map((note, idx) => (
            <div
              key={idx}
              className={`rounded-lg p-3 ${priorityColors[note.priority.toLowerCase()] || priorityColors.normal}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium opacity-75">{note.category.toUpperCase()}</p>
                  <p className="text-sm mt-1">{note.content}</p>
                </div>
              </div>
              {note.created_at && (
                <p className="text-xs opacity-60 mt-2">
                  {new Date(note.created_at).toLocaleDateString()}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Contact Info */}
      {(data.phone || data.language_preference || data.accessibility_needs) && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Quick Info</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-start gap-2">
              <Mail className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" />
              <span className="truncate text-lsc-dark dark:text-lsc-cream" title={data.email}>{data.email}</span>
            </div>
            {data.phone && (
              <div className="flex items-start gap-2">
                <Phone className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" />
                <span className="text-lsc-dark dark:text-lsc-cream">{data.phone}</span>
              </div>
            )}
            {data.language_preference && (
              <div className="flex items-start gap-2">
                <Globe className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" />
                <span className="text-lsc-dark dark:text-lsc-cream">{data.language_preference}</span>
              </div>
            )}
            {data.accessibility_needs && (
              <div className="flex items-start gap-2">
                <Accessibility className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" />
                <span className="text-lsc-dark dark:text-lsc-cream">{data.accessibility_needs}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Last Visit */}
      {data.last_login && (
        <div className="text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70 pt-2 border-t border-lsc-border dark:border-earth-700">
          <Clock className="w-4 h-4 inline mr-1" />
          Last login: {new Date(data.last_login).toLocaleDateString()} at{" "}
          {new Date(data.last_login).toLocaleTimeString()}
        </div>
      )}
    </div>
  )
}