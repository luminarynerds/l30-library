/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import FocusTrap from 'focus-trap-react'
import { X, Loader2, AlertTriangle, ArrowRight, Check, GitMerge, Users, ChevronLeft } from "lucide-react"
import type { DuplicatePatron, MergePreview } from "@/api/staff-api"
import { useTranslation, formatCurrency } from '@/i18n'

interface PatronMergeDialogsProps {
  showDuplicatesModal: boolean
  onClose: () => void
  // Duplicate detection
  duplicates: DuplicatePatron[]
  isLoadingDuplicates: boolean
  // Merge preview
  selectedDuplicate: DuplicatePatron | null
  showMergePreviewModal: boolean
  mergePreview: MergePreview | null
  isLoadingMergePreview: boolean
  isMerging: boolean
  mergeOptions: {
    merge_checkouts: boolean
    merge_holds: boolean
    merge_fines: boolean
    merge_history: boolean
  }
  // Handlers
  onSelectDuplicate: (duplicate: DuplicatePatron) => void
  onExecuteMerge: () => void
  onCloseMergePreview: () => void
  onSetMergeOptions: (options: {
    merge_checkouts: boolean
    merge_holds: boolean
    merge_fines: boolean
    merge_history: boolean
  }) => void
}

function MatchBadge({ type, score }: { type: string; score: number }) {
  const color =
    score >= 90
      ? "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300"
      : score >= 70
        ? "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300"
        : "bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light"

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {type} ({score}%)
    </span>
  )
}

function PatronCard({
  patron,
  label,
  highlighted,
}: {
  patron: { id: number; email: string; name?: string; first_name?: string; last_name?: string; library_card?: string; created_at: string }
  label: string
  highlighted?: boolean
}) {
  const name = patron.name || `${(patron as DuplicatePatron).first_name} ${(patron as DuplicatePatron).last_name}`
  return (
    <div
      className={`rounded-lg p-4 ${
        highlighted
          ? "bg-lsc-rose/10 border-2 border-lsc-rose dark:bg-lsc-rose/20"
          : "bg-lsc-cream dark:bg-lsc-brown/50 border border-lsc-border dark:border-earth-700"
      }`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/50 mb-2">
        {label}
      </p>
      <p className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">{name}</p>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{patron.email}</p>
      {patron.library_card && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-1">Card: {patron.library_card}</p>
      )}
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-1">
        Created: {new Date(patron.created_at).toLocaleDateString()}
      </p>
    </div>
  )
}

