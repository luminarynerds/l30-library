/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { clsx } from '@/utils/helpers'
import { MAGNETIC_HOVER } from '../motion'

interface MetricCardProps {
  value: string
  label: string
  detail: string
  className?: string
}

export default function MetricCard({
  value,
  label,
  detail,
  className,
}: MetricCardProps): React.ReactElement {
  return (
    <div
      className={clsx(
        'bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6 text-center',
        MAGNETIC_HOVER,
        className,
      )}
    >
      <p className="text-3xl md:text-4xl font-serif font-bold text-lsc-rose dark:text-lsc-rose-light mb-2">
        {value}
      </p>
      <p className="font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{label}</p>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{detail}</p>
    </div>
  )
}
