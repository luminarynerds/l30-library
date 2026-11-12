/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  FileText, ChevronDown, ChevronRight, Download, Save, FolderOpen,
  Loader2, Trash2, Table2, ArrowUpDown, Play,
} from "lucide-react"
import toast from "react-hot-toast"
import { AdminShell } from "../../components/shells"
import { ConfirmDialog } from "../../components/ui/ConfirmDialog"
import { listBranches } from "../../api/branch-api"
import { t } from "../../i18n"
import {
  generateJsonReport,
  downloadReport,
  type ReportType,
} from "../../api/unified-reports-api"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type DataSource = "circulation" | "patron_activity" | "collection" | "financial"
type Dimension = "date_daily" | "date_weekly" | "date_monthly" | "branch" | "item_type" | "patron_type"
type OutputMode = "table" | "csv" | "pdf"
type SortDir = "asc" | "desc"

interface ReportTemplate {
  id: string
  name: string
  dataSource: DataSource
  metrics: string[]
  dimensions: Dimension[]
  filters: FilterState
  outputMode: OutputMode
  createdAt: string
}

interface FilterState {
  startDate: string
  endDate: string
  branchId: string
  itemType: string
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DATA_SOURCES: { value: DataSource; label: string; description: string }[] = [
  { value: "circulation", label: "Circulation", description: "Checkouts, returns, renewals, and overdue tracking" },
  { value: "patron_activity", label: "Patrons", description: "Registration, engagement, and patron status" },
  { value: "collection", label: "Collection", description: "Inventory counts, condition, and format breakdown" },
  { value: "financial", label: "Financial", description: "Revenue, fines collected, and fines waived" },
]

const METRICS_BY_SOURCE: Record<DataSource, { value: string; label: string }[]> = {
  circulation: [
    { value: "checkouts", label: "Checkouts" },
    { value: "returns", label: "Returns" },
    { value: "renewals", label: "Renewals" },
    { value: "overdue_count", label: "Overdue Count" },
  ],
  patron_activity: [
    { value: "total_patrons", label: "Total Patrons" },
    { value: "new_registrations", label: "New Registrations" },
    { value: "active_patrons", label: "Active Patrons" },
    { value: "blocked_patrons", label: "Blocked Patrons" },
  ],
  collection: [
    { value: "total_items", label: "Total Items" },
    { value: "items_by_condition", label: "Items by Condition" },
    { value: "items_by_format", label: "Items by Format" },
  ],
  financial: [
    { value: "revenue", label: "Revenue" },
    { value: "fines_collected", label: "Fines Collected" },
    { value: "fines_waived", label: "Fines Waived" },
  ],
}

const DIMENSIONS: { value: Dimension; label: string }[] = [
  { value: "date_daily", label: "By Date (Daily)" },
  { value: "date_weekly", label: "By Date (Weekly)" },
  { value: "date_monthly", label: "By Date (Monthly)" },
  { value: "branch", label: "By Branch" },
  { value: "item_type", label: "By Item Type" },
  { value: "patron_type", label: "By Patron Type" },
]

const ITEM_TYPES = [
  { value: "", label: "All Types" },
  { value: "book", label: "Book" },
  { value: "dvd", label: "DVD" },
  { value: "audiobook", label: "Audiobook" },
  { value: "magazine", label: "Magazine" },
  { value: "ebook", label: "E-Book" },
  { value: "other", label: "Other" },
]

const STORAGE_KEY = "l30:custom-report-templates"

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

function loadTemplates(): ReportTemplate[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as ReportTemplate[]) : []
  } catch {
    return []
  }
}

function saveTemplates(templates: ReportTemplate[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(templates))
}

// ---------------------------------------------------------------------------
// Section wrapper
// ---------------------------------------------------------------------------

