/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * BulkMessageModal -- 5th bulk action on StaffPatronsPage.
 *
 * Two-step flow: compose -> confirm -> send. After send the modal shows a
 * per-recipient status summary so partial failures (capped, no_phone, etc.)
 * are visible rather than buried in a toast.
 */
import { useEffect, useRef, useState } from 'react'
import { Loader2, Send } from 'lucide-react'
import { Modal } from '../ui/Modal'
import type { BulkMessageChannel, BulkMessageResponse } from '@/api/staff-api'

type Step = 'compose' | 'confirm' | 'result'

interface BulkMessageModalProps {
  isOpen: boolean
  onClose: () => void
  recipientCount: number
  onSend: (payload: {
    subject: string | null
    body: string
    channels: BulkMessageChannel[]
  }) => Promise<BulkMessageResponse>
}

const CHANNEL_LABELS: Record<BulkMessageChannel, string> = {
  email: 'Email',
  in_app: 'In-app notification',
  sms: 'SMS',
}

export default function BulkMessageModal({
  isOpen,
  onClose,
  recipientCount,
  onSend,
}: BulkMessageModalProps): React.ReactElement | null {
  const [step, setStep] = useState<Step>('compose')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [channels, setChannels] = useState<BulkMessageChannel[]>(['email', 'in_app'])
  const [isSending, setIsSending] = useState(false)
  const [result, setResult] = useState<BulkMessageResponse | null>(null)
  const [showDetail, setShowDetail] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bodyRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!isOpen) {
      setStep('compose')
      setSubject('')
      setBody('')
      setChannels(['email', 'in_app'])
      setIsSending(false)
      setResult(null)
      setShowDetail(false)
      setError(null)
    }
  }, [isOpen])

  const toggleChannel = (c: BulkMessageChannel) => {
    setChannels(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c])
  }

  const canCompose = body.trim().length > 0 && channels.length > 0
  const canSend = canCompose && !isSending && recipientCount > 0

  const handleConfirm = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canCompose) return
    setStep('confirm')
  }

  const handleSend = async () => {
    setError(null)
    setIsSending(true)
    try {
      const res = await onSend({
        subject: subject.trim() || null,
        body: body.trim(),
        channels,
      })
      setResult(res)
      setStep('result')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Bulk message send failed')
      setStep('compose')
    } finally {
      setIsSending(false)
    }
  }

  if (!isOpen) return null

  const titleByStep: Record<Step, string> = {
    compose: `Bulk message — ${recipientCount} patron${recipientCount === 1 ? '' : 's'}`,
    confirm: 'Confirm bulk send',
    result: 'Bulk send results',
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={titleByStep[step]} size="lg">
      {step === 'compose' && (
        <form onSubmit={handleConfirm} className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-status-danger-50 text-status-danger-800 text-sm" role="alert">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="bulk-msg-subject" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Subject (optional)
            </label>
            <input
              id="bulk-msg-subject"
              type="text"
              maxLength={500}
              value={subject}
              onChange={e => setSubject(e.target.value)}
              placeholder="e.g. Library closed Monday"
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose"
            />
          </div>

          <div>
            <label htmlFor="bulk-msg-body" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Message body
            </label>
            <textarea
              id="bulk-msg-body"
              ref={bodyRef}
              required
              maxLength={10000}
              rows={6}
              value={body}
              onChange={e => setBody(e.target.value)}
              placeholder="Hi {first_name}, ..."
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose resize-y"
            />
            <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              Available placeholders: <code>{'{first_name}'}</code>, <code>{'{last_name}'}</code>, <code>{'{patron_name}'}</code>
            </p>
          </div>

          <fieldset>
            <legend className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Channels</legend>
            <div className="flex flex-wrap gap-3">
              {(['email', 'in_app', 'sms'] as BulkMessageChannel[]).map(c => (
                <label key={c} className="inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                  <input
                    type="checkbox"
                    checked={channels.includes(c)}
                    onChange={() => toggleChannel(c)}
                    className="h-4 w-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
                  />
                  <span>{CHANNEL_LABELS[c]}</span>
                  {c === 'in_app' && (
                    <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">(pending enum migration)</span>
                  )}
                  {c === 'sms' && (
                    <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">(provider not configured)</span>
                  )}
                </label>
              ))}
            </div>
          </fieldset>

          <div className="flex justify-end gap-2 pt-2 border-t border-lsc-border dark:border-earth-700">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream">
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canCompose}
              className="px-4 py-2 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white font-medium disabled:cursor-not-allowed"
            >
              Review
            </button>
          </div>
        </form>
      )}

      {step === 'confirm' && (
        <div className="space-y-4">
          <p className="text-sm text-lsc-dark dark:text-lsc-cream">
            You are about to send this message to{' '}
            <strong>{recipientCount} patron{recipientCount === 1 ? '' : 's'}</strong> via:{' '}
            <strong>{channels.map(c => CHANNEL_LABELS[c]).join(', ')}</strong>.
          </p>
          <div className="p-3 rounded-lg bg-lsc-cream/40 dark:bg-lsc-brown/40 text-sm space-y-2">
            {subject && (
              <div>
                <div className="font-medium text-lsc-dark dark:text-lsc-cream">Subject</div>
                <div className="text-lsc-dark/80 dark:text-lsc-cream/80">{subject}</div>
              </div>
            )}
            <div>
              <div className="font-medium text-lsc-dark dark:text-lsc-cream">Body</div>
              <pre className="whitespace-pre-wrap font-sans text-lsc-dark/80 dark:text-lsc-cream/80">{body}</pre>
            </div>
          </div>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            The daily email cap is enforced. Recipients hit by the cap will be reported as <code>capped</code> in the results.
          </p>
          <div className="flex justify-end gap-2 pt-2 border-t border-lsc-border dark:border-earth-700">
            <button type="button" onClick={() => setStep('compose')} disabled={isSending} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream">
              Back
            </button>
            <button
              type="button"
              onClick={handleSend}
              disabled={!canSend}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white font-medium disabled:cursor-not-allowed"
            >
              {isSending ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" /> : <Send className="w-4 h-4" aria-hidden="true" />}
              <span>Send</span>
            </button>
          </div>
        </div>
      )}

      {step === 'result' && result && (
        <div className="space-y-4" role="status" aria-live="polite">
          <p className="sr-only">
            Message send complete: {result.sent} sent, {result.capped} capped, {result.failed} failed, {result.skipped} skipped.
          </p>
          <div className="grid grid-cols-4 gap-2 text-center">
            <Stat label="Sent" value={result.sent} tone="ok" />
            <Stat label="Capped" value={result.capped} tone="warn" />
            <Stat label="Failed" value={result.failed} tone="danger" />
            <Stat label="Skipped" value={result.skipped} tone="muted" />
          </div>

          {result.per_recipient.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setShowDetail(s => !s)}
                className="text-sm text-lsc-rose hover:underline"
              >
                {showDetail ? 'Hide' : 'Show'} per-recipient detail
              </button>
              {showDetail && (
                <div className="mt-2 max-h-64 overflow-y-auto border border-lsc-border dark:border-earth-700 rounded-lg">
                  <table className="w-full text-sm">
                    <thead className="bg-lsc-cream/40 dark:bg-lsc-brown/40 sticky top-0">
                      <tr>
                        <th className="text-left px-2 py-1">Patron ID</th>
                        <th className="text-left px-2 py-1">Status</th>
                        <th className="text-left px-2 py-1">Channels sent</th>
                        <th className="text-left px-2 py-1">Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.per_recipient.map(r => (
                        <tr key={r.patron_id} className="border-t border-lsc-border dark:border-earth-700">
                          <td className="px-2 py-1">{r.patron_id}</td>
                          <td className="px-2 py-1">{r.status}</td>
                          <td className="px-2 py-1">{r.channels_sent.join(', ') || '—'}</td>
                          <td className="px-2 py-1 text-lsc-dark/70 dark:text-lsc-cream/70">{r.reason || ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end pt-2 border-t border-lsc-border dark:border-earth-700">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium">
              Close
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}

function Stat({ label, value, tone }: { label: string; value: number; tone: 'ok' | 'warn' | 'danger' | 'muted' }) {
  const toneClass = {
    ok: 'text-status-success-700 dark:text-status-success-400',
    warn: 'text-status-warning-700 dark:text-status-warning-400',
    danger: 'text-status-danger-700 dark:text-status-danger-400',
    muted: 'text-lsc-dark/70 dark:text-lsc-cream/70',
  }[tone]
  return (
    <div className="p-3 rounded-lg border border-lsc-border dark:border-earth-700">
      <div className={`text-2xl font-semibold ${toneClass}`}>{value}</div>
      <div className="text-xs uppercase tracking-wide text-lsc-dark/60 dark:text-lsc-cream/60">{label}</div>
    </div>
  )
}
