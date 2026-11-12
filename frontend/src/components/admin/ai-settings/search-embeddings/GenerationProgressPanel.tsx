/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { TrendingUp } from 'lucide-react'

import { AccordionSection, EntityProgressCard } from '../../semantic-search/SemanticSearchPrimitives'
import { ENTITY_TYPES } from '../../semantic-search/semantic-search-admin-data'

interface Props {
  expanded: boolean
  onToggle: () => void
}

export function GenerationProgressPanel({ expanded, onToggle }: Props) {
  return (
    <AccordionSection
      id="progress"
      title="Generation Progress"
      icon={<TrendingUp className="h-5 w-5 text-category-500" />}
      expanded={expanded}
      onToggle={onToggle}
    >
      <div className="space-y-3">
        <p className="text-sm text-earth-600 dark:text-earth-300">
          Real-time progress for each embedding entity type. Auto-refreshes every 30 seconds (every 3 seconds when running).
        </p>
        {ENTITY_TYPES.map((et) => (
          <EntityProgressCard key={et.id} entityType={et} />
        ))}
      </div>
    </AccordionSection>
  )
}
