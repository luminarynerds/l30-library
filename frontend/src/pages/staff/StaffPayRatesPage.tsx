/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Manager-only view: list staff, see current pay rates, set a new rate,
 * review per-staff rate history. Mirrors StaffTimesheetEditorPage layout.
 */
import { useEffect, useMemo, useState } from "react"
import { useAuth } from "@/contexts/AuthContext"
import {
  listCurrentPayRates,
  getPayRateHistory,
  setPayRate,
  type CurrentPayRateEntry,
  type PayRateEntry,
} from "@/api/domains/staff/staff-presence-api"
import {
  getPayrollPolicy,
  updatePayrollPolicy,
  type PayrollPolicy,
} from "@/api/fair-scheduling-api"

function todayISO(): string {
  const d = new Date()
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, "0")
  const dd = String(d.getDate()).padStart(2, "0")
  return `${yyyy}-${mm}-${dd}`
}

function fmtRate(rate: number | null | undefined): string {
  if (rate == null) return "--"
  return `$${rate.toFixed(2)}/hr`
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "--"
  return iso
}

export default function StaffPayRatesPage() {
  const { token } = useAuth()
  const [current, setCurrent] = useState<CurrentPayRateEntry[]>([])
  const [loadingCurrent, setLoadingCurrent] = useState(true)
  const [selectedStaffId, setSelectedStaffId] = useState<number | null>(null)
  const [history, setHistory] = useState<PayRateEntry[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [draft, setDraft] = useState<{ hourly_rate: string; effective_from: string; notes: string }>({
    hourly_rate: "",
    effective_from: todayISO(),
    notes: "",
  })

  const loadCurrent = async () => {
    setLoadingCurrent(true)
    setErr(null)
    try {
      const rows = await listCurrentPayRates()
      setCurrent(rows)
    } catch (e) {
      setErr(`Couldn't load active rates: ${String((e as Error).message ?? e)}`)
      setCurrent([])
    } finally {
      setLoadingCurrent(false)
    }
  }


  useEffect(() => {
    if (!token) return
    void loadCurrent()
  }, [token])

  const loadHistory = async (staffId: number) => {
    setLoadingHistory(true)
    setErr(null)
    try {
      const rows = await getPayRateHistory(staffId)
      setHistory(rows)
    } catch (e) {
      setErr(`Couldn't load history: ${String((e as Error).message ?? e)}`)
      setHistory([])
    } finally {
      setLoadingHistory(false)
    }
  }

  useEffect(() => {
    if (selectedStaffId != null) {
      void loadHistory(selectedStaffId)
      setDraft({ hourly_rate: "", effective_from: todayISO(), notes: "" })
    } else {
      setHistory([])
    }
  }, [selectedStaffId])

  const selectedRow = useMemo(
    () => current.find(r => r.staff_id === selectedStaffId) ?? null,
    [current, selectedStaffId],
  )

  const handleSetRate = async () => {
    if (selectedStaffId == null) return
    const rateNum = Number.parseFloat(draft.hourly_rate)
    if (!Number.isFinite(rateNum) || rateNum <= 0) {
      setErr("Enter a positive hourly rate.")
      return
    }
    if (!draft.effective_from) {
      setErr("Pick an effective-from date.")
      return
    }
    setBusy(true)
    setErr(null)
    try {
      // Match StaffTimesheetEditorPage pattern: build payload with notes
      // only when present, to avoid setting notes: undefined under
      // exactOptionalPropertyTypes.
      const payload: {
        staff_id: number
        hourly_rate: number
        effective_from: string
        notes?: string
      } = {
        staff_id: selectedStaffId,
        hourly_rate: rateNum,
        effective_from: draft.effective_from,
      }
      if (draft.notes.trim()) payload.notes = draft.notes.trim()
      await setPayRate(payload)
      await Promise.all([loadCurrent(), loadHistory(selectedStaffId)])
      setDraft({ hourly_rate: "", effective_from: todayISO(), notes: "" })
    } catch (e) {
      setErr(`Save failed: ${String((e as Error).message ?? e)}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">Staff pay rates</h1>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Manager-only. Set hourly rates with an effective date; prior rates are closed automatically
          so historical payroll keeps the rate that was in effect on each shift.
        </p>
      </div>

      {err && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/30 border border-status-danger-200 dark:border-status-danger-700 rounded-xl p-3 text-sm text-status-danger-700 dark:text-status-danger-300">
          {err}
        </div>
      )}

      <PayrollPolicyCard />

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700">
          <h2 className="text-base font-semibold text-lsc-dark dark:text-lsc-cream">Active staff</h2>
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
            {loadingCurrent ? "Loading..." : `${current.length} active staff`}
          </p>
        </div>
        <div className="divide-y divide-lsc-border dark:divide-earth-700">
          {current.map(row => {
            const isOpen = selectedStaffId === row.staff_id
            return (
              <div key={row.staff_id} className="">
                <button
                  type="button"
                  onClick={() => setSelectedStaffId(isOpen ? null : row.staff_id)}
                  className="w-full p-4 grid grid-cols-1 sm:grid-cols-12 gap-3 items-center text-left hover:bg-lsc-white/60 dark:hover:bg-earth-700/40"
                >
                  <div className="sm:col-span-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    {row.staff_name || `Staff #${row.staff_id}`}
                  </div>
                  <div className="sm:col-span-2 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                    {row.role}
                  </div>
                  <div className="sm:col-span-3 text-sm text-lsc-dark dark:text-lsc-cream">
                    {fmtRate(row.hourly_rate)}
                  </div>
                  <div className="sm:col-span-2 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                    Since {fmtDate(row.effective_from)}
                  </div>
                  <div className="sm:col-span-1 text-right text-xs font-medium text-lsc-rose">
                    {isOpen ? "Hide" : "Manage"}
                  </div>
                </button>
                {isOpen && (
                  <div className="px-4 pb-4 space-y-4 bg-lsc-white/40 dark:bg-earth-900/40">
                    <RateHistoryPanel
                      loading={loadingHistory}
                      history={history}
                      staffName={selectedRow?.staff_name ?? ""}
                    />
                    <SetRateForm
                      busy={busy}
                      draft={draft}
                      onChange={setDraft}
                      onSubmit={handleSetRate}
                    />
                  </div>
                )}
              </div>
            )
          })}
          {!loadingCurrent && current.length === 0 && (
            <p className="p-4 text-sm text-lsc-dark/60 dark:text-lsc-cream/60">No active staff found.</p>
          )}
        </div>
      </div>
    </div>
  )
}

