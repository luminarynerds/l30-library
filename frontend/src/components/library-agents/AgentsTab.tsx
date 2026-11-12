/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Bot, Edit2, ToggleLeft, ToggleRight, Loader } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation } from '@/i18n'
import type { LibraryAgent } from '../../api/library-agents-api'
import { getAgentIcon } from './agent-zones'

export function AgentsTab({
  agents,
  onEdit,
  onToggle,
  isTogglingId,
  token: _token,
}: {
  agents: LibraryAgent[]
  onEdit: (agent: LibraryAgent) => void
  onToggle: (agent: LibraryAgent) => void
  isTogglingId: number | null
  token: string
}) {
  const { t } = useTranslation()
  return (
    <div className="space-y-3">
      {agents.length === 0 && (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          <Bot className="w-12 h-12 mx-auto mb-3 opacity-40" aria-hidden="true" />
          <p>{t('admin.adminLibraryAgents.noAgentsFoundCreateOne')}</p>
        </div>
      )}
      {agents.map(agent => (
        <div
          key={agent.id}
          className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 flex items-start gap-4"
        >
          {(() => {
            const Icon = getAgentIcon(agent)
            return (
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 bg-lsc-cream dark:bg-lsc-brown text-lsc-rose dark:text-lsc-rose-light"
                aria-hidden="true"
              >
                <Icon className="w-6 h-6" strokeWidth={1.75} />
              </div>
            )
          })()}

          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {agent.name}
              </h3>
              {agent.nickname && (
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">
                  "{agent.nickname}"
                </span>
              )}
              <span className={clsx(
                'text-xs px-2 py-0.5 rounded-full font-medium',
                agent.is_active
                  ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300'
                  : 'bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-300'
              )}>
                {agent.is_active ? 'Active' : 'Disabled'}
              </span>
            </div>
            <p className="text-sm text-lsc-rose dark:text-lsc-rose-light">{agent.role}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 line-clamp-2" title={agent.bio}>{agent.bio}</p>
            <div className="flex flex-wrap gap-1.5 mt-2">
              <span className="text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                {agent.personality}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                {agent.department}
              </span>
              {agent.specialties.slice(0, 2).map(s => (
                <span key={s} className="text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                  {s}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => onEdit(agent)}
              className="p-2 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
              aria-label={`Edit ${agent.name}`}
              title="Edit agent"
            >
              <Edit2 className="w-4 h-4" aria-hidden="true" />
            </button>
            <button
              onClick={() => onToggle(agent)}
              disabled={isTogglingId === agent.id}
              className={clsx(
                'p-2 rounded-lg transition-colors',
                agent.is_active
                  ? 'text-status-success-600 dark:text-status-success-400 hover:bg-status-success-50 dark:bg-status-success-900/20 dark:hover:bg-status-success-900/20'
                  : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700'
              )}
              aria-label={agent.is_active ? `Disable ${agent.name}` : `Enable ${agent.name}`}
              title={agent.is_active ? 'Disable' : 'Enable'}
            >
              {isTogglingId === agent.id ? (
                <Loader className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
              ) : agent.is_active ? (
                <ToggleRight className="w-5 h-5" aria-hidden="true" />
              ) : (
                <ToggleLeft className="w-5 h-5" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
