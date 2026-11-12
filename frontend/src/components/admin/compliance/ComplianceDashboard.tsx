/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  Shield, Monitor, MapPin, Scale, ShieldAlert, FileText, ClipboardCheck,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { fetchApi } from '@/api/fetchApi'
import { getDashboard } from '@/api/unified-compliance-api'
import { ComplianceStatusCard } from './ComplianceStatusCard'
import type { ComplianceStatus } from './ComplianceStatusBadge'

export type SectionId = 'audit' | 'cipa' | 'state' | 'law-enforcement' | 'ban-tracker' | 'public-records' | 'ops-audit'

interface DashboardData {
  openViolations: number
  unresolvedIncidents: number
  overallScore: number
  filteringRate: number
  pendingBypasses: number
  overtimeSessions: number
  overdueReports: number
  nextDeadline: string | null
  openLERequests: number
  pastDueLERequests: number
  activeChallenges: number
  catalogMatches: number
  openPRRequests: number
  overduePRRequests: number
}

const EMPTY: DashboardData = {
  openViolations: 0, unresolvedIncidents: 0, overallScore: 100,
  filteringRate: 100, pendingBypasses: 0, overtimeSessions: 0,
  overdueReports: 0, nextDeadline: null,
  openLERequests: 0, pastDueLERequests: 0,
  activeChallenges: 0, catalogMatches: 0,
  openPRRequests: 0, overduePRRequests: 0,
}

interface ComplianceDashboardProps {
  onSelectSection: (id: SectionId) => void
}

async function fetchJson(path: string) {
  return fetchApi(path)
}

