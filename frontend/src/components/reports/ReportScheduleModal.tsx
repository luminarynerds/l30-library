/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Plus, Edit2, Trash2, Clock, Loader2, Mail } from "lucide-react"
import toast from "react-hot-toast"
import { Modal } from "@/components/ui/Modal"
import { DestructiveActionDialog } from "@/components/dialogs/DestructiveActionDialog"
import { fetchApi } from "@/lib/api-client"
import { getAccessToken } from "@/utils/tokenStore"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ReportSchedule {
  id: number
  name: string
  is_active: boolean
  report_type: string
  output_format: string
  frequency: string
  day_of_week?: number | null
  day_of_month?: number | null
  time_of_day: string
  branch_id?: number | null
  recipient_emails: string[]
  last_run_at?: string | null
  next_run_at?: string | null
  last_status?: string | null
  created_at?: string | null
}

interface ScheduleFormData {
  name: string
  report_type: string
  output_format: string
  frequency: string
  day_of_week: number
  day_of_month: number
  time_of_day: string
  recipient_emails: string[]
  is_active: boolean
}

const REPORT_TYPE_LABELS: Record<string, string> = {
  circulation: "Circulation",
  financial: "Financial",
  patron_activity: "Patron Activity",
  collection: "Collection",
  compliance: "Compliance",
  community_outcomes: "Community Outcomes",
}

const FORMAT_LABELS: Record<string, string> = {
  csv: "CSV",
  excel: "Excel",
  pdf: "PDF",
}

const FREQUENCY_LABELS: Record<string, string> = {
  daily: "Daily",
  weekly: "Weekly",
  monthly: "Monthly",
}

const WEEKDAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const BASE = "/unified-reports/schedules"

function authHeaders() {
  const token = getAccessToken()
  return token ? { token } : {}
}

async function fetchSchedules(): Promise<ReportSchedule[]> {
  return fetchApi<ReportSchedule[]>(BASE, authHeaders())
}

async function fetchSchedule(id: number): Promise<ReportSchedule> {
  return fetchApi<ReportSchedule>(`${BASE}/${id}`, authHeaders())
}

async function createSchedule(data: ScheduleFormData): Promise<ReportSchedule> {
  return fetchApi<ReportSchedule>(BASE, { method: "POST", body: data, ...authHeaders() })
}

async function updateSchedule(id: number, data: Partial<ScheduleFormData>): Promise<ReportSchedule> {
  return fetchApi<ReportSchedule>(`${BASE}/${id}`, { method: "PUT", body: data, ...authHeaders() })
}

async function deleteScheduleApi(id: number): Promise<void> {
  await fetchApi(`${BASE}/${id}`, { method: "DELETE", ...authHeaders() })
}

// ---------------------------------------------------------------------------
// Main modal
// ---------------------------------------------------------------------------

