/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Loader2, Download, Trash2, Eye, EyeOff, ChevronDown, ChevronUp } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import { fetchApi } from '@/lib/api-client'
import { useTranslation } from '@/i18n'

type TFunction = (key: string, paramsOrFallback?: Record<string, unknown> | string) => string

interface DataExport {
  profile: Record<string, unknown>
  checkouts: Record<string, unknown>[]
  holds: Record<string, unknown>[]
  fines: Record<string, unknown>[]
  reading_history: Record<string, unknown>[]
  favorites: Record<string, unknown>[]
  reading_lists: Record<string, unknown>[]
  event_registrations: Record<string, unknown>[]
  ai_conversations: Record<string, unknown>[]
  ebook_checkouts: Record<string, unknown>[]
  privacy_change_history: Record<string, unknown>[]
  exported_at: string
}

interface PrivacySettings {
  track_reading_history: boolean
  discreet_receipts: boolean
  allow_staff_access_to_history: boolean
  notification_frequency: string
}

function Section({ title, count, children }: { title: string; count?: number; children: React.ReactNode }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-cream/50 dark:hover:bg-earth-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="font-medium text-lsc-dark dark:text-lsc-cream">{title}</span>
          {count != null && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-lsc-dark/[.06] dark:bg-lsc-cream/10 text-lsc-dark/70 dark:text-lsc-cream/60">
              {count} {count === 1 ? t('components.account.myDataTab.record', 'record') : t('components.account.myDataTab.records', 'records')}
            </span>
          )}
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50" /> : <ChevronDown className="w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50" />}
      </button>
      {open && <div className="px-4 pb-4 border-t border-lsc-border dark:border-earth-700">{children}</div>}
    </div>
  )
}

function ProfileField({ label, value }: { label: string; value: unknown }) {
  const { t } = useTranslation()
  if (value == null || value === '') return null
  const display = typeof value === 'boolean' ? (value ? t('common.yes', 'Yes') : t('common.no', 'No')) : String(value)
  return (
    <div className="flex justify-between py-1.5 border-b border-lsc-border/30 dark:border-earth-700/30 last:border-0">
      <span className="text-sm text-lsc-dark/60 dark:text-lsc-cream/50">{label}</span>
      <span className="text-sm text-lsc-dark dark:text-lsc-cream text-right max-w-[60%] break-words">{display}</span>
    </div>
  )
}

