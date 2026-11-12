/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { Building2, Check, ChevronDown, Clock, ExternalLink, Users } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import type { AITool } from '../data/ai-tools-data'
import { EASE_OUT_EXPO, MAGNETIC_HOVER } from '../motion'

/*
 * WCAG 2.2 AA contrast + 1.4.1 non-color-cue redundancy for status pills.
 * `text-lsc-rose` routes through the lifted --accent-rose-text-rgb var
 * (light mode #7A4040), which measures 6.82:1 on lsc-cream. The old
 * hand-darkened #6B4242 predates that var split and is no longer needed.
 * "Available now" uses success-800 for a comfortable margin. Each status
 * also gets an icon so the cue is not color-only.
 */
function StatusBadge({ status }: { status: AITool['status'] }): React.ReactElement {
  const styles = {
    'available': 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
    'in-library': 'bg-lsc-cream text-lsc-rose dark:bg-lsc-dark/30 dark:text-lsc-rose-light',
    'coming-soon': 'bg-lsc-cream text-lsc-rose dark:bg-lsc-dark/30 dark:text-lsc-rose-light',
  }
  const labels = {
    'available': 'Available now',
    'in-library': 'In-library only',
    'coming-soon': 'Coming soon',
  }
  const Icon = {
    'available': Check,
    'in-library': Building2,
    'coming-soon': Clock,
  }[status]
  return (
    <span className={clsx('inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium', styles[status])}>
      <Icon aria-hidden="true" className="w-3.5 h-3.5" />
      {labels[status]}
    </span>
  )
}

interface AIToolCardProps {
  tool: AITool
  expanded: boolean
  onToggle: () => void
}

export default function AIToolCard({ tool, expanded, onToggle }: AIToolCardProps): React.ReactElement {
  const slug = tool.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  const panelId = `ai-tool-panel-${slug}`
  const buttonId = `ai-tool-button-${slug}`

  return (
    <div className={clsx('bg-lsc-white dark:bg-earth-800 rounded-xl shadow-soft-sm', MAGNETIC_HOVER)}>
      <button
        id={buttonId}
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={panelId}
        className="w-full p-5 flex items-start gap-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded-xl"
      >
        <div className="w-12 h-12 rounded-xl bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center flex-shrink-0">
          <tool.icon aria-hidden="true" className={clsx('w-6 h-6', tool.iconColor || 'text-lsc-rose')} />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {tool.name}
          </h2>
          <p className="text-sm text-lsc-rose dark:text-lsc-rose-light italic mt-0.5">
            {tool.tagline}
          </p>
          {tool.summary && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {tool.summary}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <StatusBadge status={tool.status} />
          <ChevronDown
            aria-hidden="true"
            className={clsx(
              'w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 motion-safe:transition-transform motion-safe:duration-300',
              EASE_OUT_EXPO,
              expanded && 'rotate-180',
            )}
          />
        </div>
      </button>

      <div
        id={panelId}
        role="region"
        aria-labelledby={buttonId}
        hidden={!expanded}
        className="px-5 pb-5"
      >
        <div className="pl-16 border-t border-lsc-border dark:border-earth-700 pt-4">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{tool.description}</p>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 mt-3">
            {tool.link && (
              <Link
                to={tool.link}
                className={clsx(
                  'inline-flex items-center gap-2 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded',
                )}
              >
                Explore
                <ExternalLink aria-hidden="true" className="w-4 h-4" />
              </Link>
            )}
            <Link
              to="/contact"
              className="inline-flex items-center gap-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
            >
              <Users aria-hidden="true" className="w-4 h-4" />
              Talk to a librarian instead
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
