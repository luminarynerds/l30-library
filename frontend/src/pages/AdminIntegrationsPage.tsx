/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Plug } from 'lucide-react'
import { AdminShell } from '@/components/shells'
import { useRequireRole } from '@/hooks/useRequireRole'
import { usePageTitle } from '@/hooks/usePageTitle'
import {
  listIntegrations,
  probeIntegration,
  sendTestEmail,
  type IntegrationRow,
  type IntegrationCategory,
} from '@/api/admin/integrations-api'
import { IntegrationCard } from '@/components/admin/integrations/IntegrationCard'
import { ProbeLog, type ProbeLogEntry } from '@/components/admin/integrations/ProbeLog'

const CATEGORY_ORDER: IntegrationCategory[] = [
  'Email',
  'SMS',
  'Payments',
  'Storage',
  'Observability',
  'Auth',
  'AI',
  'Other',
]

function groupByCategory(rows: IntegrationRow[]): Map<IntegrationCategory, IntegrationRow[]> {
  const map = new Map<IntegrationCategory, IntegrationRow[]>()
  for (const row of rows) {
    const list = map.get(row.category) ?? []
    list.push(row)
    map.set(row.category, list)
  }
  return map
}

function logStatusFor(row: IntegrationRow): ProbeLogEntry['status'] {
  if (!row.configured) return 'unconfigured'
  if (row.status === 'ok') return 'ok'
  if (row.status === 'error') return 'error'
  return 'unconfigured'
}

export default function AdminIntegrationsPage(): JSX.Element {
  // TODO: i18n -- adminIntegrations.pageTitle
  usePageTitle('System Integrations')

  const { user, authLoading, isAuthorized } = useRequireRole('adminOrDirector')
  const navigate = useNavigate()

  const [rows, setRows] = useState<IntegrationRow[]>([])
  const [loading, setLoading] = useState(true)
  const [probing, setProbing] = useState<Record<string, boolean>>({})
  const [log, setLog] = useState<ProbeLogEntry[]>([])
  const [pendingTestEmail, setPendingTestEmail] = useState<string | null>(null)
  const [sendingTestEmail, setSendingTestEmail] = useState(false)

  useEffect(() => {
    if (!authLoading && !isAuthorized) {
      navigate('/')
    }
  }, [authLoading, isAuthorized, navigate])

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listIntegrations()
      setRows(data.integrations)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load integrations'
      toast.error(msg)
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isAuthorized) {
      void loadAll()
    }
  }, [isAuthorized, loadAll])

  const handleProbe = useCallback(async (id: string) => {
    setProbing((p) => ({ ...p, [id]: true }))
    try {
      const result = await probeIntegration(id)
      setRows((prev) => prev.map((r) => (r.integration_id === id ? result : r)))
      setLog((prev) =>
        [
          {
            ts: new Date(),
            integrationId: result.integration_id,
            integrationName: result.name,
            status: logStatusFor(result),
            detail: result.last_probe_detail,
          },
          ...prev,
        ].slice(0, 50)
      )
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Probe failed'
      toast.error(msg)
      const failedRow = rows.find((r) => r.integration_id === id)
      setLog((prev) =>
        [
          {
            ts: new Date(),
            integrationId: id,
            integrationName: failedRow?.name ?? id,
            status: 'error' as const,
            detail: msg,
          },
          ...prev,
        ].slice(0, 50)
      )
    } finally {
      setProbing((p) => {
        const next = { ...p }
        delete next[id]
        return next
      })
    }
  }, [rows])

  const handleSendTestClick = useCallback(() => {
    if (!user?.email) {
      toast.error('No admin email on file')
      return
    }
    setPendingTestEmail(user.email)
  }, [user])

  const handleConfirmSendTestEmail = useCallback(async () => {
    setSendingTestEmail(true)
    setPendingTestEmail(null)
    try {
      const result = await sendTestEmail()
      setLog((prev) =>
        [
          {
            ts: new Date(),
            integrationId: 'email_test',
            integrationName: 'Test Email',
            status: result.ok ? ('ok' as const) : ('error' as const),
            detail: `${result.detail} (to ${result.sent_to})`,
          },
          ...prev,
        ].slice(0, 50)
      )
      if (result.ok) {
        toast.success(`Test email sent to ${result.sent_to}`)
      } else {
        toast.error(result.detail || 'Failed to send test email')
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to send test email'
      toast.error(msg)
      setLog((prev) =>
        [
          {
            ts: new Date(),
            integrationId: 'email_test',
            integrationName: 'Test Email',
            status: 'error' as const,
            detail: msg,
          },
          ...prev,
        ].slice(0, 50)
      )
    } finally {
      setSendingTestEmail(false)
    }
  }, [])

  const handleCancelSendTest = useCallback(() => {
    setPendingTestEmail(null)
  }, [])

  const grouped = useMemo(() => groupByCategory(rows), [rows])

  if (!isAuthorized) {
    return (
      <AdminShell title="System Integrations" icon={<Plug className="w-6 h-6" />}>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Checking access...</p>
      </AdminShell>
    )
  }

  return (
    <AdminShell
      title="System Integrations" // TODO: i18n -- adminIntegrations.pageTitle
      subtitle="Test and monitor connections to email, SMS, payments, and storage providers" // TODO: i18n -- adminIntegrations.pageSubtitle
      icon={<Plug className="w-6 h-6" />}
    >
      {loading ? (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Loading...</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          No integrations registered.
        </p>
      ) : (
        <div className="space-y-8">
          {CATEGORY_ORDER.filter((c) => grouped.has(c)).map((category) => {
            const items = grouped.get(category) ?? []
            return (
              <section key={category}>
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                  {category}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {items.map((row) => {
                    const cardProps: {
                      row: IntegrationRow
                      onProbe: () => void
                      probing: boolean
                      onSendTest?: () => void
                    } = {
                      row,
                      onProbe: () => void handleProbe(row.integration_id),
                      probing: Boolean(probing[row.integration_id]) || sendingTestEmail,
                    }
                    if (row.category === 'Email') {
                      cardProps.onSendTest = handleSendTestClick
                    }
                    return <IntegrationCard key={row.integration_id} {...cardProps} />
                  })}
                </div>
              </section>
            )
          })}
        </div>
      )}

      <ProbeLog log={log} />

      {/* Confirm send-test-email dialog */}
      {pendingTestEmail && (
        <div
          className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="send-test-email-title"
        >
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-sm w-full p-5">
            <h3
              id="send-test-email-title"
              className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2"
            >
              Send test email?
            </h3>
            <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-4">
              {/* TODO: i18n -- adminIntegrations.confirmSendTest */}
              Send a real email to {pendingTestEmail}?
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleCancelSendTest}
                className="px-3 py-1.5 text-sm rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/40 dark:hover:bg-earth-700/60"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleConfirmSendTestEmail()}
                className="px-3 py-1.5 text-sm rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminShell>
  )
}
