/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Monitor,
  Plus,
  Loader2,
  Search,
  Edit3,
  Trash2,
  Power,
  PowerOff,
  ChevronLeft,
  ChevronRight,
  Wifi,
  WifiOff,
} from "lucide-react"
import { useTranslation } from "@/i18n"
import { getTerminalStatusInfo, SIP2Terminal } from "@/api/sip2-api"
import { formatDate } from "../types"

interface TerminalListProps {
  terminals: SIP2Terminal[]
  isLoading: boolean
  terminalSearch: string
  setTerminalSearch: (v: string) => void
  terminalFilter: "all" | "active" | "inactive"
  setTerminalFilter: (v: "all" | "active" | "inactive") => void
  terminalPage: number
  setTerminalPage: (v: number) => void
  terminalTotalPages: number
  onToggleActive: (terminal: SIP2Terminal) => void
  onEdit: (terminal: SIP2Terminal) => void
  onDelete: (terminal: SIP2Terminal) => void
  onCreate: () => void
}

export function TerminalList({
  terminals,
  isLoading,
  terminalSearch,
  setTerminalSearch,
  terminalFilter,
  setTerminalFilter,
  terminalPage,
  setTerminalPage,
  terminalTotalPages,
  onToggleActive,
  onEdit,
  onDelete,
  onCreate,
}: TerminalListProps) {
  const { t } = useTranslation()

  return (
    <>
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex-1 min-w-[200px] max-w-md relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            type="text"
            placeholder={t('placeholder.staffSIP2.searchTerminals')}
            aria-label={t('aria.staffSIP2.searchTerminals')}
            value={terminalSearch}
            onChange={(e) => setTerminalSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
        </div>
        <select
          value={terminalFilter}
          onChange={(e) => setTerminalFilter(e.target.value as "all" | "active" | "inactive")}
          aria-label={t('aria.staffSIP2.filterTerminalsByStatus', 'Filter terminals by status')}
          className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        >
          <option value="all">All Terminals</option>
          <option value="active">Active Only</option>
          <option value="inactive">Inactive Only</option>
        </select>
      </div>

      {/* Terminals list */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div role="status" aria-live="polite" className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <span className="sr-only">Loading terminals…</span>
          </div>
        ) : terminals.length === 0 ? (
          <div className="p-8 text-center">
            <Monitor className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              No Terminals Found
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              Add your first SIP2 self-checkout terminal
            </p>
            <button
              onClick={onCreate}
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Terminal
            </button>
          </div>
        ) : (
          <div className="divide-y divide-lsc-border dark:divide-earth-700">
            {terminals.map((terminal) => {
              const statusInfo = getTerminalStatusInfo(terminal)
              return (
                <div
                  key={terminal.id}
                  className="p-4 flex items-center justify-between hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className={`p-2 rounded-lg ${
                      statusInfo.status === "online"
                        ? "bg-status-success-100 dark:bg-status-success-900/30"
                        : statusInfo.status === "offline"
                        ? "bg-status-danger-100 dark:bg-status-danger-900/30"
                        : "bg-earth-100 dark:bg-earth-700"
                    }`}>
                      {statusInfo.status === "online" ? (
                        <Wifi className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
                      ) : statusInfo.status === "offline" ? (
                        <WifiOff className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
                      ) : (
                        <PowerOff className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {terminal.name}
                        </h3>
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                          statusInfo.status === "online"
                            ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400"
                            : statusInfo.status === "offline"
                            ? "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400"
                            : "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                        }`}>
                          {statusInfo.label}
                        </span>
                      </div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        ID: {terminal.terminal_id}
                        {terminal.location && ` \u2022 ${terminal.location}`}
                      </p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        Last seen: {formatDate(terminal.last_seen_at)}
                        {terminal.last_ip && ` from ${terminal.last_ip}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onToggleActive(terminal)}
                      className={`p-2 rounded-lg transition-colors ${
                        terminal.is_active
                          ? "text-status-success-600 dark:text-status-success-400 hover:bg-status-success-50 dark:bg-status-success-900/20 dark:hover:bg-status-success-900/20"
                          : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700"
                      }`}
                      title={terminal.is_active ? "Deactivate" : "Activate"}
                    >
                      {terminal.is_active ? <Power className="w-4 h-4" /> : <PowerOff className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => onEdit(terminal)}
                      className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                      title="Edit terminal"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDelete(terminal)}
                      className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                      title="Delete terminal"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Pagination */}
        {terminalTotalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-lsc-border dark:border-earth-700">
            <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Page {terminalPage} of {terminalTotalPages}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setTerminalPage(Math.max(1, terminalPage - 1))}
                disabled={terminalPage === 1}
                aria-label={t('aria.staffSIP2.previousPage', 'Previous page')}
                className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={() => setTerminalPage(Math.min(terminalTotalPages, terminalPage + 1))}
                disabled={terminalPage === terminalTotalPages}
                aria-label={t('aria.staffSIP2.nextPage', 'Next page')}
                className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
