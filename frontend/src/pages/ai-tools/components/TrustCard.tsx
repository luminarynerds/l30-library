/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { clsx } from '@/utils/helpers'
import { MAGNETIC_HOVER } from '../motion'

interface TrustCardProps {
  icon: React.ElementType
  title: string
  body: string
  className?: string
}

export default function TrustCard({
  icon: Icon,
  title,
  body,
  className,
}: TrustCardProps): React.ReactElement {
  return (
    <div
      className={clsx(
        'bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5',
        MAGNETIC_HOVER,
        className,
      )}
    >
      <div className="w-12 h-12 rounded-xl bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center mb-4">
        <Icon aria-hidden="true" className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
      </div>
      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
        {title}
      </h3>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{body}</p>
    </div>
  )
}
