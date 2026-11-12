/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Plus, Search, Send, ShieldAlert, X } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { BAN_TYPES, US_STATES_LIST, REASON_LABELS, banTypeBadgeClasses, formatSource, formatDate } from './ban-tracker-data'
import type { AdminBanReport, BanReportFormData } from './types'
import { BanReportRationaleViewer } from '@/components/admin/BanReportRationaleViewer'

function FormInput({
  label,
  value,
  onChange,
  type = 'text',
  required = false,
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  required?: boolean
  placeholder?: string
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-lsc-dark/40 dark:placeholder-lsc-cream/40 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
      />
    </div>
  )
}

function FormSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export function AllReportsTab({
  reports,
  loading,
  search,
  onSearchChange,
  stateFilter,
  onStateFilterChange,
  typeFilter,
  onTypeFilterChange,
  page,
  totalPages,
  total,
  onPageChange,
  showForm,
  onToggleForm,
  form,
  onFormChange,
  onSubmitReport,
  submitting,
}: {
  reports: AdminBanReport[]
  loading: boolean
  search: string
  onSearchChange: (v: string) => void
  stateFilter: string
  onStateFilterChange: (v: string) => void
  typeFilter: string
  onTypeFilterChange: (v: string) => void
  page: number
  totalPages: number
  total: number
  onPageChange: (p: number) => void
  showForm: boolean
  onToggleForm: () => void
  form: BanReportFormData
  onFormChange: (f: BanReportFormData) => void
  onSubmitReport: (e: React.FormEvent) => void
  submitting: boolean
}) {
  const { t } = useTranslation()
  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        <div className="flex flex-wrap gap-2 items-center">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
            <input
              type="text"
              placeholder={t('admin.adminBanTracker.searchTitleOrAuthor')}
              value={search}
              onChange={(e) => {
                onSearchChange(e.target.value)
                onPageChange(1)
              }}
              className="pl-9 pr-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-lsc-dark/40 dark:placeholder-lsc-cream/40 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 w-56"
            />
          </div>
          {/* State filter */}
          <select
            value={stateFilter}
            onChange={(e) => {
              onStateFilterChange(e.target.value)
              onPageChange(1)
            }}
            className="px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
          >
            <option value="">All States</option>
            {US_STATES_LIST.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          {/* Type filter */}
          <select
            value={typeFilter}
            onChange={(e) => {
              onTypeFilterChange(e.target.value)
              onPageChange(1)
            }}
            className="px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
          >
            <option value="">All Types</option>
            {BAN_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={onToggleForm}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors text-sm font-medium"
        >
          {showForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          {showForm ? 'Cancel' : 'Add Report'}
        </button>
      </div>

      {/* Add Report Form */}
      {showForm && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Add Ban Report
          </h3>
          <form onSubmit={onSubmitReport} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <FormInput
              label="Title *"
              value={form.title}
              onChange={(v) => onFormChange({ ...form, title: v })}
              required
            />
            <FormInput
              label="Author *"
              value={form.author}
              onChange={(v) => onFormChange({ ...form, author: v })}
              required
            />
            <FormInput
              label="ISBN"
              value={form.isbn}
              onChange={(v) => onFormChange({ ...form, isbn: v })}
            />
            <FormSelect
              label="State"
              value={form.state}
              onChange={(v) => onFormChange({ ...form, state: v })}
              options={[{ value: '', label: 'Select state' }, ...US_STATES_LIST.map((s) => ({ value: s, label: s }))]}
            />
            <FormInput
              label="District"
              value={form.district}
              onChange={(v) => onFormChange({ ...form, district: v })}
            />
            <FormInput
              label="Institution"
              value={form.institution}
              onChange={(v) => onFormChange({ ...form, institution: v })}
            />
            <FormSelect
              label="Ban Type"
              value={form.ban_type}
              onChange={(v) => onFormChange({ ...form, ban_type: v as BanReportFormData['ban_type'] })}
              options={BAN_TYPES.map((t) => ({ value: t, label: t }))}
            />
            <FormInput
              label="Reason"
              value={form.reason}
              onChange={(v) => onFormChange({ ...form, reason: v })}
            />
            <FormSelect
              label="Reason Category"
              value={form.reason_category}
              onChange={(v) => onFormChange({ ...form, reason_category: v })}
              options={[
                { value: '', label: 'Select category' },
                ...Object.entries(REASON_LABELS).map(([value, label]) => ({ value, label })),
              ]}
            />
            <FormInput
              label="Source"
              value={form.source}
              onChange={(v) => onFormChange({ ...form, source: v })}
            />
            <FormInput
              label="Source URL"
              value={form.source_url}
              onChange={(v) => onFormChange({ ...form, source_url: v })}
              type="url"
            />
            <FormInput
              label="Date Reported"
              value={form.date_reported}
              onChange={(v) => onFormChange({ ...form, date_reported: v })}
              type="date"
            />
            <div className="sm:col-span-2 lg:col-span-3">
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Notes
              </label>
              <textarea
                value={form.notes}
                onChange={(e) => onFormChange({ ...form, notes: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 resize-y"
              />
            </div>
            <div className="sm:col-span-2 lg:col-span-3 flex justify-end">
              <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors text-sm font-medium"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                Submit Report
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Results count */}
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {total.toLocaleString()} report{total !== 1 ? 's' : ''} found
      </p>

      {/* Reports Table */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="h-8 w-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
        </div>
      ) : reports.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-8 text-center">
          <ShieldAlert className="w-8 h-8 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-2" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            No reports match your filters
          </p>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-800/50">
                  <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    Title
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    Author
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    State
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    District
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    Type
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    Source
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    Rationale
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    Date Reported
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-earth-200 dark:divide-earth-700">
                {reports.map((report) => (
                  <tr
                    key={report.id}
                    className="hover:bg-earth-50 dark:hover:bg-earth-700/30 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream max-w-[12.5rem] truncate" title={report.title}>
                      {report.title}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 max-w-[9.375rem] truncate" title={report.author}>
                      {report.author}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {report.state}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 max-w-[9.375rem] truncate" title={report.district || '--'}>
                      {report.district || '--'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${banTypeBadgeClasses(
                          report.ban_type
                        )}`}
                      >
                        {report.ban_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 max-w-[7.5rem] truncate">
                      {report.source_url ? (
                        <a
                          href={report.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-lsc-rose hover:underline"
                        >
                          {formatSource(report.source) || 'Link'}
                        </a>
                      ) : (
                        formatSource(report.source)
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {report.reason_category ? (
                        <BanReportRationaleViewer
                          rationalePresent={report.rationale_present ?? false}
                          rationaleAnticipated={report.rationale_anticipated ?? false}
                          primaryUseCase={report.rationale_primary_use_case ?? null}
                          banCategory={report.reason_category}
                        />
                      ) : (
                        <span className="text-xs text-lsc-dark/40 dark:text-lsc-cream/40">--</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/60 whitespace-nowrap">
                      {formatDate(report.date_reported)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page <= 1}
            className="px-3 py-1.5 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream disabled:opacity-40 hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1.5 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream disabled:opacity-40 hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
