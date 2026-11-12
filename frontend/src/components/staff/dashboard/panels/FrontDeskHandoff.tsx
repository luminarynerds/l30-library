/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { getShiftHandoff, postShiftHandoff, ShiftHandoffNote } from '@/api/staff-api/desk-state'

function fmtAgo(isoStr: string): string {
  const diff = Date.now() - new Date(isoStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs === 1) return '1h ago'
  return `${hrs}h ago`
}

export default function FrontDeskHandoff() {
  const { token } = useAuth()
  const [note, setNote] = useState<ShiftHandoffNote | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [body, setBody] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    getShiftHandoff(token).then(setNote).catch(() => {})
  }, [token])

  const handleSubmit = async () => {
    if (!token || !body.trim()) return
    setSubmitting(true)
    setErr(null)
    try {
      const created = await postShiftHandoff(token, body.trim())
      setNote(created)
      setBody('')
      setShowForm(false)
    } catch {
      setErr('Failed to save note')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Shift handoff</p>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-xs text-lsc-rose hover:text-lsc-rose/80"
        >
          {showForm ? 'Cancel' : 'Leave a note'}
        </button>
      </div>

      {note && !showForm && (
        <div>
          <p className="text-sm text-lsc-dark dark:text-lsc-cream">{note.body}</p>
          <p className="text-[11px] text-lsc-dark/50 dark:text-lsc-cream/50 mt-1">
            {note.author_name} -- {fmtAgo(note.created_at)}
          </p>
        </div>
      )}

      {!note && !showForm && (
        <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50">No notes from the previous shift.</p>
      )}

      {showForm && (
        <div className="space-y-2">
          <textarea
            value={body}
            onChange={e => setBody(e.target.value)}
            maxLength={500}
            rows={3}
            placeholder="Notes for the next shift..."
            className="w-full rounded-lg bg-lsc-white dark:bg-earth-900 border border-lsc-border dark:border-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/40 dark:placeholder:text-lsc-cream/40 focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
          />
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-lsc-dark/40 dark:text-lsc-cream/40">{body.length}/500</span>
            <button
              onClick={handleSubmit}
              disabled={submitting || !body.trim()}
              className="px-3 py-1.5 text-xs font-medium text-lsc-white bg-lsc-rose hover:bg-lsc-rose/90 rounded-lg motion-safe:hover:scale-[1.03] motion-safe:active:scale-[0.98] transition-all disabled:opacity-50"
            >
              {submitting ? 'Saving...' : 'Save note'}
            </button>
          </div>
          {err && <p className="text-xs text-status-danger-600">{err}</p>}
        </div>
      )}
    </div>
  )
}
