/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ArrowLeft, Cpu } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useTranslation } from '@/i18n'
import TableOfContents, { type TocEntry } from './ai-tools/components/TableOfContents'
import SensoryQuietEntry from './ai-tools/sections/SensoryQuietEntry'
import BoardPolicyQuote from './ai-tools/sections/BoardPolicyQuote'
import DataFlowMatrix from './ai-tools/sections/DataFlowMatrix'
import WhySmallLibrarySection from './ai-tools/sections/WhySmallLibrarySection'
import MetricsSection from './ai-tools/sections/MetricsSection'
import TestimonialsSection from './ai-tools/sections/TestimonialsSection'
import RubricSection from './ai-tools/sections/RubricSection'
import StaffImpactSection from './ai-tools/sections/StaffImpactSection'
import SafetyTransparencySection from './ai-tools/sections/SafetyTransparencySection'
import HardwareSection from './ai-tools/sections/HardwareSection'
import SystemPromptsSection from './ai-tools/sections/SystemPromptsSection'
import LocalKnowledgeSection from './ai-tools/sections/LocalKnowledgeSection'
import WrongnessLogSection from './ai-tools/sections/WrongnessLogSection'
import LegalNoteSection from './ai-tools/sections/LegalNoteSection'

export default function AIToolsHowItWorksPage(): React.ReactElement {
  const { t } = useTranslation()

  // Only sections that render their own scroll target (`id="..."`) belong in the TOC.
  const tocEntries: TocEntry[] = [
    { id: 'why', label: t('aITools.tocWhy', 'Why we did it') },
    { id: 'metrics', label: t('aITools.tocMetrics', 'Impact metrics') },
    { id: 'data-flow', label: t('aITools.tocDataFlow', 'Per-tool data flow') },
    { id: 'rubric', label: t('aITools.tocRubric', 'Eight-criteria rubric') },
    { id: 'safety', label: t('aITools.tocSafety', 'Safety & transparency') },
    { id: 'hardware', label: t('aITools.tocHardware', 'The hardware') },
    { id: 'system-prompts', label: t('aITools.tocSystemPrompts', 'How we steer it') },
    { id: 'wrongness', label: t('aITools.tocWrongness', 'When we were wrong') },
  ]

  return (
    <StandardPageLayout
      title={t('aITools.howItWorksTitle', 'How AI works at L30')}
      subtitle={t(
        'aITools.howItWorksSubtitle',
        'The long version. Philosophy, receipts, and the eight questions we ask before we deploy anything.',
      )}
      icon={Cpu}
    >
      {/* Back-to-/ai link, first interactive control on the page after the global skip link. */}
      <div className="mb-6">
        <Link
          to="/ai"
          className="inline-flex items-center gap-2 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
        >
          <ArrowLeft aria-hidden="true" className="w-4 h-4" />
          {t('aITools.backToAiTools', 'Back to AI tools')}
        </Link>
      </div>

      {/* This is a long technical read; keep the Sensory Quiet entry available. */}
      <SensoryQuietEntry />

      <div className="lg:grid lg:grid-cols-[1fr_14rem] lg:gap-10">
        <div className="space-y-8 lg:order-1 min-w-0">
          <BoardPolicyQuote />
          <WhySmallLibrarySection />
          <MetricsSection />
          <DataFlowMatrix />
          <RubricSection />
          <StaffImpactSection />
          <SafetyTransparencySection />
          <HardwareSection />
          <SystemPromptsSection />
          <LocalKnowledgeSection />
          <TestimonialsSection />
          <WrongnessLogSection />
          <LegalNoteSection />
        </div>

        <aside className="lg:order-2">
          <TableOfContents entries={tocEntries} />
        </aside>
      </div>
    </StandardPageLayout>
  )
}
