/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Bulk-create-recurring form.
 *
 * Posts to POST /events/bulk-from-recurrence. The backend stores the RRULE
 * on a parent event and creates one real child event row per expanded
 * occurrence (linked via parent_event_id). Each child gets independent
 * registrations, capacity, and accommodations.
 *
 * UX contract:
 *   1. User fills inherited-event fields + first-occurrence start/end + RRULE.
 *   2. User MUST click "Preview occurrences" first (dry-run round-trip).
 *   3. User MUST confirm the count looks right (checkbox) to enable submit.
 *   4. Submit calls the same endpoint with dry_run=false, navigates back to
 *      Event Management with a toast on success.
 *
 * The hard cap (52 children) and horizon cap (+366d) are enforced server-
 * side; we surface the 422 detail string to the user verbatim.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { useAuth } from '@/contexts/AuthContext'
import { listBranches } from '@/api/branch-api'
import {
  bulkCreateRecurringEvents,
  type EventBulkCreateDryRunResponse,
  type EventBulkCreateRequest,
  type EventBulkCreateResponse,
} from '@/api/events-api'

interface Props {
  onCancel: () => void
  // Optional override for tests so they can avoid react-router navigation.
  navigateOnSuccess?: ((parentId: number, count: number) => void) | undefined
}

interface FormState {
  title: string
  description: string
  location: string
  audience: string
  category: string
  start_time: string
  end_time: string
  max_attendees: string
  registration_required: boolean
  recurrence_rule: string
  branch_id: string
  image_url: string
  // Accessibility
  wheelchair_accessible: boolean
  asl_provided: boolean
  captioning_provided: boolean
  assistive_listening: boolean
  sensory_friendly: boolean
  large_print_available: boolean
  accessibility_notes: string
  // Age + caregiver
  min_age: string
  max_age: string
  caregiver_required: boolean
  photos_will_be_taken: boolean
}

const EMPTY: FormState = {
  title: '',
  description: '',
  location: '',
  audience: '',
  category: '',
  start_time: '',
  end_time: '',
  max_attendees: '',
  registration_required: false,
  recurrence_rule: '',
  branch_id: '',
  image_url: '',
  wheelchair_accessible: false,
  asl_provided: false,
  captioning_provided: false,
  assistive_listening: false,
  sensory_friendly: false,
  large_print_available: false,
  accessibility_notes: '',
  min_age: '',
  max_age: '',
  caregiver_required: false,
  photos_will_be_taken: false,
}

function buildPayload(s: FormState, dryRun: boolean): EventBulkCreateRequest {
  // Build incrementally so we never assign `undefined` to optional fields
  // (the repo enables exactOptionalPropertyTypes).
  const out: Record<string, unknown> = {
    title: s.title,
    start_time: s.start_time ? new Date(s.start_time).toISOString() : '',
    registration_required: s.registration_required,
    recurrence_rule: s.recurrence_rule,
    max_attendees: s.max_attendees ? Number(s.max_attendees) : null,
    branch_id: s.branch_id ? Number(s.branch_id) : null,
    wheelchair_accessible: s.wheelchair_accessible,
    asl_provided: s.asl_provided,
    captioning_provided: s.captioning_provided,
    assistive_listening: s.assistive_listening,
    sensory_friendly: s.sensory_friendly,
    large_print_available: s.large_print_available,
    caregiver_required: s.caregiver_required,
    photos_will_be_taken: s.photos_will_be_taken,
    dry_run: dryRun,
  }
  if (s.description) out.description = s.description
  if (s.location) out.location = s.location
  if (s.audience) out.audience = s.audience
  if (s.category) out.category = s.category
  if (s.end_time) out.end_time = new Date(s.end_time).toISOString()
  if (s.image_url) out.image_url = s.image_url
  if (s.accessibility_notes) out.accessibility_notes = s.accessibility_notes
  if (s.min_age) out.min_age = Number(s.min_age)
  if (s.max_age) out.max_age = Number(s.max_age)
  return out as unknown as EventBulkCreateRequest
}

