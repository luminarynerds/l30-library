/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  FileText, Users, Link2,
  Lightbulb, MessageSquare, Loader,
  Shield,
} from 'lucide-react'
import {
  researchProjectsApi,
  type ProjectDashboard,
} from '@/api/genealogy-research-api'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'

function StatCard({ icon, label, value, color }: {
  icon: React.ReactNode
  label: string
  value: number
  color: string
}) {
  const colorClasses: Record<string, string> = {
    accent: 'bg-earth-50 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light',
    success: 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-600 dark:text-status-success-400',
    warning: 'bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-600 dark:text-status-warning-400',
    category: 'bg-category-50 dark:bg-category-900/20 text-category-600 dark:text-category-400',
  }
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
      <div className={`inline-flex p-2 rounded-lg mb-2 ${colorClasses[color]}`}>
        {icon}
      </div>
      <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
    </div>
  )
}

export default function ProjectDashboardTab({ projectId }: { projectId: number }) {
  const { t } = useTranslation();
  const [dashboard, setDashboard] = useState<ProjectDashboard | null>(null)
  const [loading, setLoading] = useState(true)

  async function loadDashboard() {
    try {
      setLoading(true)
      const data = await researchProjectsApi.getDashboard(projectId)
      setDashboard(data)
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToLoadDashboard'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    loadDashboard()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  if (loading || !dashboard) {
    return <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin" /></div>
  }

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<Users className="w-5 h-5" />} label="People" value={dashboard.project.person_count} color="accent" />
        <StatCard icon={<FileText className="w-5 h-5" />} label="Documents" value={dashboard.project.document_count} color="success" />
        <StatCard icon={<Link2 className="w-5 h-5" />} label="Pending Links" value={dashboard.pending_record_links} color="warning" />
        <StatCard icon={<MessageSquare className="w-5 h-5" />} label="Open Notes" value={dashboard.unresolved_notes} color="category" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Persons */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-earth-600" />
            Recent People
          </h3>
          {dashboard.recent_persons.length === 0 ? (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyResearchPageContent.noPeopleAddedYetStart')}</p>
          ) : (
            <div className="space-y-2">
              {dashboard.recent_persons.map(person => (
                <div key={person.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700">
                  <div className="w-8 h-8 rounded-full bg-earth-100 dark:bg-earth-800/30 flex items-center justify-center text-sm font-medium text-lsc-rose dark:text-lsc-rose-light">
                    {person.given_names[0]}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {person.given_names} {person.surname || ''}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {person.birth_date || 'Unknown'} - {person.is_living ? 'Living' : (person.death_date || 'Unknown')}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Research Guidance */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-status-warning-500" />
            Research Suggestions
          </h3>
          {dashboard.active_guidance.length === 0 ? (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyResearchPageContent.noActiveSuggestionsAddMore')}</p>
          ) : (
            <div className="space-y-3">
              {dashboard.active_guidance.map(suggestion => (
                <div key={suggestion.id} className="p-3 rounded-lg bg-status-warning-50 dark:bg-status-warning-900/10 border border-status-warning-200 dark:border-status-warning-800">
                  <div className="flex items-start gap-2">
                    <Lightbulb className="w-4 h-4 text-status-warning-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{suggestion.title}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{suggestion.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Collaborators */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
          <Shield className="w-4 h-4 text-status-success-500" />
          Team ({dashboard.collaborator_count} member{dashboard.collaborator_count !== 1 ? 's' : ''})
        </h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Invite collaborators from the Settings tab to research together.
        </p>
      </div>
    </div>
  )
}
