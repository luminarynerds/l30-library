/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n/I18nContext'

interface Props { measure: string | null | undefined; compact?: boolean }

export function LexileBadge({ measure, compact = false }: Props): JSX.Element | null {
  const { t } = useTranslation()
  if (!measure) return null
  const label = compact ? measure : t('lexile_badge_prefix', { measure })
  return (
    <span
      className="inline-flex items-center rounded-full bg-category-50 dark:bg-category-900/20 px-2 py-0.5 text-xs font-medium text-category-600 dark:text-category-400 border border-category-200 dark:border-category-800/30"
      title={t('lexile_badge_tooltip')}
      aria-label={t('lexile_badge_label') + ': ' + measure}
    >
      {label}
    </span>
  )
}