function DuplicatesList({
  duplicates,
  isLoading,
  onSelect,
  isLoadingMergePreview,
}: {
  duplicates: DuplicatePatron[]
  isLoading: boolean
  onSelect: (d: DuplicatePatron) => void
  isLoadingMergePreview: boolean
}) {
  const { t, language } = useTranslation()
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose mb-3" />
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('patronMergeDialogs.scanningForDuplicateAccounts')}</p>
      </div>
    )
  }

  if (duplicates.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Users className="w-10 h-10 text-status-success-500 mb-3" />
        <p className="font-medium text-lsc-dark dark:text-lsc-cream">No duplicates found</p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          This patron account does not appear to have any duplicate records.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        Found <strong>{duplicates.length}</strong> potential duplicate{duplicates.length !== 1 ? "s" : ""}. Select one to
        preview the merge.
      </p>

      <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
        {duplicates.map((dup) => (
          <button
            key={dup.id}
            onClick={() => onSelect(dup)}
            disabled={isLoadingMergePreview}
            className="w-full text-left p-4 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-cream dark:bg-lsc-brown/50 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors disabled:opacity-50"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                    {dup.first_name} {dup.last_name}
                  </p>
                  <MatchBadge type={dup.match_type} score={dup.match_score} />
                  {!dup.is_active && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-lsc-cream text-lsc-dark/70 dark:bg-earth-800 dark:text-lsc-cream/70">
                      Inactive
                    </span>
                  )}
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{dup.email}</p>
                {dup.phone && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-0.5">{dup.phone}</p>
                )}
                <div className="flex items-center gap-3 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                  <span>{dup.total_checkouts} checkouts</span>
                  <span>{dup.total_holds} holds</span>
                  <span>{formatCurrency(dup.fines_balance, language, 'USD')} fines</span>
                  {dup.library_card && <span>Card: {dup.library_card}</span>}
                </div>
              </div>
              <div className="flex-shrink-0 mt-1">
                {isLoadingMergePreview ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-rose" />
                ) : (
                  <ArrowRight className="w-4 h-4 text-lsc-rose" />
                )}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

function MergePreviewPanel({
  preview,
  mergeOptions,
  isMerging,
  onSetMergeOptions,
  onExecute,
  onBack,
}: {
  preview: MergePreview
  mergeOptions: PatronMergeDialogsProps["mergeOptions"]
  isMerging: boolean
  onSetMergeOptions: PatronMergeDialogsProps["onSetMergeOptions"]
  onExecute: () => void
  onBack: () => void
}) {
  const { t } = useTranslation()
  const [confirmed, setConfirmed] = useState(false)

  const toggleOption = (key: keyof typeof mergeOptions) => {
    onSetMergeOptions({ ...mergeOptions, [key]: !mergeOptions[key] })
  }

  const totalItems =
    (mergeOptions.merge_checkouts ? preview.checkouts_to_transfer : 0) +
    (mergeOptions.merge_holds ? preview.holds_to_transfer : 0) +
    (mergeOptions.merge_fines ? preview.fines_to_transfer : 0) +
    (mergeOptions.merge_history ? preview.history_records_to_transfer : 0)

  return (
    <div className="space-y-5">
      {/* Back button */}
      <button
        onClick={onBack}
        disabled={isMerging}
        className="text-sm text-lsc-rose hover:underline flex items-center gap-1 disabled:opacity-50"
      >
        <ChevronLeft className="w-4 h-4" />
        Back to duplicates
      </button>

      {/* Side by side comparison */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <PatronCard patron={preview.primary_patron} label="Keep (Primary)" highlighted />
        <PatronCard patron={preview.secondary_patron} label="Remove (Secondary)" />
      </div>

      {/* Transfer arrow */}
      <div className="flex items-center justify-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <GitMerge className="w-4 h-4 text-lsc-rose" />
        <span>{t('patronMergeDialogs.dataFromSecondaryWillBe')}</span>
      </div>

      {/* Merge options */}
      <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-lg p-4 space-y-3">
        <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{t('patronMergeDialogs.selectDataToTransfer')}</p>

        <label className="flex items-center justify-between py-2 border-b border-lsc-border dark:border-earth-700 cursor-pointer">
          <div>
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Checkouts</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
              {preview.checkouts_to_transfer} active checkout{preview.checkouts_to_transfer !== 1 ? "s" : ""}
            </p>
          </div>
          <input
            type="checkbox"
            checked={mergeOptions.merge_checkouts}
            onChange={() => toggleOption("merge_checkouts")}
            disabled={isMerging || preview.checkouts_to_transfer === 0}
            className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
          />
        </label>

        <label className="flex items-center justify-between py-2 border-b border-lsc-border dark:border-earth-700 cursor-pointer">
          <div>
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Holds</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
              {preview.holds_to_transfer} active hold{preview.holds_to_transfer !== 1 ? "s" : ""}
            </p>
          </div>
          <input
            type="checkbox"
            checked={mergeOptions.merge_holds}
            onChange={() => toggleOption("merge_holds")}
            disabled={isMerging || preview.holds_to_transfer === 0}
            className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
          />
        </label>

        <label className="flex items-center justify-between py-2 border-b border-lsc-border dark:border-earth-700 cursor-pointer">
          <div>
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Fines</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
              {preview.fines_to_transfer} fine{preview.fines_to_transfer !== 1 ? "s" : ""}
            </p>
          </div>
          <input
            type="checkbox"
            checked={mergeOptions.merge_fines}
            onChange={() => toggleOption("merge_fines")}
            disabled={isMerging || preview.fines_to_transfer === 0}
            className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
          />
        </label>

        <label className="flex items-center justify-between py-2 cursor-pointer">
          <div>
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Reading History</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
              {preview.history_records_to_transfer} history record{preview.history_records_to_transfer !== 1 ? "s" : ""}
            </p>
          </div>
          <input
            type="checkbox"
            checked={mergeOptions.merge_history}
            onChange={() => toggleOption("merge_history")}
            disabled={isMerging || preview.history_records_to_transfer === 0}
            className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
          />
        </label>
      </div>

      {/* Summary */}
      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800/30 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold text-status-warning-800 dark:text-status-warning-300">{t('patronMergeDialogs.thisActionCannotBeUndone')}</p>
            <p className="text-status-warning-700 dark:text-status-warning-400 mt-1">
              {totalItems > 0
                ? `${totalItems} item${totalItems !== 1 ? "s" : ""} will be transferred to the primary account.`
                : "No items selected for transfer."}{" "}
              The secondary account ({preview.secondary_patron.email}) will be permanently deactivated.
            </p>
          </div>
        </div>
      </div>

      {/* Confirmation checkbox */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
          disabled={isMerging}
          className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
        />
        <span className="text-sm text-lsc-dark dark:text-lsc-cream">
          I confirm this merge and understand it cannot be reversed.
        </span>
      </label>

      {/* Action button */}
      <div className="flex justify-end gap-3">
        <button
          onClick={onBack}
          disabled={isMerging}
          className="px-4 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={onExecute}
          disabled={isMerging || !confirmed}
          className="px-4 py-2 text-sm rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isMerging ? (
            <>
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              Merging...
            </>
          ) : (
            <>
              <Check className="w-4 h-4" />
              Execute Merge
            </>
          )}
        </button>
      </div>
    </div>
  )
}

export function PatronMergeDialogs({
  showDuplicatesModal,
  onClose,
  duplicates,
  isLoadingDuplicates,
  selectedDuplicate,
  showMergePreviewModal,
  mergePreview,
  isLoadingMergePreview,
  isMerging,
  mergeOptions,
  onSelectDuplicate,
  onExecuteMerge,
  onCloseMergePreview,
  onSetMergeOptions,
}: PatronMergeDialogsProps) {
  if (!showDuplicatesModal) return null

  const showPreview = showMergePreviewModal && mergePreview && selectedDuplicate

  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={(e) => { if (e.target === e.currentTarget && !isMerging) onClose() }}>
      <FocusTrap active={showDuplicatesModal} focusTrapOptions={{ escapeDeactivates: true }}>
      <div role="dialog" aria-modal="true" aria-labelledby="patron-merge-title" className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <GitMerge className="w-5 h-5 text-lsc-rose" />
            <h2 id="patron-merge-title" className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {showPreview ? "Merge Preview" : "Merge Patrons"}
            </h2>
          </div>
          <button
            onClick={() => { if (!isMerging) onClose() }}
            disabled={isMerging}
            className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {showPreview ? (
          <MergePreviewPanel
            preview={mergePreview}
            mergeOptions={mergeOptions}
            isMerging={isMerging}
            onSetMergeOptions={onSetMergeOptions}
            onExecute={onExecuteMerge}
            onBack={onCloseMergePreview}
          />
        ) : (
          <DuplicatesList
            duplicates={duplicates}
            isLoading={isLoadingDuplicates}
            onSelect={onSelectDuplicate}
            isLoadingMergePreview={isLoadingMergePreview}
          />
        )}
      </div>
      </FocusTrap>
    </div>
  )
}
