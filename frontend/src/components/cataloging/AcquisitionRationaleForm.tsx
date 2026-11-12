/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, type FormEvent } from 'react'
import { Loader2, Check } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  listBehaviorTags,
  createRationale,
  updateRationale,
  getRationale,
} from '@/api/acquisitionRationale'
import { CHALLENGE_REASON_LABELS } from '@/api/domains/content/book-challenges-api'
import type {
  BehaviorTag,
  SignalType,
  WeedingCondition,
  ChallengeReason,
} from '@/types/acquisitionRationale'
import { SignalLinkSelector } from './SignalLinkSelector'
import { SimilarRationalesPanel } from './SimilarRationalesPanel'

const SIGNAL_TYPE_LABELS: Record<SignalType, string> = {
  desk_question: 'Desk Question',
  purchase_request: 'Purchase Request',
  agent_conversation: 'Agent Conversation',
  staff_observation: 'Staff Observation',
  review_publication: 'Review Publication',
  awards_list: 'Awards List',
  banned_elsewhere: 'Banned Elsewhere',
  community_request: 'Community Request',
  gap_in_collection: 'Gap in Collection',
  replacement: 'Replacement',
  other: 'Other',
}
const SIGNAL_TYPES = Object.keys(SIGNAL_TYPE_LABELS) as SignalType[]

const WEEDING_CONDITION_LABELS: Record<WeedingCondition, string> = {
  ephemeral_2yr: 'Ephemeral (2 years)',
  current_5yr: 'Current (5 years)',
  foundational_indefinite: 'Foundational (indefinite)',
  circ_threshold: 'Circulation Threshold',
  damaged_only: 'Damaged Only',
  signal_persistence: 'Signal Persistence',
  never_weed: 'Never Weed',
}
const WEEDING_CONDITIONS = Object.keys(WEEDING_CONDITION_LABELS) as WeedingCondition[]

const CHALLENGE_REASONS = Object.keys(CHALLENGE_REASON_LABELS) as ChallengeReason[]

const SIGNAL_TABLES: Partial<Record<SignalType, string>> = {
  desk_question: 'reference_questions',
  purchase_request: 'patron_purchase_requests',
  agent_conversation: 'agent_conversations',
}

const labelTextClass =
  'block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1'

const inputClass =
  'w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 ' +
  'bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream ' +
  'focus:outline-none focus:ring-2 focus:ring-lsc-rose'

const checkboxClass =
  'w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-2 focus:ring-lsc-rose'

const checkboxLabelClass =
  'flex items-start gap-2 text-sm text-lsc-dark dark:text-lsc-cream py-1 cursor-pointer'

const fieldsetClass =
  'border border-lsc-border dark:border-earth-700 rounded-xl p-3'

const legendClass =
  'px-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream/80'

export interface AcquisitionRationaleFormProps {
  catalogItemId: number
  onSaved: () => void
  mode?: 'create' | 'edit'
}