export default function EventBulkRecurringForm({ onCancel, navigateOnSuccess }: Props): React.ReactElement {
  const { t } = useTranslation()
  const { token } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<FormState>(EMPTY)
  const [preview, setPreview] = useState<EventBulkCreateDryRunResponse | null>(null)
  const [confirmedCount, setConfirmedCount] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const { data: branches = [] } = useQuery({
    queryKey: ['branches'],
    queryFn: () => listBranches(),
  })

  const setField = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    // Invalidate prior preview if any inherited field changes — guarantees
    // the user can't preview, edit, then submit a different payload than
    // they reviewed.
    setPreview(null)
    setConfirmedCount(false)
  }

  const previewMutation = useMutation({
    mutationFn: () => bulkCreateRecurringEvents(token!, buildPayload(form, true)) as Promise<EventBulkCreateDryRunResponse>,
    onSuccess: (data) => {
      setPreview(data as EventBulkCreateDryRunResponse)
      setErrorMessage(null)
    },
    onError: (e: Error) => {
      setErrorMessage(e.message)
      setPreview(null)
    },
  })

  const submitMutation = useMutation({
    mutationFn: () => bulkCreateRecurringEvents(token!, buildPayload(form, false)) as Promise<EventBulkCreateResponse>,
    onSuccess: (data) => {
      const res = data as EventBulkCreateResponse
      toast.success(t('bulkRecurring.toastCreated').replace('{count}', String(res.count)))
      if (navigateOnSuccess) {
        navigateOnSuccess(res.parent_id, res.count)
      } else {
        navigate('/admin/events')
      }
    },
    onError: (e: Error) => {
      setErrorMessage(e.message)
    },
  })

  const canPreview = Boolean(form.title.trim() && form.start_time && form.recurrence_rule.trim())
  const canSubmit = Boolean(preview && confirmedCount && !submitMutation.isPending)

  const handlePreview = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canPreview) return
    previewMutation.mutate()
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    submitMutation.mutate()
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4"
      aria-label={t('bulkRecurring.formAriaLabel')}
    >
      <div>
        <label htmlFor="bulk-title" className="block text-sm font-medium mb-1">
          {t('bulkRecurring.title')}
        </label>
        <input
          id="bulk-title"
          type="text"
          required
          value={form.title}
          onChange={(e) => setField('title', e.target.value)}
          className="w-full border rounded-lg px-3 py-2"
        />
      </div>

      <div>
        <label htmlFor="bulk-description" className="block text-sm font-medium mb-1">
          {t('bulkRecurring.description')}
        </label>
        <textarea
          id="bulk-description"
          value={form.description}
          onChange={(e) => setField('description', e.target.value)}
          rows={3}
          className="w-full border rounded-lg px-3 py-2"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="bulk-start" className="block text-sm font-medium mb-1">
            {t('bulkRecurring.firstOccurrenceStart')}
          </label>
          <input
            id="bulk-start"
            type="datetime-local"
            required
            value={form.start_time}
            onChange={(e) => setField('start_time', e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="bulk-end" className="block text-sm font-medium mb-1">
            {t('bulkRecurring.firstOccurrenceEnd')}
          </label>
          <input
            id="bulk-end"
            type="datetime-local"
            value={form.end_time}
            onChange={(e) => setField('end_time', e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
          />
        </div>
      </div>

      <div>
        <label htmlFor="bulk-rrule" className="block text-sm font-medium mb-1">
          {t('bulkRecurring.recurrenceRule')}
        </label>
        <textarea
          id="bulk-rrule"
          required
          value={form.recurrence_rule}
          onChange={(e) => setField('recurrence_rule', e.target.value)}
          rows={2}
          placeholder="FREQ=WEEKLY;BYDAY=TU;COUNT=12"
          className="w-full border rounded-lg px-3 py-2 font-mono text-sm"
        />
        <p className="text-xs text-gray-600 mt-1">
          {t('bulkRecurring.recurrenceRuleHelp')}{' '}
          <a
            href="https://www.rfc-editor.org/rfc/rfc5545#section-3.3.10"
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
          >
            {t('bulkRecurring.recurrenceRuleHelpLink')}
          </a>
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="bulk-location" className="block text-sm font-medium mb-1">
            {t('bulkRecurring.location')}
          </label>
          <input
            id="bulk-location"
            type="text"
            value={form.location}
            onChange={(e) => setField('location', e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="bulk-branch" className="block text-sm font-medium mb-1">
            {t('bulkRecurring.branch')}
          </label>
          <select
            id="bulk-branch"
            value={form.branch_id}
            onChange={(e) => setField('branch_id', e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
          >
            <option value="">{t('bulkRecurring.branchNone')}</option>
            {branches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label htmlFor="bulk-audience" className="block text-sm font-medium mb-1">
            {t('bulkRecurring.audience')}
          </label>
          <input
            id="bulk-audience"
            type="text"
            value={form.audience}
            onChange={(e) => setField('audience', e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="bulk-category" className="block text-sm font-medium mb-1">
            {t('bulkRecurring.category')}
          </label>
          <input
            id="bulk-category"
            type="text"
            value={form.category}
            onChange={(e) => setField('category', e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="bulk-capacity" className="block text-sm font-medium mb-1">
            {t('bulkRecurring.capacity')}
          </label>
          <input
            id="bulk-capacity"
            type="number"
            min={1}
            value={form.max_attendees}
            onChange={(e) => setField('max_attendees', e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <input
          id="bulk-reg-required"
          type="checkbox"
          checked={form.registration_required}
          onChange={(e) => setField('registration_required', e.target.checked)}
        />
        <label htmlFor="bulk-reg-required" className="text-sm">
          {t('bulkRecurring.registrationRequired')}
        </label>
      </div>

      <fieldset className="border rounded-lg p-3">
        <legend className="text-sm font-medium px-1">{t('bulkRecurring.accessibilitySection')}</legend>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {([
            'wheelchair_accessible',
            'asl_provided',
            'captioning_provided',
            'assistive_listening',
            'sensory_friendly',
            'large_print_available',
          ] as const).map((flag) => (
            <div key={flag} className="flex items-center gap-2">
              <input
                id={`bulk-${flag}`}
                type="checkbox"
                checked={form[flag]}
                onChange={(e) => setField(flag, e.target.checked)}
              />
              <label htmlFor={`bulk-${flag}`} className="text-sm">
                {t(`bulkRecurring.${flag}`)}
              </label>
            </div>
          ))}
        </div>
        <div className="mt-3">
          <label htmlFor="bulk-a11y-notes" className="block text-sm font-medium mb-1">
            {t('bulkRecurring.accessibilityNotes')}
          </label>
          <textarea
            id="bulk-a11y-notes"
            value={form.accessibility_notes}
            onChange={(e) => setField('accessibility_notes', e.target.value)}
            rows={2}
            className="w-full border rounded-lg px-3 py-2"
          />
        </div>
      </fieldset>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label htmlFor="bulk-min-age" className="block text-sm font-medium mb-1">
            {t('bulkRecurring.minAge')}
          </label>
          <input
            id="bulk-min-age"
            type="number"
            min={0}
            max={120}
            value={form.min_age}
            onChange={(e) => setField('min_age', e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor="bulk-max-age" className="block text-sm font-medium mb-1">
            {t('bulkRecurring.maxAge')}
          </label>
          <input
            id="bulk-max-age"
            type="number"
            min={0}
            max={120}
            value={form.max_age}
            onChange={(e) => setField('max_age', e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
          />
        </div>
        <div className="flex flex-col gap-1 justify-end">
          <div className="flex items-center gap-2">
            <input
              id="bulk-caregiver-required"
              type="checkbox"
              checked={form.caregiver_required}
              onChange={(e) => setField('caregiver_required', e.target.checked)}
            />
            <label htmlFor="bulk-caregiver-required" className="text-sm">
              {t('bulkRecurring.caregiverRequired')}
            </label>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="bulk-photos"
              type="checkbox"
              checked={form.photos_will_be_taken}
              onChange={(e) => setField('photos_will_be_taken', e.target.checked)}
            />
            <label htmlFor="bulk-photos" className="text-sm">
              {t('bulkRecurring.photosWillBeTaken')}
            </label>
          </div>
        </div>
      </div>

      <div>
        <label htmlFor="bulk-image-url" className="block text-sm font-medium mb-1">
          {t('bulkRecurring.imageUrl')}
        </label>
        <input
          id="bulk-image-url"
          type="url"
          value={form.image_url}
          onChange={(e) => setField('image_url', e.target.value)}
          className="w-full border rounded-lg px-3 py-2"
        />
      </div>

      {/* ---- Preview + confirm ---- */}
      <div className="border-t pt-4 space-y-3">
        <button
          type="button"
          onClick={handlePreview}
          disabled={!canPreview || previewMutation.isPending}
          className="px-4 py-2 bg-lsc-brown text-white rounded-lg disabled:opacity-50"
        >
          {previewMutation.isPending ? (
            <span className="inline-flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> {t('bulkRecurring.previewing')}
            </span>
          ) : (
            t('bulkRecurring.previewButton')
          )}
        </button>

        {preview && (
          <div
            role="region"
            aria-label={t('bulkRecurring.previewRegion')}
            className="border rounded-lg p-3 bg-gray-50"
          >
            <p className="font-medium">
              {t('bulkRecurring.previewCount').replace('{count}', String(preview.count))}
            </p>
            <ul className="mt-2 max-h-48 overflow-y-auto text-sm space-y-1">
              {preview.instances.map((inst, i) => (
                <li key={i} className="font-mono">
                  {new Date(inst.start_time).toLocaleString()}
                </li>
              ))}
            </ul>
            <div className="flex items-center gap-2 mt-3">
              <input
                id="bulk-confirm"
                type="checkbox"
                checked={confirmedCount}
                onChange={(e) => setConfirmedCount(e.target.checked)}
              />
              <label htmlFor="bulk-confirm" className="text-sm">
                {t('bulkRecurring.confirmCountLabel')}
              </label>
            </div>
          </div>
        )}

        {errorMessage && (
          <p role="alert" className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
            {errorMessage}
          </p>
        )}
      </div>

      <div className="flex justify-end gap-2 pt-4 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded-lg border"
        >
          {t('bulkRecurring.cancel')}
        </button>
        <button
          type="submit"
          disabled={!canSubmit}
          className="px-4 py-2 bg-lsc-rose text-white rounded-lg disabled:opacity-50"
        >
          {submitMutation.isPending ? (
            <span className="inline-flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden /> {t('bulkRecurring.creating')}
            </span>
          ) : (
            t('bulkRecurring.submitButton')
          )}
        </button>
      </div>
    </form>
  )
}