function Section({
  number,
  title,
  expanded,
  onToggle,
  children,
}: {
  number: number
  title: string
  expanded: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-5 py-4 text-left focus:outline-none focus:ring-2 focus:ring-library-500 rounded-xl"
        aria-expanded={expanded}
      >
        <span className="flex items-center justify-center w-7 h-7 rounded-full bg-library-600 text-white text-sm font-bold flex-shrink-0">
          {number}
        </span>
        {expanded
          ? <ChevronDown className="w-4 h-4 text-earth-600" aria-hidden="true" />
          : <ChevronRight className="w-4 h-4 text-earth-600" aria-hidden="true" />}
        <span className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{title}</span>
      </button>
      {expanded && <div className="px-5 pb-5">{children}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sortable table
// ---------------------------------------------------------------------------

function ResultsTable({ data }: { data: unknown }) {
  const [sortCol, setSortCol] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>("asc")

  const { columns, rows } = useMemo(() => {
    if (!data || typeof data !== "object") return { columns: [] as string[], rows: [] as Record<string, unknown>[] }

    let arr: Record<string, unknown>[] = []

    if (Array.isArray(data)) {
      arr = data as Record<string, unknown>[]
    } else {
      const values = Object.values(data as Record<string, unknown>)
      const firstArr = values.find(Array.isArray)
      if (firstArr) {
        arr = firstArr as Record<string, unknown>[]
      } else {
        arr = [data as Record<string, unknown>]
      }
    }

    if (arr.length === 0) return { columns: [] as string[], rows: [] as Record<string, unknown>[] }

    const cols = Object.keys(arr[0] ?? {})
    return { columns: cols, rows: arr }
  }, [data])

  const sorted = useMemo(() => {
    if (!sortCol) return rows
    return [...rows].sort((a, b) => {
      const av = a[sortCol]
      const bv = b[sortCol]
      if (av == null && bv == null) return 0
      if (av == null) return 1
      if (bv == null) return -1
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av
      }
      const sa = String(av)
      const sb = String(bv)
      return sortDir === "asc" ? sa.localeCompare(sb) : sb.localeCompare(sa)
    })
  }, [rows, sortCol, sortDir])

  const handleSort = useCallback((col: string) => {
    setSortCol((prev) => {
      if (prev === col) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"))
        return col
      }
      setSortDir("asc")
      return col
    })
  }, [])

  if (columns.length === 0) {
    return (
      <div className="bg-earth-50 dark:bg-earth-900 rounded-lg p-6 text-center">
        <p className="text-sm text-earth-600 dark:text-earth-400">No tabular data available. Raw response:</p>
        <pre className="mt-3 text-xs text-left overflow-auto max-h-96 font-mono text-earth-700 dark:text-earth-300">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    )
  }

  return (
    <div className="overflow-auto max-h-[500px] rounded-lg border border-lsc-border dark:border-earth-700">
      <table className="min-w-full divide-y divide-lsc-border dark:divide-earth-700 text-sm">
        <thead className="bg-earth-50 dark:bg-earth-900 sticky top-0">
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                scope="col"
                aria-sort={
                  sortCol === col
                    ? sortDir === "asc"
                      ? "ascending"
                      : "descending"
                    : "none"
                }
                className="px-4 py-2 text-left font-medium text-lsc-dark/70 dark:text-lsc-cream/70"
              >
                <button
                  type="button"
                  onClick={() => handleSort(col)}
                  className="inline-flex w-full items-center gap-1 select-none rounded px-1 py-0.5 text-left hover:bg-earth-100 dark:hover:bg-earth-800 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                >
                  {col.replace(/_/g, " ")}
                  <ArrowUpDown className="w-3 h-3 text-earth-600" aria-hidden="true" />
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-lsc-border dark:divide-earth-700 bg-lsc-white dark:bg-earth-800">
          {sorted.slice(0, 500).map((row, i) => (
            <tr key={i} className="hover:bg-earth-50 dark:hover:bg-earth-900/50">
              {columns.map((col) => (
                <td key={col} className="px-4 py-2 text-lsc-dark dark:text-lsc-cream whitespace-nowrap">
                  {row[col] == null ? "\u2014" : String(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {sorted.length > 500 && (
        <p className="px-4 py-2 text-xs text-earth-600 text-center bg-earth-50 dark:bg-earth-900">
          Showing first 500 of {sorted.length} rows
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CustomReportBuilderPage(): React.ReactElement {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({
    1: true, 2: true, 3: true, 4: true, 5: true,
  })
  const toggle = useCallback((n: number) => setExpanded((prev) => ({ ...prev, [n]: !prev[n] })), [])

  const [dataSource, setDataSource] = useState<DataSource>("circulation")
  const [metrics, setMetrics] = useState<string[]>(["checkouts"])
  const [dimensions, setDimensions] = useState<Dimension[]>([])
  const [filters, setFilters] = useState<FilterState>({
    startDate: "",
    endDate: "",
    branchId: "",
    itemType: "",
  })
  const [outputMode, setOutputMode] = useState<OutputMode>("table")

  const [templates, setTemplates] = useState<ReportTemplate[]>(loadTemplates)
  const [templateName, setTemplateName] = useState("")
  const [showSaveInput, setShowSaveInput] = useState(false)
  const [pendingDeleteTemplate, setPendingDeleteTemplate] = useState<ReportTemplate | null>(null)

  const [isLoading, setIsLoading] = useState(false)
  const [reportData, setReportData] = useState<unknown>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const { data: branchOptions = [] } = useQuery({
    queryKey: ["custom-reports:branches"],
    queryFn: () => listBranches({ active_only: true }),
    staleTime: 300_000,
  })

  const apiReportType: ReportType = dataSource as ReportType

  const handleSourceChange = useCallback((src: DataSource) => {
    setDataSource(src)
    const available = METRICS_BY_SOURCE[src]
    setMetrics(available[0] ? [available[0].value] : [])
  }, [])

  const toggleMetric = useCallback((m: string) => {
    setMetrics((prev) =>
      prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m],
    )
  }, [])

  const toggleDimension = useCallback((d: Dimension) => {
    setDimensions((prev) =>
      prev.includes(d) ? prev.filter((x) => x !== d) : [...prev, d],
    )
  }, [])

  const buildParams = useCallback(() => ({
    report_type: apiReportType,
    ...(filters.startDate ? { start_date: filters.startDate } : {}),
    ...(filters.endDate ? { end_date: filters.endDate } : {}),
    ...(filters.branchId ? { branch_id: parseInt(filters.branchId, 10) } : {}),
  }), [apiReportType, filters])

  const handleGenerate = useCallback(async () => {
    if (metrics.length === 0) {
      toast.error("Select at least one metric")
      return
    }
    setIsLoading(true)
    setErrorMsg(null)
    setReportData(null)

    try {
      if (outputMode === "table") {
        const result = await generateJsonReport({ ...buildParams(), format: "json" })
        setReportData(result.data)
        toast.success("Report generated")
      } else {
        const fmt = outputMode === "csv" ? "csv" : "pdf"
        await downloadReport({ ...buildParams(), format: fmt })
        toast.success(`${fmt.toUpperCase()} download started`)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setErrorMsg(msg)
      toast.error(msg || "Failed to generate report")
    } finally {
      setIsLoading(false)
    }
  }, [buildParams, metrics, outputMode])

  const handleSaveTemplate = useCallback(() => {
    const name = templateName.trim()
    if (!name) {
      toast.error("Enter a template name")
      return
    }
    const tpl: ReportTemplate = {
      id: crypto.randomUUID(),
      name,
      dataSource,
      metrics,
      dimensions,
      filters,
      outputMode,
      createdAt: new Date().toISOString(),
    }
    const next = [...templates, tpl]
    setTemplates(next)
    saveTemplates(next)
    setTemplateName("")
    setShowSaveInput(false)
    toast.success(`Template "${name}" saved`)
  }, [templateName, dataSource, metrics, dimensions, filters, outputMode, templates])

  const handleLoadTemplate = useCallback((id: string) => {
    const tpl = templates.find((t) => t.id === id)
    if (!tpl) return
    setDataSource(tpl.dataSource)
    setMetrics(tpl.metrics)
    setDimensions(tpl.dimensions)
    setFilters(tpl.filters)
    setOutputMode(tpl.outputMode)
    toast.success(`Loaded "${tpl.name}"`)
  }, [templates])

  const handleDeleteTemplate = useCallback((id: string) => {
    const next = templates.filter((t) => t.id !== id)
    setTemplates(next)
    saveTemplates(next)
    toast.success("Template deleted")
  }, [templates])

  return (
    <AdminShell
      title="Custom Report Builder"
      subtitle="Build, preview, and save custom reports"
      icon={<FileText className="w-8 h-8 text-library-600" aria-hidden="true" />}
    >
      {/* Template toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        {templates.length > 0 && (
          <div className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-earth-600" aria-hidden="true" />
            <select
              aria-label="Load saved template"
              className="rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-1.5 text-sm text-lsc-dark dark:text-lsc-cream"
              defaultValue=""
              onChange={(e) => {
                if (e.target.value) handleLoadTemplate(e.target.value)
                e.target.value = ""
              }}
            >
              <option value="" disabled>Load Template...</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
        )}

        {showSaveInput ? (
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleSaveTemplate() }}
              placeholder="Template name..."
              className="rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-1.5 text-sm text-lsc-dark dark:text-lsc-cream w-48"
              autoFocus
            />
            <button
              onClick={handleSaveTemplate}
              className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-library-600 hover:bg-library-700 text-white transition-colors"
            >
              <Save className="w-3.5 h-3.5" aria-hidden="true" />
              Save
            </button>
            <button
              onClick={() => { setShowSaveInput(false); setTemplateName("") }}
              className="px-2 py-1.5 text-sm text-earth-600 hover:text-earth-700 dark:hover:text-earth-300"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowSaveInput(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-800 transition-colors"
          >
            <Save className="w-3.5 h-3.5" aria-hidden="true" />
            Save as Template
          </button>
        )}

        {templates.length > 0 && (
          <div className="flex flex-wrap gap-2 ml-auto">
            {templates.map((tmpl) => (
              <span
                key={tmpl.id}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs bg-library-50 dark:bg-library-900/20 text-library-700 dark:text-library-300 border border-library-200 dark:border-library-800"
              >
                {tmpl.name}
                <button
                  onClick={() => setPendingDeleteTemplate(tmpl)}
                  className="ml-0.5 text-library-400 hover:text-status-danger-500 transition-colors"
                  aria-label={`Delete template ${tmpl.name}`}
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-4">
        {/* Step 1: Data Source */}
        <Section number={1} title="Data Source" expanded={!!expanded[1]} onToggle={() => toggle(1)}>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {DATA_SOURCES.map((src) => (
              <button
                key={src.value}
                type="button"
                onClick={() => handleSourceChange(src.value)}
                aria-pressed={dataSource === src.value}
                className={`p-4 rounded-lg border-2 text-left transition-all ${
                  dataSource === src.value
                    ? "border-library-500 bg-library-50 dark:bg-library-900/20"
                    : "border-lsc-border dark:border-earth-700 hover:border-library-300"
                }`}
              >
                <p className={`font-semibold text-sm ${
                  dataSource === src.value
                    ? "text-library-700 dark:text-library-300"
                    : "text-lsc-dark/70 dark:text-lsc-cream/70"
                }`}>
                  {src.label}
                </p>
                <p className="text-xs text-earth-600 dark:text-earth-400 mt-1">{src.description}</p>
              </button>
            ))}
          </div>
        </Section>

        {/* Step 2: Metrics */}
        <Section number={2} title="Metrics" expanded={!!expanded[2]} onToggle={() => toggle(2)}>
          <p className="text-xs text-earth-600 dark:text-earth-400 mb-3">
            Select one or more metrics to include in the report.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
            {METRICS_BY_SOURCE[dataSource].map((m) => (
              <label
                key={m.value}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg border cursor-pointer transition-all ${
                  metrics.includes(m.value)
                    ? "border-library-500 bg-library-50 dark:bg-library-900/20"
                    : "border-lsc-border dark:border-earth-700 hover:border-library-300"
                }`}
              >
                <input
                  type="checkbox"
                  checked={metrics.includes(m.value)}
                  onChange={() => toggleMetric(m.value)}
                  className="rounded border-earth-300 text-library-600 focus:ring-library-500"
                />
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">{m.label}</span>
              </label>
            ))}
          </div>
        </Section>

        {/* Step 3: Dimensions */}
        <Section number={3} title="Dimensions / Grouping" expanded={!!expanded[3]} onToggle={() => toggle(3)}>
          <p className="text-xs text-earth-600 dark:text-earth-400 mb-3">
            Choose how to group your data. Leave empty for totals only.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {DIMENSIONS.map((d) => (
              <label
                key={d.value}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg border cursor-pointer transition-all ${
                  dimensions.includes(d.value)
                    ? "border-library-500 bg-library-50 dark:bg-library-900/20"
                    : "border-lsc-border dark:border-earth-700 hover:border-library-300"
                }`}
              >
                <input
                  type="checkbox"
                  checked={dimensions.includes(d.value)}
                  onChange={() => toggleDimension(d.value)}
                  className="rounded border-earth-300 text-library-600 focus:ring-library-500"
                />
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">{d.label}</span>
              </label>
            ))}
          </div>
        </Section>

        {/* Step 4: Filters */}
        <Section number={4} title="Filters" expanded={!!expanded[4]} onToggle={() => toggle(4)}>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label htmlFor="crb-start" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Start Date
              </label>
              <input
                id="crb-start"
                type="date"
                value={filters.startDate}
                max={filters.endDate || undefined}
                onChange={(e) => setFilters((f) => ({ ...f, startDate: e.target.value }))}
                className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label htmlFor="crb-end" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                End Date
              </label>
              <input
                id="crb-end"
                type="date"
                value={filters.endDate}
                min={filters.startDate || undefined}
                onChange={(e) => setFilters((f) => ({ ...f, endDate: e.target.value }))}
                className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label htmlFor="crb-branch" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Branch
              </label>
              <select
                id="crb-branch"
                value={filters.branchId}
                onChange={(e) => setFilters((f) => ({ ...f, branchId: e.target.value }))}
                className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
              >
                <option value="">All Branches</option>
                {branchOptions.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="crb-item-type" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Item Type
              </label>
              <select
                id="crb-item-type"
                value={filters.itemType}
                onChange={(e) => setFilters((f) => ({ ...f, itemType: e.target.value }))}
                className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
              >
                {ITEM_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>
        </Section>

        {/* Step 5: Output Format */}
        <Section number={5} title="Output Format" expanded={!!expanded[5]} onToggle={() => toggle(5)}>
          <div className="flex flex-wrap gap-3">
            {([
              { value: "table" as OutputMode, label: "Table View", icon: Table2 },
              { value: "csv" as OutputMode, label: "CSV Export", icon: Download },
              { value: "pdf" as OutputMode, label: "PDF Export", icon: FileText },
            ]).map((opt) => {
              const Icon = opt.icon
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setOutputMode(opt.value)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border-2 text-sm font-medium transition-all ${
                    outputMode === opt.value
                      ? "border-library-500 bg-library-50 dark:bg-library-900/20 text-library-700 dark:text-library-300"
                      : "border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-library-300"
                  }`}
                >
                  <Icon className="w-4 h-4" aria-hidden="true" />
                  {opt.label}
                </button>
              )
            })}
          </div>
        </Section>
      </div>

      {/* Generate button */}
      <div className="mt-6 flex items-center gap-3">
        <button
          onClick={handleGenerate}
          disabled={isLoading || metrics.length === 0}
          className="flex items-center gap-2 px-6 py-2.5 bg-library-600 hover:bg-library-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          {isLoading
            ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
            : <Play className="w-4 h-4" aria-hidden="true" />}
          {isLoading ? "Generating..." : "Generate Report"}
        </button>
        {metrics.length === 0 && (
          <span className="text-sm text-earth-600">Select at least one metric to generate.</span>
        )}
      </div>

      {/* Error */}
      {errorMsg && (
        <div role="alert" className="mt-6 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4">
          <p className="text-sm text-status-danger-700 dark:text-status-danger-300">{errorMsg}</p>
        </div>
      )}

      {/* Results */}
      {reportData != null && (
        <div className="mt-6">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
            <Table2 className="w-5 h-5 text-library-600" aria-hidden="true" />
            Results
          </h2>
          <ResultsTable data={reportData} />
        </div>
      )}

      <ConfirmDialog
        open={!!pendingDeleteTemplate}
        title={t('customReportBuilder.confirmDeleteTitle', 'Delete template?')}
        body={
          pendingDeleteTemplate
            ? t(
                'customReportBuilder.confirmDeleteBody',
                'Delete report template "{{name}}"? This can\'t be undone.'
              ).replace('{{name}}', pendingDeleteTemplate.name)
            : ''
        }
        confirmLabel={t('customReportBuilder.confirmDeleteLabel', 'Delete template')}
        tone="danger"
        onConfirm={() => {
          if (!pendingDeleteTemplate) return
          handleDeleteTemplate(pendingDeleteTemplate.id)
          setPendingDeleteTemplate(null)
        }}
        onCancel={() => setPendingDeleteTemplate(null)}
      />
    </AdminShell>
  )
}
