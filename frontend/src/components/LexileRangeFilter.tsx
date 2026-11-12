/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n/I18nContext'

interface Props {
  min: number | null
  max: number | null
  onChange: (next: { min: number | null; max: number | null }) => void
}

/**
 * Reading-level preset bands.
 *
 * Contiguous (shared endpoints) Lexile bands matching commonly published
 * Common Sense Media / Scholastic guided-reading ranges. Cutoffs are a v1
 * starting point; revisit if real-world circulation data shows drift.
 */
export const READING_LEVEL_BANDS: ReadonlyArray<{
  key: string
  min: number
  max: number
}> = [
  { key: 'catalog.readingLevel.earlyReader', min: 0, max: 500 },
  { key: 'catalog.readingLevel.middleGrade', min: 500, max: 850 },
  { key: 'catalog.readingLevel.teen', min: 850, max: 1100 },
  { key: 'catalog.readingLevel.adult', min: 1100, max: 1500 },
]

function bandKeyForRange(min: number | null, max: number | null): string | null {
  if (min == null || max == null) return null
  const hit = READING_LEVEL_BANDS.find((b) => b.min === min && b.max === max)
  return hit ? hit.key : null
}

const BAND_FALLBACKS: Record<string, string> = {
  'catalog.readingLevel.earlyReader': 'Early reader',
  'catalog.readingLevel.middleGrade': 'Middle grade',
  'catalog.readingLevel.teen': 'Teen',
  'catalog.readingLevel.adult': 'Adult',
}

export function LexileRangeFilter({ min, max, onChange }: Props): JSX.Element {
  const { t } = useTranslation()
  const selectedKey = bandKeyForRange(min, max)

  const handle = (key: 'min' | 'max') => (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value === '' ? null : Math.max(-400, Math.min(2000, parseInt(e.target.value, 10)))
    onChange({ min: key === 'min' ? v : min, max: key === 'max' ? v : max })
  }

  const onChipClick = (band: typeof READING_LEVEL_BANDS[number]) => () => {
    if (selectedKey === band.key) {
      onChange({ min: null, max: null })
    } else {
      onChange({ min: band.min, max: band.max })
    }
  }

  return (
    <details className="group">
      <summary
        className="flex items-center justify-between cursor-pointer list-none font-serif text-[12px] font-bold uppercase tracking-[0.06em] pb-2 mb-[6px] border-b border-lsc-border dark:border-earth-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm text-lsc-dark/70 dark:text-lsc-cream/60"
      >
        <span>{t('lexile_filter_title')}</span>
      </summary>
      <div
        role="group"
        aria-label={t('catalog.readingLevel.groupLabel', 'Reading level presets')}
        className="flex flex-wrap gap-2 mt-2"
      >
        {READING_LEVEL_BANDS.map((band) => {
          const pressed = selectedKey === band.key
          const label = t(band.key, BAND_FALLBACKS[band.key])
          const ariaSuffix = t('catalog.readingLevel.ariaSuffix', 'Lexile {{min}} to {{max}}')
            .replace('{{min}}', String(band.min))
            .replace('{{max}}', String(band.max))
          return (
            <button
              key={band.key}
              type="button"
              aria-pressed={pressed}
              aria-label={`${label}, ${ariaSuffix}`}
              onClick={onChipClick(band)}
              className={[
                'min-h-[44px] px-3 py-2 text-sm rounded-full border-2 transition-colors',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose',
                pressed
                  ? 'bg-lsc-rose/15 border-lsc-rose text-lsc-dark dark:text-lsc-cream font-semibold'
                  : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:border-lsc-rose/60',
              ].join(' ')}
            >
              {label}
            </button>
          )
        })}
      </div>
      <div className="flex gap-2 mt-3">
        <label className="flex-1 text-sm text-lsc-dark dark:text-lsc-cream">
          <span>{t('lexile_filter_min')}</span>
          <input
            type="number"
            inputMode="numeric"
            min={-400}
            max={2000}
            step={50}
            value={min ?? ''}
            onChange={handle('min')}
            aria-label={t('lexile_filter_aria_min')}
            className="w-full mt-1 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/40"
          />
        </label>
        <label className="flex-1 text-sm text-lsc-dark dark:text-lsc-cream">
          <span>{t('lexile_filter_max')}</span>
          <input
            type="number"
            inputMode="numeric"
            min={-400}
            max={2000}
            step={50}
            value={max ?? ''}
            onChange={handle('max')}
            aria-label={t('lexile_filter_aria_max')}
            className="w-full mt-1 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/40"
          />
        </label>
        <button
          type="button"
          onClick={() => onChange({ min: null, max: null })}
          className="self-end text-sm text-lsc-rose underline pb-2"
        >
          {t('lexile_filter_clear')}
        </button>
      </div>
    </details>
  )
}
