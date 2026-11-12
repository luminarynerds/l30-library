/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  RefreshCcw, DollarSign, Users, UserCog, Gauge,
} from 'lucide-react'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { DashboardCard } from '../shared/DashboardCard'
import { DashboardGrid } from '../shared/DashboardGrid'

export type SectionId = 'circulation-rules' | 'financial' | 'patron-settings' | 'staff-settings' | 'system-limits'

interface DashboardData {
  materialTypesConfigured: number
  specialRulesActive: number
  dailyFineRate: number
  maxFine: number
  gracePeriodDays: number
  patronTypesCount: number
  selfRegistration: boolean
  cardExpiryYears: number
  rolesCount: number
  departmentsCount: number
  require2fa: boolean
  coppaThreshold: number
  ageTransition: number
  cardGracePeriod: number
}

const EMPTY: DashboardData = {
  materialTypesConfigured: 0,
  specialRulesActive: 0,
  dailyFineRate: 0,
  maxFine: 0,
  gracePeriodDays: 0,
  patronTypesCount: 0,
  selfRegistration: false,
  cardExpiryYears: 0,
  rolesCount: 0,
  departmentsCount: 0,
  require2fa: false,
  coppaThreshold: 13,
  ageTransition: 18,
  cardGracePeriod: 30,
}

interface CirculationPolicyDashboardProps {
  onSelectSection: (id: string) => void
}

export function CirculationPolicyDashboard({ onSelectSection }: CirculationPolicyDashboardProps) {
  const { features, loading: featuresLoading } = useOrganizationFeatures()
  const [data, setData] = useState<DashboardData>(EMPTY)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (featuresLoading) return

    const d = { ...EMPTY }

    if (features?.configuration) {
      const config = features.configuration as Record<string, unknown>

      const circRules = config.circulation_rules as Record<string, unknown> | undefined
      if (circRules) {
        const matTypes = circRules.material_types
        d.materialTypesConfigured = Array.isArray(matTypes) ? matTypes.length : 0
        const specRules = circRules.special_rules
        d.specialRulesActive = Array.isArray(specRules)
          ? specRules.filter((r: { active?: boolean }) => r.active).length
          : 0
      }

      const financial = config.financial as Record<string, unknown> | undefined
      if (financial) {
        d.dailyFineRate = (financial.daily_fine_rate as number) ?? 0
        d.maxFine = (financial.max_fine_per_user as number) ?? 0
        d.gracePeriodDays = (financial.grace_period_days as number) ?? 0
      }

      const patron = config.patron_settings as Record<string, unknown> | undefined
      if (patron) {
        d.selfRegistration = (patron.allow_self_registration as boolean) ?? false
        d.cardExpiryYears = (patron.card_expiry_years as number) ?? 0
        const policies = patron.patron_type_policies
        d.patronTypesCount = policies ? Object.keys(policies as Record<string, unknown>).length : 0
      }
    }

    if (features) {
      const f = features as unknown as Record<string, unknown>
      d.coppaThreshold = (f.coppa_age_threshold as number) ?? 13
      d.ageTransition = (f.age_transition_threshold as number) ?? 18
      d.cardGracePeriod = (f.card_expiration_grace_period_days as number) ?? 30
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
      id: 'circulation-rules',
      icon: <RefreshCcw className="w-5 h-5 text-lsc-rose" />,
      title: 'Circulation Rules',
      description: 'How long patrons can borrow each type of material, and how many times they can renew.',
      statusItems: [
        { label: 'Material types', value: data.materialTypesConfigured },
        { label: 'Special rules', value: data.specialRulesActive },
      ],
    },
    {
      id: 'financial',
      icon: <DollarSign className="w-5 h-5 text-lsc-rose" />,
      title: 'Fine Policies',
      description: 'Fines for overdue items, damage charges, lost item fees, and patron claim limits.',
      statusItems: [
        { label: 'Daily fine', value: `$${data.dailyFineRate.toFixed(2)}` },
        { label: 'Max fine', value: `$${data.maxFine.toFixed(2)}` },
        { label: 'Grace period', value: `${data.gracePeriodDays}d` },
      ],
    },
    {
      id: 'patron-settings',
      icon: <Users className="w-5 h-5 text-lsc-rose" />,
      title: 'Patron Types & Policies',
      description: 'Registration rules, library card policies, privacy settings, and communication defaults.',
      statusItems: [
        { label: 'Patron types', value: data.patronTypesCount },
        { label: 'Self-registration', value: data.selfRegistration ? 'On' : 'Off' },
        { label: 'Card expiry', value: `${data.cardExpiryYears}yr` },
      ],
    },
    {
      id: 'staff-settings',
      icon: <UserCog className="w-5 h-5 text-lsc-rose" />,
      title: 'Staff Roles & Policies',
      description: 'Staff roles, permissions, departments, security policies, scheduling, and training.',
      statusItems: [
        { label: 'Roles', value: data.rolesCount },
        { label: 'Departments', value: data.departmentsCount },
        { label: '2FA', value: data.require2fa ? 'Required' : 'Off' },
      ],
    },
    {
      id: 'system-limits',
      icon: <Gauge className="w-5 h-5 text-lsc-rose" />,
      title: 'System Limits',
      description: 'Age thresholds, quiz scores, card expiration grace periods, and inactive account cleanup.',
      statusItems: [
        { label: 'COPPA', value: `${data.coppaThreshold}yr` },
        { label: 'Age transition', value: `${data.ageTransition}yr` },
        { label: 'Card grace', value: `${data.cardGracePeriod}d` },
      ],
    },
  ]

  return (
    <DashboardGrid label="Circulation and policy sections" loading={loading} skeletonCount={6}>
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