export function ComplianceDashboard({ onSelectSection }: ComplianceDashboardProps) {
  const { token } = useAuth()
  const [data, setData] = useState<DashboardData>(EMPTY)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    const load = async () => {
      const d = { ...EMPTY }
      const results = await Promise.allSettled([
        getDashboard(),
        fetchJson('/cipa/dashboard'),
        fetchJson('/state-compliance/deadlines?days_ahead=90'),
        fetchJson('/law-enforcement/stats'),
        fetchJson('/ban-tracker/reports/stats'),
        fetchJson('/public-records/stats'),
      ])

      if (results[0].status === 'fulfilled') {
        const r = results[0].value
        d.openViolations = r.violations?.total_open ?? 0
        d.unresolvedIncidents = r.incidents?.total_open ?? 0
        d.overallScore = r.compliance_score ?? 100
      }
      if (results[1].status === 'fulfilled') {
        const r = results[1].value
        d.filteringRate = r.filtering_enabled_rate ?? 100
        d.pendingBypasses = r.active_bypasses ?? 0
        d.overtimeSessions = r.overtime_sessions ?? 0
      }
      if (results[2].status === 'fulfilled') {
        const deadlines = results[2].value
        if (Array.isArray(deadlines) && deadlines.length > 0) {
          const overdue = deadlines.filter((dl: { days_until_due: number }) => dl.days_until_due < 0)
          d.overdueReports = overdue.length
          d.nextDeadline = deadlines[0]?.due_date ?? null
        }
      }
      if (results[3].status === 'fulfilled') {
        const r = results[3].value
        d.openLERequests = r.open ?? r.pending ?? 0
        d.pastDueLERequests = r.overdue ?? 0
      }
      if (results[4].status === 'fulfilled') {
        const r = results[4].value
        d.activeChallenges = r.active_challenges ?? r.challenged ?? 0
        d.catalogMatches = r.catalog_matches ?? 0
      }
      if (results[5].status === 'fulfilled') {
        const r = results[5].value
        d.openPRRequests = (r.pending ?? 0) + (r.in_progress ?? 0)
        d.overduePRRequests = r.overdue ?? 0
      }
      setData(d)
      setLoading(false)
    }
    void load()
  }, [token])

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" aria-busy="true" aria-label="Loading compliance dashboard">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="h-52 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" />
        ))}
      </div>
    )
  }

  function auditStatus(): ComplianceStatus {
    if (data.openViolations > 0) return data.overallScore < 70 ? 'action-required' : 'attention'
    return 'compliant'
  }
  function cipaStatus(): ComplianceStatus {
    if (data.filteringRate < 80) return 'action-required'
    if (data.filteringRate < 95 || data.pendingBypasses > 0) return 'attention'
    return 'compliant'
  }
  function stateStatus(): ComplianceStatus {
    if (data.overdueReports > 0) return 'action-required'
    if (data.nextDeadline) return 'attention'
    return 'compliant'
  }
  function leStatus(): ComplianceStatus {
    if (data.pastDueLERequests > 0) return 'action-required'
    if (data.openLERequests > 0) return 'attention'
    return 'compliant'
  }
  function banStatus(): ComplianceStatus {
    if (data.activeChallenges > 0) return 'attention'
    return 'compliant'
  }
  function prStatus(): ComplianceStatus {
    if (data.overduePRRequests > 0) return 'action-required'
    if (data.openPRRequests > 0) return 'attention'
    return 'compliant'
  }

  const cards: {
    id: SectionId
    icon: React.ReactNode
    title: string
    description: string
    status: ComplianceStatus
    actionItems: { label: string; urgent?: boolean | undefined }[]
  }[] = [
    {
      id: 'audit',
      icon: <Shield className="w-5 h-5 text-lsc-rose" />,
      title: 'Compliance Overview',
      description: 'Cross-regulation compliance overview. Shows where your library stands across all requirements.',
      status: auditStatus(),
      actionItems: [
        ...(data.openViolations > 0 ? [{ label: `${data.openViolations} open violation${data.openViolations !== 1 ? 's' : ''}`, urgent: true }] : []),
        ...(data.unresolvedIncidents > 0 ? [{ label: `${data.unresolvedIncidents} unresolved incident${data.unresolvedIncidents !== 1 ? 's' : ''}` }] : []),
      ],
    },
    {
      id: 'cipa',
      icon: <Monitor className="w-5 h-5 text-lsc-rose" />,
      title: 'Internet Filtering (CIPA)',
      description: "Internet filtering for children's safety. Required for E-Rate funding.",
      status: cipaStatus(),
      actionItems: [
        ...(data.pendingBypasses > 0 ? [{ label: `${data.pendingBypasses} bypass request${data.pendingBypasses !== 1 ? 's' : ''} pending` }] : []),
        ...(data.overtimeSessions > 0 ? [{ label: `${data.overtimeSessions} overtime session${data.overtimeSessions !== 1 ? 's' : ''}` }] : []),
      ],
    },
    {
      id: 'state',
      icon: <MapPin className="w-5 h-5 text-lsc-rose" />,
      title: 'State Reporting',
      description: 'State library reporting requirements. Tracks deadlines and submissions so nothing slips through.',
      status: stateStatus(),
      actionItems: [
        ...(data.overdueReports > 0 ? [{ label: `${data.overdueReports} report${data.overdueReports !== 1 ? 's' : ''} overdue`, urgent: true }] : []),
        ...(data.nextDeadline ? [{ label: `Next deadline: ${data.nextDeadline}` }] : []),
      ],
    },
    {
      id: 'law-enforcement',
      icon: <Scale className="w-5 h-5 text-lsc-rose" />,
      title: 'Law Enforcement Requests',
      description: 'Track and respond to law enforcement requests for patron records. Every request is logged.',
      status: leStatus(),
      actionItems: [
        ...(data.pastDueLERequests > 0 ? [{ label: `${data.pastDueLERequests} past response deadline`, urgent: true }] : []),
        ...(data.openLERequests > 0 ? [{ label: `${data.openLERequests} open request${data.openLERequests !== 1 ? 's' : ''}` }] : []),
      ],
    },
    {
      id: 'ban-tracker',
      icon: <ShieldAlert className="w-5 h-5 text-lsc-rose" />,
      title: 'Book Challenge Tracker',
      description: "Track book challenges, bans, and your library's response. Public transparency page included.",
      status: banStatus(),
      actionItems: [
        ...(data.activeChallenges > 0 ? [{ label: `${data.activeChallenges} active challenge${data.activeChallenges !== 1 ? 's' : ''}` }] : []),
        ...(data.catalogMatches > 0 ? [{ label: `${data.catalogMatches} catalog match${data.catalogMatches !== 1 ? 'es' : ''}` }] : []),
      ],
    },
    {
      id: 'public-records',
      icon: <FileText className="w-5 h-5 text-lsc-rose" />,
      title: 'Public Records Requests',
      description: 'Manage public records requests. Track deadlines and maintain response documentation.',
      status: prStatus(),
      actionItems: [
        ...(data.overduePRRequests > 0 ? [{ label: `${data.overduePRRequests} past due date`, urgent: true }] : []),
        ...(data.openPRRequests > 0 ? [{ label: `${data.openPRRequests} open request${data.openPRRequests !== 1 ? 's' : ''}` }] : []),
      ],
    },
    {
      id: 'ops-audit',
      icon: <ClipboardCheck className="w-5 h-5 text-lsc-rose" />,
      title: 'Operations Audit',
      description: 'Who did what and when. Searchable activity trail for board questions and internal review.',
      status: 'info' as ComplianceStatus,
      actionItems: [],
    },
  ]

  return (
    <nav aria-label="Compliance sections">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {cards.map((card) => (
          <ComplianceStatusCard
            key={card.id}
            id={card.id}
            icon={card.icon}
            title={card.title}
            description={card.description}
            status={card.status}
            actionItems={card.actionItems}
            onClick={onSelectSection as (id: string) => void}
          />
        ))}
      </div>
    </nav>
  )
}
