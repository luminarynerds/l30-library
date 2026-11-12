/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  Users, Loader,
  Globe, Shield,
} from 'lucide-react'
import {
  collaboratorsApi,
  type ResearchProject,
  type ProjectCollaborator,
} from '@/api/genealogy-research-api'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'

export default function ProjectSettingsTab({ project, onUpdate: _onUpdate }: {
  project: ResearchProject
  onUpdate: (project: ResearchProject) => void
}) {
  const { t } = useTranslation()
  const [collaborators, setCollaborators] = useState<ProjectCollaborator[]>([])
  const [loading, setLoading] = useState(true)

  async function loadCollaborators() {
    try {
      setLoading(true)
      const data = await collaboratorsApi.list(project.id)
      setCollaborators(data)
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToLoadCollaborators'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    loadCollaborators()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id])

  const roleColors: Record<string, string> = {
    owner: 'bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-300',
    admin: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300',
    editor: 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light',
    viewer: 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70',
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Project Settings</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Project Name</label>
            <p className="text-lsc-dark dark:text-lsc-cream">{project.name}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Visibility</label>
            <p className="text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              {project.is_public ? <Globe className="w-4 h-4 text-status-success-500" /> : <Shield className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />}
              {project.is_public ? 'Public' : 'Private'}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">License</label>
            <p className="text-lsc-dark dark:text-lsc-cream">{project.default_license}</p>
          </div>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Users className="w-4 h-4" />
          Collaborators
        </h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Team members with access to this research project. Permission levels: Owner (full control),
          Admin (manage members), Editor (add/edit data), Viewer (read-only).
        </p>
        {loading ? (
          <Loader className="w-5 h-5 motion-safe:animate-spin" />
        ) : (
          <div className="space-y-2">
            {collaborators.map(c => (
              <div key={c.id} className="flex items-center justify-between p-3 rounded-lg bg-earth-50 dark:bg-earth-700/50">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-status-warning-100 dark:bg-status-warning-900/30 flex items-center justify-center text-sm font-medium text-status-warning-700 dark:text-status-warning-300">
                    U
                  </div>
                  <span className="text-sm text-lsc-dark dark:text-lsc-cream">User #{c.user_id}</span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${roleColors[c.role] || roleColors.viewer}`}>
                  {c.role}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
