/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Sparkles } from 'lucide-react'
import { useTranslation } from '@/i18n'
import AIToolCard from '../components/AIToolCard'
import type { AITool } from '../data/ai-tools-data'

interface AllToolsSectionProps {
  tools: AITool[]
  expanded: Set<string>
  onToggle: (name: string) => void
}

export default function AllToolsSection({ tools, expanded, onToggle }: AllToolsSectionProps): React.ReactElement {
  const { t } = useTranslation()
  return (
    <section id="tools" className="scroll-mt-24">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('aITools.allAiTools', 'All AI Tools')}
        </h2>
      </div>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        {t('aITools.allAiToolsLead', 'Click any tool to learn more about what it does and how it works.')}
      </p>
      <div className="space-y-3">
        {tools.map(tool => (
          <AIToolCard
            key={tool.name}
            tool={tool}
            expanded={expanded.has(tool.name)}
            onToggle={() => onToggle(tool.name)}
          />
        ))}
      </div>
    </section>
  )
}
