/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { useTranslation } from '@/i18n/I18nContext'

type Band = { key: string; min: number; max: number }

interface Props { bands?: Band[]; basePath?: string }

const KID_BANDS: Band[] = [
  { key: 'just_starting', min: -400, max: 100 },
  { key: 'early_reader', min: 100, max: 400 },
  { key: 'confident_reader', min: 400, max: 700 },
  { key: 'strong_reader', min: 700, max: 1000 },
  { key: 'advanced', min: 1000, max: 2000 },
]

export function LexilePresetStrip({ bands = KID_BANDS, basePath = '/catalog' }: Props): JSX.Element {
  const { t } = useTranslation()
  return (
    <section aria-labelledby="lexile-preset-heading" className="my-4">
      <h2 id="lexile-preset-heading" className="text-lg font-semibold mb-2">{t('lexile_preset_title')}</h2>
      <div className="flex flex-wrap gap-2">
        {bands.map(b => {
          const label = t(`lexile_preset_${b.key}`)
          return (
            <Link
              key={b.key}
              to={`${basePath}?min_lexile=${b.min}&max_lexile=${b.max}`}
              aria-label={t('lexile_preset_aria', { label, min: b.min, max: b.max })}
              className="rounded-full bg-category-100 dark:bg-category-800 px-3 py-1 text-sm hover:bg-category-200 text-category-900 dark:text-category-100"
            >
              {label}
            </Link>
          )
        })}
      </div>
    </section>
  )
}

export const TEEN_BANDS: Band[] = [
  { key: 'early_reader', min: 400, max: 700 },
  { key: 'confident_reader', min: 600, max: 900 },
  { key: 'strong_reader', min: 800, max: 1100 },
  { key: 'advanced', min: 1000, max: 2000 },
]