type PolicyDraft = {
  overtime_multiplier: string
  holiday_multiplier: string
  weekend_differential: string
  evening_differential: string
  default_ot_threshold_hours: string
  evening_start_local: string
}

type PolicyNumberKey = Exclude<keyof PolicyDraft, "evening_start_local">

const POLICY_NUMBER_FIELDS: { key: PolicyNumberKey; label: string; min: number; max: number; step: string }[] = [
  { key: "overtime_multiplier", label: "Overtime multiplier", min: 1, max: 3, step: "0.05" },
  { key: "holiday_multiplier", label: "Holiday multiplier", min: 1, max: 3, step: "0.05" },
  { key: "weekend_differential", label: "Weekend differential", min: 1, max: 2, step: "0.05" },
  { key: "evening_differential", label: "Evening differential", min: 1, max: 2, step: "0.05" },
  { key: "default_ot_threshold_hours", label: "Overtime after (hrs/week)", min: 20, max: 60, step: "0.5" },
]

function fmtTime12(value: string): string {
  const [hStr, mStr] = value.split(":")
  const h = Number(hStr)
  if (!Number.isFinite(h)) return value
  const suffix = h >= 12 ? "PM" : "AM"
  const h12 = h % 12 === 0 ? 12 : h % 12
  return `${h12}:${mStr ?? "00"} ${suffix}`
}

function draftFromPolicy(policy: PayrollPolicy): PolicyDraft {
  return {
    overtime_multiplier: String(policy.overtime_multiplier),
    holiday_multiplier: String(policy.holiday_multiplier),
    weekend_differential: String(policy.weekend_differential),
    evening_differential: String(policy.evening_differential),
    default_ot_threshold_hours: String(policy.default_ot_threshold_hours),
    evening_start_local: policy.evening_start_local.slice(0, 5),
  }
}

function validatePolicyDraft(draft: PolicyDraft): Partial<Record<keyof PolicyDraft, string>> {
  const errors: Partial<Record<keyof PolicyDraft, string>> = {}
  for (const f of POLICY_NUMBER_FIELDS) {
    const n = Number.parseFloat(draft[f.key])
    if (!Number.isFinite(n) || n < f.min || n > f.max) {
      errors[f.key] = `Enter a number between ${f.min.toFixed(2)} and ${f.max.toFixed(2)}.`
    }
  }
  const t = draft.evening_start_local
  if (!/^\d{2}:\d{2}$/.test(t) || t < "16:00" || t > "22:00") {
    errors.evening_start_local = "Pick a time between 4:00 PM and 10:00 PM."
  }
  return errors
}

