/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { MessageCircle, ThumbsUp, ThumbsDown, Clock, ChevronDown, ChevronUp } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import type { AgentConversation } from '../../api/library-agents-api'

export function ConversationsTab({
  conversations,
  isLoading,
  onFilterChange,
  currentFilter,
}: {
  conversations: AgentConversation[]
  isLoading: boolean
  onFilterChange: (f: string) => void
  currentFilter: string
}) {
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const toggleExpand = (id: number) => {
    setExpandedId(prev => prev === id ? null : id)
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-24 bg-lsc-cream dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" aria-hidden="true" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {[
          { value: 'all', label: 'All' },
          { value: 'helpful', label: 'Helpful' },
          { value: 'not_helpful', label: 'Not Helpful' },
          { value: 'no_feedback', label: 'No Feedback' },
        ].map(f => (
          <button
            key={f.value}
            onClick={() => onFilterChange(f.value)}
            className={clsx(
              'px-3 py-1.5 rounded-lg text-sm transition-colors',
              currentFilter === f.value
                ? 'bg-lsc-rose text-white'
                : 'bg-lsc-cream dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/80 dark:hover:bg-earth-700'
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {conversations.length === 0 && (
        <div className="text-center py-10 text-lsc-dark/70 dark:text-lsc-cream/70">
          <MessageCircle className="w-12 h-12 mx-auto mb-3 opacity-40" aria-hidden="true" />
          <p>No conversations found.</p>
        </div>
      )}

      {conversations.map(conv => (
        <div
          key={conv.id}
          className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden"
        >
          <button
            onClick={() => toggleExpand(conv.id)}
            className="w-full p-4 flex items-start gap-3 text-left hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors"
            aria-expanded={expandedId === conv.id}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="text-xs font-medium text-lsc-rose dark:text-lsc-rose-light">
                  Agent #{conv.agent_id}
                </span>
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {new Date(conv.created_at).toLocaleDateString()} {new Date(conv.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                {conv.response_time_ms && (
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
                    <Clock className="w-3 h-3" aria-hidden="true" />
                    {conv.response_time_ms}ms
                  </span>
                )}
                {conv.helpful !== null && (
                  <span className={clsx(
                    'text-xs px-2 py-0.5 rounded-full font-medium flex items-center gap-1',
                    conv.helpful
                      ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300'
                      : 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300'
                  )}>
                    {conv.helpful ? (
                      <><ThumbsUp className="w-3 h-3" aria-hidden="true" /> Helpful</>
                    ) : (
                      <><ThumbsDown className="w-3 h-3" aria-hidden="true" /> Not helpful</>
                    )}
                  </span>
                )}
                {conv.detected_intent && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                    {conv.detected_intent.replace(/_/g, ' ')}
                  </span>
                )}
              </div>
              <p className="text-sm text-lsc-dark dark:text-lsc-cream font-medium truncate" title={`Q: ${conv.user_message}`}>
                Q: {conv.user_message}
              </p>
            </div>
            {expandedId === conv.id ? (
              <ChevronUp className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0 mt-0.5" aria-hidden="true" />
            ) : (
              <ChevronDown className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0 mt-0.5" aria-hidden="true" />
            )}
          </button>
          {expandedId === conv.id && (
            <div className="px-4 pb-4 border-t border-lsc-border dark:border-earth-700 pt-3 space-y-3">
              <div>
                <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1 uppercase tracking-wide">User asked:</p>
                <p className="text-sm text-lsc-dark dark:text-lsc-cream bg-lsc-cream/50 dark:bg-earth-900/50 rounded-lg px-3 py-2">
                  {conv.user_message}
                </p>
              </div>
              <div>
                <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1 uppercase tracking-wide">Agent responded:</p>
                <p className="text-sm text-lsc-dark dark:text-lsc-cream bg-lsc-rose/5 dark:bg-lsc-rose/10 rounded-lg px-3 py-2">
                  {conv.agent_response}
                </p>
              </div>
              {conv.feedback_note && (
                <div>
                  <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1 uppercase tracking-wide">Feedback note:</p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">{conv.feedback_note}</p>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
