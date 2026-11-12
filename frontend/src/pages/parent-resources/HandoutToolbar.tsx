/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Printer, X } from 'lucide-react'
import { useTranslation } from '@/i18n'

interface HandoutToolbarProps {
  sectionsSelected: number
  sectionsTotal: number
  itemsSelected: number
  itemsTotal: number
  largeType: boolean
  qrCodes: boolean
  coverSheet: boolean
  onToggleLargeType: () => void
  onToggleQrCodes: () => void
  onToggleCoverSheet: () => void
  onCancel: () => void
  onPreviewPrint: () => void
}

export function HandoutToolbar({
  sectionsSelected,
  sectionsTotal,
  itemsSelected,
  itemsTotal,
  largeType,
  qrCodes,
  coverSheet,
  onToggleLargeType,
  onToggleQrCodes,
  onToggleCoverSheet,
  onCancel,
  onPreviewPrint,
}: HandoutToolbarProps) {
  const { t } = useTranslation()
  const disabled = sectionsSelected === 0 || itemsSelected === 0

  return (
    <div
      className="bg-lsc-cream/40 dark:bg-earth-800/60 border border-lsc-border dark:border-earth-700 rounded-xl p-4 space-y-3 print:hidden"
      role="region"
      aria-label={t('parentResources.handout.toolbar.regionLabel')}
      data-testid="handout-toolbar"
    >
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
        <span data-testid="handout-toolbar-sections-count">
          {t('parentResources.handout.toolbar.sections', {
            selected: sectionsSelected,
            total: sectionsTotal,
          })}
        </span>
        <span data-testid="handout-toolbar-items-count">
          {t('parentResources.handout.toolbar.items', {
            selected: itemsSelected,
            total: itemsTotal,
          })}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <ToolbarSwitch
          label={t('parentResources.handout.toggle.largeType')}
          checked={largeType}
          onChange={onToggleLargeType}
          testId="handout-toggle-large-type"
        />
        <ToolbarSwitch
          label={t('parentResources.handout.toggle.qrCodes')}
          checked={qrCodes}
          onChange={onToggleQrCodes}
          testId="handout-toggle-qr-codes"
        />
        <ToolbarSwitch
          label={t('parentResources.handout.toggle.coverSheet')}
          checked={coverSheet}
          onChange={onToggleCoverSheet}
          testId="handout-toggle-cover-sheet"
        />
      </div>

      <div className="flex items-center justify-end gap-3 pt-2 border-t border-lsc-border/60 dark:border-earth-700/60">
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
          data-testid="handout-cancel"
        >
          <X className="w-4 h-4" aria-hidden="true" />
          {t('parentResources.handout.action.cancel')}
        </button>
        <button
          type="button"
          onClick={onPreviewPrint}
          disabled={disabled}
          aria-disabled={disabled}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:bg-lsc-rose/40 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 transition-colors"
          data-testid="handout-preview-print"
        >
          <Printer className="w-4 h-4" aria-hidden="true" />
          {t('parentResources.handout.action.previewPrint')}
        </button>
      </div>
    </div>
  )
}

function ToolbarSwitch({
  label,
  checked,
  onChange,
  testId,
}: {
  label: string
  checked: boolean
  onChange: () => void
  testId: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className="group inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 rounded"
      data-testid={testId}
    >
      <span
        className={`relative inline-block h-5 w-9 rounded-full transition-colors ${
          checked
            ? 'bg-lsc-rose'
            : 'bg-lsc-dark/20 dark:bg-lsc-cream/20'
        }`}
        aria-hidden="true"
      >
        <span
          className={`absolute top-0.5 inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
            checked ? 'translate-x-4' : 'translate-x-0.5'
          }`}
        />
      </span>
      {label}
    </button>
  )
}