export function AcquisitionRationaleForm({
  catalogItemId,
  onSaved,
  mode = 'create',
}: AcquisitionRationaleFormProps): React.ReactElement {
  const { t } = useTranslation()
  const [tags, setTags] = useState<BehaviorTag[]>([])
  const [signalType, setSignalType] = useState<SignalType | ''>('')
  const [signalRefTable, setSignalRefTable] = useState<string | null>(null)
  const [signalRefId, setSignalRefId] = useState<number | null>(null)
  const [signalNote, setSignalNote] = useState('')
  const [policyClause, setPolicyClause] = useState('')
  const [primaryUseCase, setPrimaryUseCase] = useState('')
  const [secondaryUseCases, setSecondaryUseCases] = useState<string[]>([])
  const [weedingCondition, setWeedingCondition] = useState<WeedingCondition>('current_5yr')
  const [weedingNote, setWeedingNote] = useState('')
  const [anticipated, setAnticipated] = useState<ChallengeReason[]>([])
  const [acknowledged, setAcknowledged] = useState(false)
  const [patronVisible, setPatronVisible] = useState(false)
  const [publicSummary, setPublicSummary] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listBehaviorTags()
      .then(setTags)
      .catch((e) => setError(String(e)))

    if (mode === 'edit') {
      getRationale(catalogItemId)
        .then((r) => {
          if (!r) return
          setSignalType(r.signal_type)
          setSignalRefTable(r.signal_ref_table)
          setSignalRefId(r.signal_ref_id)
          setSignalNote(r.signal_note ?? '')
          setPolicyClause(r.policy_clause ?? '')
          setPrimaryUseCase(r.primary_use_case_slug)
          setSecondaryUseCases(r.secondary_use_case_slugs)
          setWeedingCondition(r.weeding_condition)
          setWeedingNote(r.weeding_signal_note ?? '')
          setAnticipated(r.anticipated_challenge_reasons)
          setAcknowledged(r.anticipated_challenge_acknowledged)
          setPatronVisible(r.patron_visible)
          setPublicSummary(r.public_summary ?? '')
        })
        .catch((e) => setError(String(e)))
    }
  }, [catalogItemId, mode])

  const valid = signalType !== '' && primaryUseCase !== ''

  async function handleSave(e: FormEvent) {
    e.preventDefault()
    if (!valid) return
    setSaving(true)
    setError(null)
    try {
      const payload = {
        signal_type: signalType as SignalType,
        signal_ref_table: signalRefTable,
        signal_ref_id: signalRefId,
        signal_note: signalNote || null,
        policy_clause: policyClause || null,
        primary_use_case_slug: primaryUseCase,
        secondary_use_case_slugs: secondaryUseCases,
        weeding_condition: weedingCondition,
        weeding_signal_note: weedingNote || null,
        anticipated_challenge_reasons: anticipated,
        anticipated_challenge_acknowledged: acknowledged,
        patron_visible: patronVisible,
        public_summary: publicSummary || null,
      }
      if (mode === 'edit') {
        await updateRationale(catalogItemId, payload)
      } else {
        await createRationale(catalogItemId, payload)
      }
      onSaved()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      setError(t('acquisitionRationale.errorPrefix', { message }))
    } finally {
      setSaving(false)
    }
  }

  const tagsByCategory = tags.reduce<Record<string, BehaviorTag[]>>((acc, tag) => {
    ;(acc[tag.category] ??= []).push(tag)
    return acc
  }, {})

  const allowedSignalTable = signalType ? SIGNAL_TABLES[signalType] : undefined

  return (
    <form
      onSubmit={handleSave}
      aria-label={t('acquisitionRationale.title')}
      className="space-y-4 mt-4 pt-4 border-t border-lsc-border dark:border-earth-700"
    >
      <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
        {t('acquisitionRationale.title')}
      </h2>

      <label className="block">
        <span className={labelTextClass}>{t('acquisitionRationale.signalLabel')}</span>
        <select
          value={signalType}
          onChange={(e) => setSignalType(e.target.value as SignalType | '')}
          required
          className={inputClass}
        >
          <option value="">{t('acquisitionRationale.selectOption')}</option>
          {SIGNAL_TYPES.map((s) => (
            <option key={s} value={s}>
              {SIGNAL_TYPE_LABELS[s]}
            </option>
          ))}
        </select>
      </label>

      {allowedSignalTable && (
        <SignalLinkSelector
          catalogItemId={catalogItemId}
          allowedTable={allowedSignalTable}
          selectedTable={signalRefTable}
          selectedId={signalRefId}
          onSelect={(table, id) => {
            setSignalRefTable(table)
            setSignalRefId(id)
          }}
        />
      )}

      <label className="block">
        <span className={labelTextClass}>{t('acquisitionRationale.signalNote')}</span>
        <textarea
          value={signalNote}
          onChange={(e) => setSignalNote(e.target.value)}
          rows={2}
          className={inputClass}
        />
      </label>

      <label className="block">
        <span className={labelTextClass}>{t('acquisitionRationale.policyClauseLabel')}</span>
        <input
          type="text"
          value={policyClause}
          onChange={(e) => setPolicyClause(e.target.value)}
          className={inputClass}
        />
      </label>

      <label className="block">
        <span className={labelTextClass}>{t('acquisitionRationale.primaryUseCaseLabel')}</span>
        <select
          value={primaryUseCase}
          onChange={(e) => setPrimaryUseCase(e.target.value)}
          required
          className={inputClass}
        >
          <option value="">{t('acquisitionRationale.selectOption')}</option>
          {Object.entries(tagsByCategory).map(([cat, items]) => (
            <optgroup key={cat} label={cat}>
              {items.map((tg) => (
                <option key={tg.slug} value={tg.slug}>
                  {tg.label}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>

      <fieldset className={fieldsetClass}>
        <legend className={legendClass}>
          {t('acquisitionRationale.secondaryUseCaseLabel')}
        </legend>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4">
          {tags.map((tag) => (
            <label key={tag.slug} className={checkboxLabelClass}>
              <input
                type="checkbox"
                checked={secondaryUseCases.includes(tag.slug)}
                disabled={tag.slug === primaryUseCase}
                onChange={(e) =>
                  setSecondaryUseCases((prev) =>
                    e.target.checked
                      ? [...prev, tag.slug]
                      : prev.filter((s) => s !== tag.slug),
                  )
                }
                className={checkboxClass}
              />
              <span>{tag.label}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <label className="block">
        <span className={labelTextClass}>{t('acquisitionRationale.weedingConditionLabel')}</span>
        <select
          value={weedingCondition}
          onChange={(e) => setWeedingCondition(e.target.value as WeedingCondition)}
          required
          className={inputClass}
        >
          {WEEDING_CONDITIONS.map((w) => (
            <option key={w} value={w}>
              {WEEDING_CONDITION_LABELS[w]}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className={labelTextClass}>{t('acquisitionRationale.weedingNoteLabel')}</span>
        <textarea
          value={weedingNote}
          onChange={(e) => setWeedingNote(e.target.value)}
          rows={2}
          className={inputClass}
        />
      </label>

      <fieldset className={fieldsetClass}>
        <legend className={legendClass}>
          {t('acquisitionRationale.anticipatedChallengesLabel')}
        </legend>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4">
          {CHALLENGE_REASONS.map((r) => (
            <label key={r} className={checkboxLabelClass}>
              <input
                type="checkbox"
                checked={anticipated.includes(r)}
                onChange={(e) =>
                  setAnticipated((prev) =>
                    e.target.checked ? [...prev, r] : prev.filter((x) => x !== r),
                  )
                }
                className={checkboxClass}
              />
              <span>{CHALLENGE_REASON_LABELS[r]}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {anticipated.length > 0 && (
        <label className={checkboxLabelClass}>
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            className={checkboxClass}
          />
          <span>{t('acquisitionRationale.anticipatedAcknowledgeLabel')}</span>
        </label>
      )}

      <label className={checkboxLabelClass}>
        <input
          type="checkbox"
          checked={patronVisible}
          onChange={(e) => setPatronVisible(e.target.checked)}
          className={checkboxClass}
        />
        <span>{t('acquisitionRationale.patronVisibleLabel')}</span>
      </label>

      {patronVisible && (
        <label className="block">
          <span className={labelTextClass}>
            {t('acquisitionRationale.publicSummaryLabel')}
          </span>
          <textarea
            value={publicSummary}
            onChange={(e) => setPublicSummary(e.target.value)}
            required
            rows={3}
            className={inputClass}
          />
        </label>
      )}

      <SimilarRationalesPanel
        query={
          (publicSummary || '').trim() ||
          [signalNote, primaryUseCase].filter(Boolean).join(' ').trim()
        }
      />

      {error && (
        <p role="alert" className="text-sm text-lsc-rose">
          {error}
        </p>
      )}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={!valid || saving}
          className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium flex items-center gap-2 transition-colors"
        >
          {saving ? (
            <Loader2 aria-hidden="true" className="w-4 h-4 motion-safe:animate-spin" />
          ) : (
            <Check aria-hidden="true" className="w-4 h-4" />
          )}
          {saving ? t('acquisitionRationale.saving') : t('acquisitionRationale.save')}
        </button>
      </div>
    </form>
  )
}
