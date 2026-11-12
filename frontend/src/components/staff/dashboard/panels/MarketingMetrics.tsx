/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTone } from '@/contexts/ToneContext'
import type { Last30Days } from '@/api/staff-api/marketing-dashboard'

interface Props {
  data: Last30Days
}

export default function MarketingMetrics({ data }: Props) {
  const { showCountBadges } = useTone()

  const stats = [
    {
      label: 'Newsletter opens',
      value: `${data.newsletter_open_rate}%`,
      sub: 'Last 30 days',
    },
    {
      label: 'Posts published',
      value: data.posts_published,
      sub: 'Last 30 days',
    },
    {
      label: 'Most shared',
      value: '--',
      sub: 'Coming soon',
    },
    {
      label: 'Subscribers',
      value: showCountBadges
        ? data.subscriber_count.toLocaleString()
        : data.subscriber_count > 0 ? data.subscriber_count.toLocaleString() : '--',
      sub: 'Active',
    },
  ]

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Last 30 days</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {stats.map(s => (
          <div key={s.label} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70 mb-1">{s.label}</p>
            <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">{s.value}</p>
            <p className="text-[11px] mt-1 text-lsc-dark/50 dark:text-lsc-cream/50">{s.sub}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
