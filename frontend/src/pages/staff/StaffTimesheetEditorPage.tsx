/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Manager-only view: list staff, pick a date, edit/add/delete time entries.
 */
import { useCallback, useEffect, useMemo, useState } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { listStaff, type StaffMember } from "@/api/staff-api/staff-management"
import {
  adminListEntries,
  adminUpdateEntry,
  adminCreateEntry,
  adminDeleteEntry,
  type TimeEntry,
} from "@/api/domains/staff/staff-presence-api"

const ENTRY_TYPES = ["clock_in", "clock_out", "break_start", "break_end"] as const

function todayISO(): string {
  const d = new Date()
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, "0")
  const dd = String(d.getDate()).padStart(2, "0")
  return `${yyyy}-${mm}-${dd}`
}

function isoToLocalInput(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ""
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function localInputToISO(local: string): string {
  if (!local) return ""
  const d = new Date(local)
  if (isNaN(d.getTime())) return ""
  return d.toISOString()
}

function validatePunch(
  entryType: string,
  iso: string,
  shiftDate: string,
  others: Pick<TimeEntry, "entry_type" | "recorded_at">[],
): string | null {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return "Pick a valid date and time."
  if (t > Date.now() + 60_000) return "That time is in the future."
  if (isoToLocalInput(iso).slice(0, 10) !== shiftDate) {
    return "That time falls on a different day than the selected shift date."
  }
  const timesOf = (type: string) =>
    others.filter(o => o.entry_type === type).map(o => new Date(o.recorded_at).getTime())
  if (entryType === "clock_out") {
    const clockIns = timesOf("clock_in")
    if (clockIns.length > 0 && t <= Math.min(...clockIns)) {
      return "Clock-out must be after clock-in."
    }
  }
  if (entryType === "clock_in") {
    const clockOuts = timesOf("clock_out")
    if (clockOuts.length > 0 && t >= Math.max(...clockOuts)) {
      return "Clock-in must be before clock-out."
    }
  }
  if (entryType === "break_end") {
    const breakStarts = timesOf("break_start")
    if (breakStarts.length === 0) return "Add the break start first, then the break end."
    if (!breakStarts.some(s => s < t)) return "Break end must be after its break start."
  }
  return null
}

export default function StaffTimesheetEditorPage() {
  const { token } = useAuth()
  const [staff, setStaff] = useState<StaffMember[]>([])
  const [staffId, setStaffId] = useState<number | null>(null)
  const [shiftDate, setShiftDate] = useState<string>(todayISO())
  const [entries, setEntries] = useState<TimeEntry[]>([])
  const [loadingStaff, setLoadingStaff] = useState(true)
  const [loadingEntries, setLoadingEntries] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [draft, setDraft] = useState<{ entry_type: string; recorded_local: string; notes: string }>({
    entry_type: "clock_out",
    recorded_local: "",
    notes: "",
  })
  const [draftError, setDraftError] = useState<string | null>(null)
  const [dirtyIds, setDirtyIds] = useState<Set<number>>(new Set())
  const hasUnsaved = dirtyIds.size > 0

  const setRowDirty = useCallback((entryId: number, isDirty: boolean) => {
    setDirtyIds(prev => {
      if (isDirty === prev.has(entryId)) return prev
      const next = new Set(prev)
      if (isDirty) next.add(entryId)
      else next.delete(entryId)
      return next
    })
  }, [])

  useEffect(() => {
    if (!hasUnsaved) return
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ""
    }
    window.addEventListener("beforeunload", onBeforeUnload)
    return () => window.removeEventListener("beforeunload", onBeforeUnload)
  }, [hasUnsaved])

  useEffect(() => {
    if (!token) return
    let cancelled = false
    setLoadingStaff(true)
    ;(async () => {
      try {
        // Anyone who can clock in must be editable here, not just role "staff":
        // super_admin, admin, director, and bookmobile staff work shifts too.
        // Patrons/children are excluded by only querying employee roles.
        const EMPLOYEE_ROLES = ["staff", "admin", "director", "super_admin", "bookmobile"]
        const results = await Promise.all(
          EMPLOYEE_ROLES.map(role => listStaff(token, 1, 100, { role })),
        )
        if (cancelled) return
        const byId = new Map<number, StaffMember>()
        for (const r of results) {
          for (const s of r.staff) {
            if (s.is_active) byId.set(s.id, s)
          }
        }
        setStaff([...byId.values()].sort((a, b) => a.first_name.localeCompare(b.first_name)))
      } catch (e) {
        if (!cancelled) setErr(String((e as Error)?.message ?? e))
      } finally {
        if (!cancelled) setLoadingStaff(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  const loadEntries = async (sid: number, day: string) => {
    setLoadingEntries(true)
    setErr(null)
    try {
      const data = await adminListEntries(sid, day)
      setEntries(data)
    } catch (e) {
      setErr(`Couldn't load entries: ${String((e as Error).message ?? e)}`)
      setEntries([])
    } finally {
      setLoadingEntries(false)
    }
  }

  useEffect(() => {
    if (staffId != null) loadEntries(staffId, shiftDate)
  }, [staffId, shiftDate])

  const selectedStaff = useMemo(
    () => staff.find(s => s.id === staffId) ?? null,
    [staff, staffId],
  )

  const handleSaveTime = async (entry: TimeEntry, newLocal: string): Promise<string | null> => {
    const iso = localInputToISO(newLocal)
    if (!iso) return "Pick a valid date and time."
    const validationError = validatePunch(
      entry.entry_type,
      iso,
      shiftDate,
      entries.filter(e => e.id !== entry.id),
    )
    if (validationError) return validationError
    setBusy(true)
    setErr(null)
    try {
      const updated = await adminUpdateEntry(entry.id, { recorded_at: iso })
      setEntries(prev => prev.map(e => (e.id === entry.id ? updated : e)))
    } catch (e) {
      setErr(`Save failed: ${String((e as Error).message ?? e)}`)
    } finally {
      setBusy(false)
    }
    return null
  }

  const handleDelete = async (entry: TimeEntry) => {
    if (!window.confirm(`Delete this ${entry.entry_type} entry? This cannot be undone.`)) return
    setBusy(true)
    setErr(null)
    try {
      await adminDeleteEntry(entry.id)
      setEntries(prev => prev.filter(e => e.id !== entry.id))
      setRowDirty(entry.id, false)
    } catch (e) {
      setErr(`Delete failed: ${String((e as Error).message ?? e)}`)
    } finally {
      setBusy(false)
    }
  }

  const handleAdd = async () => {
    if (staffId == null) return
    const iso = localInputToISO(draft.recorded_local)
    if (!iso) {
      setDraftError("Pick a recorded time first.")
      return
    }
    const validationError = validatePunch(draft.entry_type, iso, shiftDate, entries)
    if (validationError) {
      setDraftError(validationError)
      return
    }
    setDraftError(null)
    setBusy(true)
    setErr(null)
    try {
      const payload: {
        staff_id: number
        entry_type: string
        recorded_at: string
        shift_date: string
        notes?: string
      } = {
        staff_id: staffId,
        entry_type: draft.entry_type,
        recorded_at: iso,
        shift_date: shiftDate,
      }
      if (draft.notes) payload.notes = draft.notes
      const created = await adminCreateEntry(payload)
      setEntries(prev => [...prev, created].sort((a, b) => a.recorded_at.localeCompare(b.recorded_at)))
      setDraft({ entry_type: "clock_out", recorded_local: "", notes: "" })
    } catch (e) {
      setErr(`Add failed: ${String((e as Error).message ?? e)}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">Timesheet editor</h1>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Manager-only. Adjust missing or incorrect time entries. Edits update shift totals.
        </p>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Staff member</span>
          <select
            value={staffId ?? ""}
            onChange={e => setStaffId(e.target.value ? Number(e.target.value) : null)}
            disabled={loadingStaff}
            className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">{loadingStaff ? "Loading..." : "Pick a staff member"}</option>
            {staff.map(s => (
              <option key={s.id} value={s.id}>
                {s.first_name} {s.last_name} ({s.email})
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Shift date</span>
          <input
            type="date"
            value={shiftDate}
            onChange={e => setShiftDate(e.target.value)}
            className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
          />
        </label>
      </div>

      {err && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/30 border border-status-danger-200 dark:border-status-danger-700 rounded-xl p-3 text-sm text-status-danger-700 dark:text-status-danger-300">
          {err}
        </div>
      )}

      {staffId == null ? (
        <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">Pick a staff member to view their day.</p>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm">
          <div className="p-4 border-b border-lsc-border dark:border-earth-700">
            <h2 className="text-base font-semibold text-lsc-dark dark:text-lsc-cream">
              {selectedStaff ? `${selectedStaff.first_name} ${selectedStaff.last_name}` : "Selected staff"} -- {shiftDate}
            </h2>
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
              {loadingEntries ? "Loading..." : `${entries.length} entries`}
            </p>
          </div>
          <div className="divide-y divide-lsc-border dark:divide-earth-700">
            {entries.map(e => (
              <EntryRow
                key={e.id}
                entry={e}
                busy={busy}
                onSaveTime={newLocal => handleSaveTime(e, newLocal)}
                onDelete={() => handleDelete(e)}
                onDirtyChange={setRowDirty}
              />
            ))}
            {!loadingEntries && entries.length === 0 && (
              <p className="p-4 text-sm text-lsc-dark/60 dark:text-lsc-cream/60">No entries for this day.</p>
            )}
          </div>
          <div className="p-4 border-t border-lsc-border dark:border-earth-700 grid grid-cols-1 sm:grid-cols-4 gap-2 items-end">
            <label className="block">
              <span className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Type</span>
              <select
                value={draft.entry_type}
                onChange={ev => setDraft(d => ({ ...d, entry_type: ev.target.value }))}
                className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
              >
                {ENTRY_TYPES.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Recorded at</span>
              <input
                type="datetime-local"
                value={draft.recorded_local}
                onChange={ev => {
                  setDraftError(null)
                  setDraft(d => ({ ...d, recorded_local: ev.target.value }))
                }}
                aria-invalid={draftError ? true : undefined}
                aria-describedby={draftError ? "draft-recorded-error" : undefined}
                className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
              />
              {draftError && (
                <p id="draft-recorded-error" role="alert" className="mt-1 text-xs text-status-danger-600 dark:text-status-danger-400">
                  {draftError}
                </p>
              )}
            </label>
            <label className="block sm:col-span-1">
              <span className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Reason / note</span>
              <input
                type="text"
                value={draft.notes}
                onChange={ev => setDraft(d => ({ ...d, notes: ev.target.value }))}
                placeholder="Forgot to clock out"
                className="mt-1 block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
              />
            </label>
            <button
              type="button"
              onClick={handleAdd}
              disabled={busy}
              className="h-10 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-lsc-white text-sm font-medium disabled:opacity-50"
            >
              Add entry
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function EntryRow({
  entry,
  busy,
  onSaveTime,
  onDelete,
  onDirtyChange,
}: {
  entry: TimeEntry
  busy: boolean
  onSaveTime: (newLocal: string) => Promise<string | null>
  onDelete: () => void
  onDirtyChange: (entryId: number, isDirty: boolean) => void
}) {
  const [local, setLocal] = useState(isoToLocalInput(entry.recorded_at))
  const [rowError, setRowError] = useState<string | null>(null)
  const errorId = `entry-${entry.id}-time-error`
  const dirty = local !== isoToLocalInput(entry.recorded_at)

  useEffect(() => {
    setLocal(isoToLocalInput(entry.recorded_at))
  }, [entry.recorded_at])

  useEffect(() => {
    onDirtyChange(entry.id, dirty)
  }, [dirty, entry.id, onDirtyChange])

  useEffect(() => {
    const id = entry.id
    return () => onDirtyChange(id, false)
  }, [entry.id, onDirtyChange])

  return (
    <div className="p-4 grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
      <div className="sm:col-span-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
        {entry.entry_type}
      </div>
      <div className="sm:col-span-5">
        <input
          type="datetime-local"
          value={local}
          onChange={e => {
            setRowError(null)
            setLocal(e.target.value)
          }}
          aria-invalid={rowError ? true : undefined}
          aria-describedby={rowError ? errorId : undefined}
          className="block w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
        />
        {rowError && (
          <p id={errorId} role="alert" className="mt-1 text-xs text-status-danger-600 dark:text-status-danger-400">
            {rowError}
          </p>
        )}
      </div>
      <div className="sm:col-span-4 flex justify-end gap-2">
        <button
          type="button"
          disabled={busy || !dirty}
          onClick={async () => setRowError(await onSaveTime(local))}
          className="px-3 py-2 text-xs font-medium rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-lsc-white disabled:opacity-50"
        >
          Save
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onDelete}
          className="px-3 py-2 text-xs font-medium rounded-lg bg-status-danger-600 hover:bg-status-danger-700 text-lsc-white disabled:opacity-50"
        >
          Delete
        </button>
      </div>
      {entry.notes && (
        <div className="sm:col-span-12 text-[11px] text-lsc-dark/50 dark:text-lsc-cream/50">
          {entry.notes}
        </div>
      )}
    </div>
  )
}
