/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { Settings, ToggleLeft, Globe, BookOpen } from 'lucide-react'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { DashboardCard } from '../shared/DashboardCard'
import { DashboardGrid } from '../shared/DashboardGrid'

export type SectionId = 'site-settings' | 'features' | 'community-resources' | 'circulation-policies'

interface DashboardData {
  librarySystemName: string
  defaultLoanPeriod: number
  checkoutLimit: number
  featuresEnabled: number
  featuresTotal: number
  resourceCount: number
  categoryCount: number
}

const EMPTY: DashboardData = {
  librarySystemName: '',
  defaultLoanPeriod: 0,
  checkoutLimit: 0,
  featuresEnabled: 0,
  featuresTotal: 0,
  resourceCount: 0,
  categoryCount: 0,
}

const FEATURE_TOGGLE_KEYS = [
  'gamification_enabled', 'reading_programs_enabled', 'board_features_enabled',
  'training_modules_enabled', 'community_features_enabled', 'email_notifications_enabled',
  'banned_books_tracking_enabled',
  'patron_portal_enabled', 'self_checkout_enabled', 'circulation_print_slip_enabled',
  'customer_display_enabled',
] as const

interface LibraryConfigDashboardProps {
  onSelectSection: (id: string) => void
}

export function LibraryConfigDashboard({ onSelectSection }: LibraryConfigDashboardProps) {
  const { features, loading: featuresLoading } = useOrganizationFeatures()
  const [data, setData] = useState<DashboardData>(EMPTY)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (featuresLoading) return

    const d = { ...EMPTY }

    if (features) {
      const f = features as unknown as Record<string, unknown>

      // Count enabled feature toggles
      d.featuresTotal = FEATURE_TOGGLE_KEYS.length
      d.featuresEnabled = FEATURE_TOGGLE_KEYS.filter((k) => f[k] === true).length

      // Checkout limits from org features
      d.checkoutLimit = (f.max_checkouts_per_patron as number) ?? 0
      d.defaultLoanPeriod = (f.default_daily_goal_minutes as number) ?? 0
    }

    setData(d)
    setLoading(false)
  }, [features, featuresLoading])

  const cards: {
    id: SectionId
    icon: React.ReactNode
    title: string
    description: string
    statusItems: { label: string; value: string | number }[]
  }[] = [
    {
      id: 'site-settings',
      icon: <Settings className="w-5 h-5 text-lsc-rose" />,
      title: 'Site Settings',
      description: 'General library configuration -- circulation defaults, fine defaults, hold policies, transit rules, and feature flags.',
      statusItems: [],
    },
    {
      id: 'features',
      icon: <ToggleLeft className="w-5 h-5 text-lsc-rose" />,
      title: 'Organization Features',
      description: 'Turn library features on or off. Gamification, reading programs, board tools, training, community features, and self-checkout.',
      statusItems: [
        { label: 'Features enabled', value: `${data.featuresEnabled} of ${data.featuresTotal}` },
      ],
    },
    {
      id: 'community-resources',
      icon: <Globe className="w-5 h-5 text-lsc-rose" />,
      title: 'Community Resources',
      description: 'Links to local organizations, services, and agencies shown on public pages. Curated by staff or discovered by AI.',
      statusItems: [],
    },
    {
      id: 'circulation-policies',
      icon: <BookOpen className="w-5 h-5 text-lsc-rose" />,
      title: 'Circulation Policy Matrix',
      description: 'Per-format, per-audience, per-binding, and per-collection overrides on top of Site Settings defaults. Defines who can keep what, for how long, with what fines.',
      statusItems: [],
    },
  ]

  return (
    <DashboardGrid label="Library configuration sections" loading={loading} skeletonCount={3}>
      {cards.map((card) => (
        <DashboardCard
          key={card.id}
          id={card.id}
          icon={card.icon}
          title={card.title}
          description={card.description}
          statusItems={card.statusItems}
          onClick={onSelectSection}
        />
      ))}
    </DashboardGrid>
  )
}
