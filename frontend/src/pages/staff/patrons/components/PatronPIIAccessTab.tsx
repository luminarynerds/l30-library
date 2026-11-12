/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useState } from "react"
import { Loader2, AlertCircle, Shield, ChevronLeft, ChevronRight } from "lucide-react"
import { useAuth } from "../../../../contexts/AuthContext"
import { useTranslation } from "@/i18n"
import {
  fetchPiiAccessLog,
  type PIIAccessLogEntry,
} from "../../../../api/staff-api/pii-access-log"

interface PatronPIIAccessTabProps {
  patronId: number
}

const PAGE_SIZE = 25

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 30) return `${days}d ago`
  return `${Math.floor(days / 30)}mo ago`
}

export function PatronPIIAccessTab({ patronId }: PatronPIIAccessTabProps) {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [entries, setEntries] = useState<PIIAccessLogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [endpoint, setEndpoint] = useState("")
  const [actorId, setActorId] = useState<string>("")
  const [since, setSince] = useState<string>("")
  const [until, setUntil] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const result = await fetchPiiAccessLog(token, {
        patron_id: patronId,
        endpoint: endpoint || undefined,
        user_id: actorId ? Number(actorId) : undefined,
        since: since || undefined,
        until: until || undefined,
        limit: PAGE_SIZE,
        offset,
      })
      setEntries(result.entries)
      setTotal(result.total)
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e)
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [token, patronId, endpoint, actorId, since, until, offset])

  useEffect(() => {
    void load()
  }, [load])

  const onApplyFilters = () => {
    setOffset(0)
    void load()
  }

  if (!token) {
    return (
      <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
        <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>{t("staffPatrons.piiAccess.authRequired")}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <Shield className="w-4 h-4" aria-hidden />
        <span>{t("staffPatrons.piiAccess.intro")}</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
        <input
          type="text"
          value={endpoint}
          onChange={(e) => setEndpoint(e.target.value)}
          placeholder={t("staffPatrons.piiAccess.filters.endpointPlaceholder")}
          aria-label={t("staffPatrons.piiAccess.filters.endpoint")}
          className="px-3 py-2 rounded-lg border border-lsc-border bg-white dark:bg-earth-900 text-sm"
        />
        <input
          type="number"
          value={actorId}
          onChange={(e) => setActorId(e.target.value)}
          placeholder={t("staffPatrons.piiAccess.filters.actorPlaceholder")}
          aria-label={t("staffPatrons.piiAccess.filters.actor")}
          className="px-3 py-2 rounded-lg border border-lsc-border bg-white dark:bg-earth-900 text-sm"
        />
        <input
          type="date"
          value={since}
          onChange={(e) => setSince(e.target.value)}
          aria-label={t("staffPatrons.piiAccess.filters.since")}
          className="px-3 py-2 rounded-lg border border-lsc-border bg-white dark:bg-earth-900 text-sm"
        />
        <input
          type="date"
          value={until}
          onChange={(e) => setUntil(e.target.value)}
          aria-label={t("staffPatrons.piiAccess.filters.until")}
          className="px-3 py-2 rounded-lg border border-lsc-border bg-white dark:bg-earth-900 text-sm"
        />
      </div>
      <div>
        <button
          type="button"
          onClick={onApplyFilters}
          className="px-3 py-1.5 rounded-lg bg-lsc-rose text-white text-sm hover:bg-lsc-rose-dark"
        >
          {t("staffPatrons.piiAccess.applyFilters")}
        </button>
      </div>

      {/* Persistent live region: survives the loading/results swap below so
          screen readers get one announcement instead of a torn-down node */}
      <div role="status" aria-live="polite" className="sr-only">
        {loading
          ? t("staffPatrons.piiAccess.loading")
          : error
            ? t("staffPatrons.piiAccess.loadFailed", "Failed to load PII access events.")
            : t("staffPatrons.piiAccess.resultCount", { count: String(entries.length) })}
      </div>

      {loading && (
        <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
          <Loader2 className="w-6 h-6 mx-auto motion-safe:animate-spin opacity-60" aria-hidden />
          <p className="mt-2 text-sm">{t("staffPatrons.piiAccess.loading")}</p>
        </div>
      )}

      {error && (
        <div role="alert" className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200 text-sm">
          {error}
        </div>
      )}

      {!loading && !error && entries.length === 0 && (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          <p>{t("staffPatrons.piiAccess.empty")}</p>
        </div>
      )}

      {!loading && !error && entries.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-lsc-border">
                <th scope="col" className="py-2 pr-3 font-medium">{t("staffPatrons.piiAccess.cols.when")}</th>
                <th scope="col" className="py-2 pr-3 font-medium">{t("staffPatrons.piiAccess.cols.actor")}</th>
                <th scope="col" className="py-2 pr-3 font-medium">{t("staffPatrons.piiAccess.cols.endpoint")}</th>
                <th scope="col" className="py-2 pr-3 font-medium">{t("staffPatrons.piiAccess.cols.fields")}</th>
                <th scope="col" className="py-2 pr-3 font-medium">{t("staffPatrons.piiAccess.cols.context")}</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} className="border-b border-lsc-border/50 align-top">
                  <td className="py-2 pr-3" title={new Date(e.timestamp).toLocaleString()}>
                    {relativeTime(e.timestamp)}
                  </td>
                  <td className="py-2 pr-3">
                    <div>{e.user_name ?? `#${e.user_id}`}</div>
                    <div className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">{e.user_role}</div>
                  </td>
                  <td className="py-2 pr-3 font-mono text-xs">{e.endpoint}</td>
                  <td className="py-2 pr-3 text-xs">{e.fields_accessed.join(", ") || "—"}</td>
                  <td className="py-2 pr-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {e.additional_context
                      ? Object.entries(e.additional_context)
                          .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
                          .join(" · ")
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex items-center justify-between mt-3 text-sm">
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {t("staffPatrons.piiAccess.pagination.showing", {
                from: String(offset + 1),
                to: String(Math.min(offset + entries.length, total)),
                total: String(total),
              })}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="inline-flex items-center gap-1 px-2 py-1 rounded border border-lsc-border disabled:opacity-50"
                aria-label={t("staffPatrons.piiAccess.pagination.prev")}
              >
                <ChevronLeft className="w-4 h-4" aria-hidden /> {t("staffPatrons.piiAccess.pagination.prev")}
              </button>
              <button
                type="button"
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + entries.length >= total}
                className="inline-flex items-center gap-1 px-2 py-1 rounded border border-lsc-border disabled:opacity-50"
                aria-label={t("staffPatrons.piiAccess.pagination.next")}
              >
                {t("staffPatrons.piiAccess.pagination.next")} <ChevronRight className="w-4 h-4" aria-hidden />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