interface ReportScheduleModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function ReportScheduleModal({ isOpen, onClose }: ReportScheduleModalProps) {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null)

  const { data: schedules = [], isLoading } = useQuery({
    queryKey: ["report-schedules"],
    queryFn: fetchSchedules,
    enabled: isOpen,
    staleTime: 30_000,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteScheduleApi,
    onSuccess: () => {
      toast.success("Schedule deleted")
      queryClient.invalidateQueries({ queryKey: ["report-schedules"] })
      setPendingDeleteId(null)
    },
    onError: (err: unknown) => {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error("Failed to delete schedule")
      setPendingDeleteId(null)
    },
  })

  const ordinal = (n: number): string => {
    if (n % 100 >= 11 && n % 100 <= 13) return n + "th"
    switch (n % 10) {
      case 1: return n + "st"
      case 2: return n + "nd"
      case 3: return n + "rd"
      default: return n + "th"
    }
  }

  const describeSchedule = (s: ReportSchedule): string => {
    let desc = FREQUENCY_LABELS[s.frequency] || s.frequency
    if (s.frequency === "weekly" && s.day_of_week != null) {
      desc += ` on ${WEEKDAY_LABELS[s.day_of_week] || "?"}`
    } else if (s.frequency === "monthly" && s.day_of_month != null) {
      desc += ` on the ${ordinal(s.day_of_month)}`
    }
    if (s.time_of_day) desc += ` at ${s.time_of_day}`
    return desc
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Report Schedules" size="lg">
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-earth-600" />
        </div>
      ) : showForm ? (
        <ScheduleForm
          scheduleId={editingId}
          onClose={() => { setShowForm(false); setEditingId(null) }}
          onSuccess={() => {
            setShowForm(false)
            setEditingId(null)
            queryClient.invalidateQueries({ queryKey: ["report-schedules"] })
          }}
        />
      ) : (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => { setEditingId(null); setShowForm(true) }}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-primary text-white rounded-lg hover:bg-lsc-primary/90 transition-colors text-sm"
            >
              <Plus className="w-4 h-4" />
              New Schedule
            </button>
          </div>

          {schedules.length === 0 ? (
            <div className="text-center py-10 bg-earth-50 dark:bg-earth-900 rounded-lg">
              <Clock className="w-10 h-10 text-lsc-dark/50 dark:text-lsc-cream/50 mx-auto mb-3" />
              <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
                No report schedules configured yet.
              </p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[60vh] overflow-y-auto">
              {schedules.map((s) => (
                <div
                  key={s.id}
                  className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-4"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="min-w-0 flex-1">
                      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate">
                        {s.name}
                      </h3>
                      <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-0.5">
                        {describeSchedule(s)}
                      </p>
                    </div>
                    <span
                      className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${
                        s.is_active
                          ? "bg-status-success-100 text-status-success-800 dark:bg-status-success-900 dark:text-status-success-200"
                          : "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900 dark:text-status-danger-200"
                      }`}
                    >
                      {s.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-xs mb-3">
                    <div>
                      <span className="text-lsc-dark/50 dark:text-lsc-cream/50">Type</span>
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {REPORT_TYPE_LABELS[s.report_type] || s.report_type}
                      </p>
                    </div>
                    <div>
                      <span className="text-lsc-dark/50 dark:text-lsc-cream/50">Format</span>
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {FORMAT_LABELS[s.output_format] || s.output_format}
                      </p>
                    </div>
                    <div>
                      <span className="text-lsc-dark/50 dark:text-lsc-cream/50">Recipients</span>
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {s.recipient_emails.length}
                      </p>
                    </div>
                  </div>

                  {s.last_run_at && (
                    <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mb-2">
                      Last run: {new Date(s.last_run_at).toLocaleString()}
                      {s.last_status && ` (${s.last_status})`}
                    </p>
                  )}
                  {s.next_run_at && (
                    <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mb-3">
                      Next run: {new Date(s.next_run_at).toLocaleString()}
                    </p>
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={() => { setEditingId(s.id); setShowForm(true) }}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs bg-earth-500 text-white rounded hover:bg-lsc-rose transition-colors"
                    >
                      <Edit2 className="w-3 h-3" /> Edit
                    </button>
                    <button
                      onClick={() => setPendingDeleteId(s.id)}
                      disabled={deleteMutation.isPending}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs bg-status-danger-500 text-white rounded hover:bg-status-danger-600 disabled:opacity-50 transition-colors"
                    >
                      <Trash2 className="w-3 h-3" /> Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <DestructiveActionDialog
        isOpen={pendingDeleteId !== null}
        title="Delete Schedule"
        message="Are you sure you want to delete this schedule? This action cannot be undone."
        isLoading={deleteMutation.isPending}
        onConfirm={() => pendingDeleteId !== null && deleteMutation.mutate(pendingDeleteId)}
        onCancel={() => setPendingDeleteId(null)}
      />
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// Form sub-component
// ---------------------------------------------------------------------------

interface ScheduleFormProps {
  scheduleId: number | null
  onClose: () => void
  onSuccess: () => void
}

function ScheduleForm({ scheduleId, onClose, onSuccess }: ScheduleFormProps) {
  const [loading, setLoading] = useState(false)
  const [emailInput, setEmailInput] = useState("")
  const [formData, setFormData] = useState<ScheduleFormData>({
    name: "",
    report_type: "circulation",
    output_format: "pdf",
    frequency: "weekly",
    day_of_week: 0,
    day_of_month: 1,
    time_of_day: "08:00",
    recipient_emails: [],
    is_active: true,
  })

  useEffect(() => {
    if (!scheduleId) return
    let cancelled = false
    fetchSchedule(scheduleId).then((s) => {
      if (cancelled) return
      setFormData({
        name: s.name,
        report_type: s.report_type,
        output_format: s.output_format,
        frequency: s.frequency,
        day_of_week: s.day_of_week ?? 0,
        day_of_month: s.day_of_month ?? 1,
        time_of_day: s.time_of_day,
        recipient_emails: s.recipient_emails ?? [],
        is_active: s.is_active,
      })
    }).catch((err) => {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error("Failed to load schedule")
    })
    return () => { cancelled = true }
  }, [scheduleId])

  const set = useCallback(
    <K extends keyof ScheduleFormData>(key: K, value: ScheduleFormData[K]) =>
      setFormData((prev) => ({ ...prev, [key]: value })),
    [],
  )

  const addEmail = () => {
    const trimmed = emailInput.trim()
    if (!trimmed) return
    if (!trimmed.includes("@")) {
      toast.error("Please enter a valid email address")
      return
    }
    if (!formData.recipient_emails.includes(trimmed)) {
      set("recipient_emails", [...formData.recipient_emails, trimmed])
      setEmailInput("")
    }
  }

  const removeEmail = (email: string) => {
    set("recipient_emails", formData.recipient_emails.filter((e) => e !== email))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name.trim()) {
      toast.error("Schedule name is required")
      return
    }
    if (formData.recipient_emails.length === 0) {
      toast.error("At least one recipient email is required")
      return
    }

    setLoading(true)
    try {
      if (scheduleId) {
        await updateSchedule(scheduleId, formData)
        toast.success("Schedule updated")
      } else {
        await createSchedule(formData)
        toast.success("Schedule created")
      }
      onSuccess()
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error("Failed to save schedule")
    } finally {
      setLoading(false)
    }
  }

  const inputCls = "w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
  const labelCls = "block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="rs-name" className={labelCls}>Schedule Name *</label>
        <input
          id="rs-name"
          type="text"
          value={formData.name}
          onChange={(e) => set("name", e.target.value)}
          className={inputCls}
          required
          placeholder="e.g. Weekly Circulation Report"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="rs-type" className={labelCls}>Report Type *</label>
          <select
            id="rs-type"
            value={formData.report_type}
            onChange={(e) => set("report_type", e.target.value)}
            className={inputCls}
          >
            {Object.entries(REPORT_TYPE_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="rs-format" className={labelCls}>Output Format *</label>
          <select
            id="rs-format"
            value={formData.output_format}
            onChange={(e) => set("output_format", e.target.value)}
            className={inputCls}
          >
            {Object.entries(FORMAT_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="rs-freq" className={labelCls}>Frequency *</label>
          <select
            id="rs-freq"
            value={formData.frequency}
            onChange={(e) => set("frequency", e.target.value)}
            className={inputCls}
          >
            {Object.entries(FREQUENCY_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="rs-time" className={labelCls}>Time of Day</label>
          <input
            id="rs-time"
            type="time"
            value={formData.time_of_day}
            onChange={(e) => set("time_of_day", e.target.value)}
            className={inputCls}
          />
        </div>
      </div>

      {formData.frequency === "weekly" && (
        <div>
          <label htmlFor="rs-dow" className={labelCls}>Day of Week</label>
          <select
            id="rs-dow"
            value={formData.day_of_week}
            onChange={(e) => set("day_of_week", parseInt(e.target.value))}
            className={inputCls}
          >
            {WEEKDAY_LABELS.map((label, idx) => (
              <option key={idx} value={idx}>{label}</option>
            ))}
          </select>
        </div>
      )}

      {formData.frequency === "monthly" && (
        <div>
          <label htmlFor="rs-dom" className={labelCls}>Day of Month (1-31)</label>
          <input
            id="rs-dom"
            type="number"
            min={1}
            max={31}
            value={formData.day_of_month}
            onChange={(e) => set("day_of_month", parseInt(e.target.value))}
            className={inputCls}
          />
        </div>
      )}

      <div>
        <label htmlFor="rs-email" className={labelCls}>
          <Mail className="w-3.5 h-3.5 inline mr-1" />
          Recipient Emails *
        </label>
        <div className="flex gap-2 mb-2">
          <input
            id="rs-email"
            type="email"
            value={emailInput}
            onChange={(e) => setEmailInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addEmail() } }}
            className={`flex-1 ${inputCls}`}
            placeholder="Enter email address"
          />
          <button
            type="button"
            onClick={addEmail}
            className="px-3 py-2 bg-earth-300 dark:bg-earth-700 rounded-lg hover:bg-earth-400 dark:hover:bg-earth-600 text-sm"
          >
            Add
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {formData.recipient_emails.map((email) => (
            <span
              key={email}
              className="px-2 py-1 bg-earth-100 dark:bg-earth-800 text-earth-800 dark:text-lsc-rose-light/80 rounded text-xs flex items-center gap-1"
            >
              {email}
              <button type="button" onClick={() => removeEmail(email)} className="ml-1 hover:text-status-danger-600">
                x
              </button>
            </span>
          ))}
        </div>
      </div>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={formData.is_active}
          onChange={(e) => set("is_active", e.target.checked)}
          className="w-4 h-4"
        />
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active</span>
      </label>

      <div className="flex gap-2 justify-end pt-4 border-t border-lsc-border dark:border-earth-700">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-800 rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 text-sm bg-lsc-primary text-white rounded-lg hover:bg-lsc-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          {loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
          {scheduleId ? "Update" : "Create"} Schedule
        </button>
      </div>
    </form>
  )
}