export function PayrollPolicyCard() {
  const [policy, setPolicy] = useState<PayrollPolicy | null>(null)
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [mode, setMode] = useState<"read" | "edit" | "confirm">("read")
  const [draft, setDraft] = useState<PolicyDraft | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof PolicyDraft, string>>>({})
  const [saving, setSaving] = useState(false)
  const [saveErr, setSaveErr] = useState<string | null>(null)
  const [savedNote, setSavedNote] = useState(false)

  useEffect(() => {
    let cancelled = false
    getPayrollPolicy()
      .then(p => {
        if (!cancelled) setPolicy(p)
      })
      .catch(e => {
        if (!cancelled) setLoadErr(`Couldn't load the payroll policy: ${String((e as Error).message ?? e)}`)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const startEdit = () => {
    if (!policy) return
    setDraft(draftFromPolicy(policy))
    setFieldErrors({})
    setSaveErr(null)
    setSavedNote(false)
    setMode("edit")
  }

  const review = () => {
    if (!draft) return
    const errors = validatePolicyDraft(draft)
    setFieldErrors(errors)
    if (Object.keys(errors).length === 0) setMode("confirm")
  }

  const confirmSave = async () => {
    if (!draft) return
    setSaving(true)
    setSaveErr(null)
    try {
      const updated = await updatePayrollPolicy({
        overtime_multiplier: Number.parseFloat(draft.overtime_multiplier),
        holiday_multiplier: Number.parseFloat(draft.holiday_multiplier),
        weekend_differential: Number.parseFloat(draft.weekend_differential),
        evening_differential: Number.parseFloat(draft.evening_differential),
        default_ot_threshold_hours: Number.parseFloat(draft.default_ot_threshold_hours),
        evening_start_local: draft.evening_start_local,
      })
      setPolicy(updated)
      setSavedNote(true)
      setMode("read")
    } catch (e) {
      setSaveErr(`Save failed: ${String((e as Error).message ?? e)}`)
      setMode("edit")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm">
      <div className="p-4 border-b border-lsc-border dark:border-earth-700">
        <h2 className="text-base font-semibold text-lsc-dark dark:text-lsc-cream">Payroll policy</h2>
        <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
          Board-approved multipliers and overtime rules. Changes apply to payroll runs going
          forward. Past payroll records keep the rates they were generated with.
        </p>
      </div>

      <div className="p-4 space-y-3">
        {loadErr && (
          <p className="text-sm text-status-danger-700 dark:text-status-danger-300">{loadErr}</p>
        )}
        {!loadErr && !policy && (
          <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">Loading payroll policy...</p>
        )}

        {saveErr && (
          <p role="alert" className="bg-status-danger-50 dark:bg-status-danger-900/30 border border-status-danger-200 dark:border-status-danger-700 rounded-lg p-3 text-sm text-status-danger-700 dark:text-status-danger-300">
            {saveErr}
          </p>
        )}

        {policy && mode === "read" && (
          <>
            {savedNote && (
              <p role="status" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Saved. The new values apply to the next payroll run.
              </p>
            )}
            <ul className="space-y-1 text-sm text-lsc-dark dark:text-lsc-cream">
              <li>{`Overtime pays ${policy.overtime_multiplier}x after ${policy.default_ot_threshold_hours} hrs/week`}</li>
              <li>{`Holiday shifts pay ${policy.holiday_multiplier}x`}</li>
              <li>{`Weekend differential ${policy.weekend_differential}x`}</li>
              <li>{`Evening differential ${policy.evening_differential}x after ${fmtTime12(policy.evening_start_local)}`}</li>
            </ul>
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
              The overtime threshold applies to staff without a scheduling profile; profiles carry
              their own weekly limits.
            </p>
            <button
              type="button"
              onClick={startEdit}
              className="h-10 px-4 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-lsc-white text-sm font-medium"
            >
              Edit policy
            </button>
          </>
        )}

        {policy && draft && mode === "edit" && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {POLICY_NUMBER_FIELDS.map(f => (
                <div key={f.key}>
                  <label
                    htmlFor={`policy-${f.key}`}
                    className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60"
                  >
                    {f.label}
                  </label>
                  <input
                    id={`policy-${f.key}`}
                    type="number"
                    min={f.min}
                    max={f.max}
                    step={f.step}
                    value={draft[f.key]}
                    onChange={ev => setDraft({ ...draft, [f.key]: ev.target.value })}
                    aria-invalid={fieldErrors[f.key] ? true : undefined}
                    aria-describedby={fieldErrors[f.key] ? `policy-${f.key}-error` : undefined}
                    className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
                  />
                  {fieldErrors[f.key] && (
                    <p
                      id={`policy-${f.key}-error`}
                      className="mt-1 text-xs text-status-danger-700 dark:text-status-danger-300"
                    >
                      {fieldErrors[f.key]}
                    </p>
                  )}
                </div>
              ))}
              <div>
                <label
                  htmlFor="policy-evening_start_local"
                  className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60"
                >
                  Evening starts at
                </label>
                <input
                  id="policy-evening_start_local"
                  type="time"
                  value={draft.evening_start_local}
                  onChange={ev => setDraft({ ...draft, evening_start_local: ev.target.value })}
                  aria-invalid={fieldErrors.evening_start_local ? true : undefined}
                  aria-describedby={fieldErrors.evening_start_local ? "policy-evening_start_local-error" : undefined}
                  className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
                />
                {fieldErrors.evening_start_local && (
                  <p
                    id="policy-evening_start_local-error"
                    className="mt-1 text-xs text-status-danger-700 dark:text-status-danger-300"
                  >
                    {fieldErrors.evening_start_local}
                  </p>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={review}
                className="h-10 px-4 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-lsc-white text-sm font-medium"
              >
                Review changes
              </button>
              <button
                type="button"
                onClick={() => setMode("read")}
                className="h-10 px-4 rounded-lg border border-lsc-border dark:border-earth-700 text-sm font-medium text-lsc-dark dark:text-lsc-cream"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {policy && draft && mode === "confirm" && (
          <div className="space-y-3">
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              Save these payroll policy values?
            </p>
            <ul className="space-y-1 text-sm text-lsc-dark dark:text-lsc-cream">
              <li>{`Overtime pays ${draft.overtime_multiplier}x after ${draft.default_ot_threshold_hours} hrs/week`}</li>
              <li>{`Holiday shifts pay ${draft.holiday_multiplier}x`}</li>
              <li>{`Weekend differential ${draft.weekend_differential}x`}</li>
              <li>{`Evening differential ${draft.evening_differential}x after ${fmtTime12(draft.evening_start_local)}`}</li>
            </ul>
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
              These apply to payroll runs going forward. Past payroll records keep the rates they
              were generated with.
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void confirmSave()}
                disabled={saving}
                className="h-10 px-4 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-lsc-white text-sm font-medium disabled:opacity-50"
              >
                Confirm and save
              </button>
              <button
                type="button"
                onClick={() => setMode("edit")}
                disabled={saving}
                className="h-10 px-4 rounded-lg border border-lsc-border dark:border-earth-700 text-sm font-medium text-lsc-dark dark:text-lsc-cream disabled:opacity-50"
              >
                Go back
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function RateHistoryPanel({
  loading,
  history,
  staffName,
}: {
  loading: boolean
  history: PayRateEntry[]
  staffName: string
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm">
      <div className="p-3 border-b border-lsc-border dark:border-earth-700">
        <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
          Rate history{staffName ? ` -- ${staffName}` : ""}
        </h3>
        <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
          {loading ? "Loading..." : `${history.length} change${history.length === 1 ? "" : "s"} on file`}
        </p>
      </div>
      <div className="divide-y divide-lsc-border dark:divide-earth-700">
        {history.map(h => (
          <div key={h.id} className="p-3 grid grid-cols-1 sm:grid-cols-12 gap-2 items-start">
            <div className="sm:col-span-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              ${h.hourly_rate.toFixed(2)}/hr
            </div>
            <div className="sm:col-span-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              {fmtDate(h.effective_from)} -- {fmtDate(h.effective_to) === "--" ? "current" : fmtDate(h.effective_to)}
            </div>
            <div className="sm:col-span-5 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
              {h.notes || ""}
            </div>
          </div>
        ))}
        {!loading && history.length === 0 && (
          <p className="p-3 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
            No rate on file yet. Set one below.
          </p>
        )}
      </div>
    </div>
  )
}

function SetRateForm({
  busy,
  draft,
  onChange,
  onSubmit,
}: {
  busy: boolean
  draft: { hourly_rate: string; effective_from: string; notes: string }
  onChange: (next: { hourly_rate: string; effective_from: string; notes: string }) => void
  onSubmit: () => void
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 grid grid-cols-1 sm:grid-cols-4 gap-2 items-end">
      <label className="block">
        <span className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Hourly rate ($)</span>
        <input
          type="number"
          min="0"
          step="0.01"
          value={draft.hourly_rate}
          onChange={ev => onChange({ ...draft, hourly_rate: ev.target.value })}
          placeholder="20.00"
          className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
        />
      </label>
      <label className="block">
        <span className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Effective from</span>
        <input
          type="date"
          value={draft.effective_from}
          onChange={ev => onChange({ ...draft, effective_from: ev.target.value })}
          className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
        />
      </label>
      <label className="block">
        <span className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Reason / note</span>
        <input
          type="text"
          value={draft.notes}
          onChange={ev => onChange({ ...draft, notes: ev.target.value })}
          placeholder="Annual raise"
          className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
        />
      </label>
      <button
        type="button"
        onClick={onSubmit}
        disabled={busy}
        className="h-10 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-lsc-white text-sm font-medium disabled:opacity-50"
      >
        Set new rate
      </button>
    </div>
  )
}