function DataTable({ rows, columns }: { rows: Record<string, unknown>[]; columns: { key: string; label: string }[] }) {
  const { t } = useTranslation()
  if (rows.length === 0) return <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50 py-2">{t('components.account.myDataTab.noRecords', 'No records')}</p>
  return (
    <div className="overflow-x-auto mt-2">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-lsc-border dark:border-earth-700">
            {columns.map(c => (
              <th key={c.key} className="text-left py-2 pr-4 text-lsc-dark/60 dark:text-lsc-cream/50 font-medium">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-lsc-border/20 dark:border-earth-700/20 last:border-0">
              {columns.map(c => (
                <td key={c.key} className="py-2 pr-4 text-lsc-dark dark:text-lsc-cream">
                  {row[c.key] == null ? '--' : String(row[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function getProfileLabels(t: TFunction): Record<string, string> {
  return {
    email: t('account.email', 'Email'),
    first_name: t('components.account.myDataTab.firstName', 'First name'),
    last_name: t('components.account.myDataTab.lastName', 'Last name'),
    phone: t('account.phone', 'Phone'),
    address: t('account.address', 'Address'),
    library_card: t('components.account.myDataTab.libraryCardLabel', 'Library card'),
    date_of_birth: t('components.account.myDataTab.dateOfBirth', 'Date of birth'),
    email_verified: t('components.account.myDataTab.emailVerified', 'Email verified'),
    track_reading_history: t('components.account.myDataTab.readingHistoryTracking', 'Reading history tracking'),
    language_preference: t('components.account.myDataTab.language', 'Language'),
    accessibility_needs: t('components.account.myDataTab.accessibilityNeeds', 'Accessibility needs'),
    preferred_contact_method: t('components.account.myDataTab.preferredContact', 'Preferred contact'),
    created_at: t('components.account.myDataTab.accountCreated', 'Account created'),
    last_login: t('components.account.myDataTab.lastSignIn', 'Last sign-in'),
  }
}

export function MyDataTab(): React.ReactElement {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [data, setData] = useState<DataExport | null>(null)
  const [privacy, setPrivacy] = useState<PrivacySettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (!token) return
    setLoading(true)
    setError(null)
    Promise.all([
      fetchApi<DataExport>('/privacy/export'),
      fetchApi<PrivacySettings>('/privacy/settings'),
    ])
      .then(([exportData, privacyData]) => {
        setData(exportData)
        setPrivacy(privacyData)
      })
      .catch(() => setError(t('components.account.myDataTab.loadError', 'Could not load your data right now. Please try again.')))
      .finally(() => setLoading(false))
  }, [token])

  const handleDownload = async () => {
    if (!token) return
    setDownloading(true)
    try {
      const full = await fetchApi<Record<string, unknown>>('/privacy/export/complete')
      const blob = new Blob([JSON.stringify(full, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `my-library-data-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setError(t('components.account.myDataTab.downloadError', 'Could not download your data. Please try again.'))
    } finally {
      setDownloading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12" role="status">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
        <span className="sr-only">{t('components.account.myDataTab.loadingData', 'Loading your data...')}</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="text-center py-12">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{error || t('components.account.myDataTab.somethingWentWrong', 'Something went wrong.')}</p>
        <button onClick={() => window.location.reload()} className="mt-4 text-lsc-rose hover:underline text-sm">
          {t('states.tryAgain', 'Try again')}
        </button>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('components.account.myDataTab.title', 'My Data')}</h2>
          <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
            {t('components.account.myDataTab.subtitle', 'Everything the library stores about you, in one place.')}
          </p>
        </div>
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
        >
          {downloading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Download className="w-4 h-4" />}
          {t('components.account.myDataTab.downloadAll', 'Download all')}
        </button>
      </div>

      {/* Privacy settings summary */}
      {privacy && (
        <div className="mb-6 p-4 bg-cream/50 dark:bg-earth-800/50 rounded-xl">
          <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('components.account.myDataTab.privacySettingsTitle', 'Your privacy settings')}</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
            <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
              {privacy.track_reading_history ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
              {t('components.account.myDataTab.readingHistoryTitle', 'Reading history')}: {privacy.track_reading_history ? t('components.account.myDataTab.tracked', 'tracked') : t('components.account.myDataTab.notTracked', 'not tracked')}
            </div>
            <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
              {privacy.discreet_receipts ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              {t('components.account.myDataTab.receiptsLabel', 'Receipts')}: {privacy.discreet_receipts ? t('components.account.myDataTab.discreetTitlesHidden', 'discreet (titles hidden)') : t('components.account.myDataTab.fullDetails', 'full details')}
            </div>
            <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
              {privacy.allow_staff_access_to_history ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
              {t('components.account.myDataTab.staffAccessLabel', 'Staff access to history')}: {privacy.allow_staff_access_to_history ? t('components.account.myDataTab.allowedLabel', 'allowed') : t('components.account.myDataTab.offLabel', 'off')}
            </div>
            <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('components.account.myDataTab.notificationsFrequencyLabel', 'Notifications')}: {privacy.notification_frequency || t('components.account.myDataTab.defaultLabel', 'default')}
            </div>
          </div>
          <p className="text-xs text-lsc-dark/40 dark:text-lsc-cream/40 mt-2">
            {t('components.account.myDataTab.changeInSettings', 'Change these in Settings > Privacy.')}
          </p>
        </div>
      )}

      <div className="space-y-3">
        {/* Profile */}
        <Section title={t('components.account.myDataTab.profileInfoTitle', 'Profile information')}>
          <div className="mt-2">
            {Object.entries(getProfileLabels(t)).map(([key, label]) => (
              <ProfileField key={key} label={label} value={data.profile[key]} />
            ))}
          </div>
        </Section>

        {/* Checkouts */}
        <Section title={t('components.account.myDataTab.checkoutHistoryTitle', 'Checkout history')} count={data.checkouts.length}>
          <DataTable
            rows={data.checkouts}
            columns={[
              { key: 'status', label: t('common.status', 'Status') },
              { key: 'checked_out_at', label: t('components.account.myDataTab.colCheckedOut', 'Checked out') },
              { key: 'due_date', label: t('components.account.myDataTab.colDue', 'Due') },
              { key: 'returned_at', label: t('components.account.myDataTab.colReturned', 'Returned') },
              { key: 'renewal_count', label: t('components.account.myDataTab.colRenewals', 'Renewals') },
            ]}
          />
        </Section>

        {/* Holds */}
        <Section title={t('components.account.myDataTab.holdHistoryTitle', 'Hold history')} count={data.holds.length}>
          <DataTable
            rows={data.holds}
            columns={[
              { key: 'status', label: t('common.status', 'Status') },
              { key: 'position', label: t('components.account.myDataTab.colPosition', 'Position') },
              { key: 'created_at', label: t('components.account.myDataTab.colPlaced', 'Placed') },
            ]}
          />
        </Section>

        {/* Fines */}
        <Section title={t('account.fines', 'Fines')} count={data.fines.length}>
          <DataTable
            rows={data.fines}
            columns={[
              { key: 'fine_type', label: t('components.account.myDataTab.colType', 'Type') },
              { key: 'amount', label: t('components.account.myDataTab.colAmount', 'Amount') },
              { key: 'amount_paid', label: t('components.account.myDataTab.colPaid', 'Paid') },
              { key: 'status', label: t('common.status', 'Status') },
              { key: 'created_at', label: t('components.account.myDataTab.colDate', 'Date') },
            ]}
          />
        </Section>

        {/* Reading history */}
        <Section title={t('components.account.myDataTab.readingHistoryTitle', 'Reading history')} count={data.reading_history.length}>
          {!data.profile.track_reading_history && (
            <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50 py-2">
              {t('components.account.myDataTab.readingHistoryOffHint', 'Reading history tracking is off. Turn it on in Settings > Privacy if you want to keep a record.')}
            </p>
          )}
          <DataTable
            rows={data.reading_history}
            columns={[
              { key: 'book_title', label: t('components.account.myDataTab.colTitle', 'Title') },
              { key: 'book_author', label: t('components.account.myDataTab.colAuthor', 'Author') },
              { key: 'minutes', label: t('components.account.myDataTab.colMinutes', 'Minutes') },
              { key: 'reading_date', label: t('components.account.myDataTab.colDate', 'Date') },
            ]}
          />
        </Section>

        {/* Favorites */}
        <Section title={t('account.favorites', 'Favorites')} count={data.favorites.length}>
          <DataTable
            rows={data.favorites}
            columns={[
              { key: 'item_id', label: t('components.account.myDataTab.colItemId', 'Item ID') },
              { key: 'created_at', label: t('components.account.myDataTab.colAdded', 'Added') },
            ]}
          />
        </Section>

        {/* Reading lists */}
        <Section title={t('components.account.myDataTab.readingListsTitle', 'Reading lists')} count={data.reading_lists.length}>
          <DataTable
            rows={data.reading_lists}
            columns={[
              { key: 'name', label: t('components.account.myDataTab.colName', 'Name') },
              { key: 'is_public', label: t('components.account.myDataTab.colPublic', 'Public') },
              { key: 'created_at', label: t('components.account.myDataTab.colCreated', 'Created') },
            ]}
          />
        </Section>

        {/* Events */}
        <Section title={t('components.account.myDataTab.eventRegistrationsTitle', 'Event registrations')} count={data.event_registrations.length}>
          <DataTable
            rows={data.event_registrations}
            columns={[
              { key: 'event_id', label: t('components.account.myDataTab.colEvent', 'Event') },
              { key: 'status', label: t('common.status', 'Status') },
              { key: 'registered_at', label: t('components.account.myDataTab.colRegistered', 'Registered') },
            ]}
          />
        </Section>

        {/* E-books */}
        <Section title={t('components.account.myDataTab.ebookActivityTitle', 'E-book activity')} count={data.ebook_checkouts.length}>
          <DataTable
            rows={data.ebook_checkouts}
            columns={[
              { key: 'ebook_title', label: t('components.account.myDataTab.colTitle', 'Title') },
              { key: 'ebook_author', label: t('components.account.myDataTab.colAuthor', 'Author') },
              { key: 'action', label: t('components.account.myDataTab.colAction', 'Action') },
              { key: 'recorded_at', label: t('components.account.myDataTab.colDate', 'Date') },
            ]}
          />
        </Section>

        {/* AI conversations */}
        <Section title={t('components.account.myDataTab.aiConversationsTitle', 'AI assistant conversations')} count={data.ai_conversations.length}>
          <DataTable
            rows={data.ai_conversations}
            columns={[
              { key: 'user_message', label: t('components.account.myDataTab.colYourQuestion', 'Your question') },
              { key: 'detected_intent', label: t('components.account.myDataTab.colTopic', 'Topic') },
              { key: 'created_at', label: t('components.account.myDataTab.colDate', 'Date') },
            ]}
          />
        </Section>
      </div>

      {/* Footer actions */}
      <div className="mt-8 pt-6 border-t border-lsc-border dark:border-earth-700">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
              {t('components.account.myDataTab.deleteAccountHint', 'Want to delete your account? You can request deletion with a 30-day grace period.')}
            </p>
          </div>
          <a
            href="/account?tab=settings"
            className="flex items-center gap-2 text-sm text-status-danger-600 dark:text-status-danger-400 hover:underline"
          >
            <Trash2 className="w-4 h-4" />
            {t('components.account.myDataTab.accountDeletionLink', 'Account deletion')}
          </a>
        </div>
      </div>
    </div>
  )
}
