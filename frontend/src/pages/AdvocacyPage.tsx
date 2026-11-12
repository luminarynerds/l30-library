/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Megaphone, BookOpen, ChevronRight } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useTranslation } from '@/i18n'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import BanContextSections from '@/components/advocacy/BanContextSections'
import RepLookupSection from '@/components/advocacy/RepLookupSection'
import LetterComposerSection from '@/components/advocacy/LetterComposerSection'
import ResourcesSection from '@/components/advocacy/ResourcesSection'
import { useBanContextData } from '@/components/advocacy/hooks'
import type { RepresentativeInfo } from '@/components/advocacy/types'

export default function AdvocacyPage(): React.ReactElement {
  const { t } = useTranslation()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const banTrackingEnabled = isFeatureEnabled('banned_books_tracking_enabled')
  const { banStats, mostBanned, loading: banDataLoading } = useBanContextData(banTrackingEnabled)
  const [selectedRep, setSelectedRep] = useState<RepresentativeInfo | null>(null)

  return (
    <StandardPageLayout
      title="Advocacy Hub"
      subtitle={t('advocacy.findYourRepresentativesAndMake')}
      icon={Megaphone}
    >
      <div className="bg-gradient-to-r from-lsc-rose to-lsc-brown rounded-xl p-8 text-white mb-8 -mt-4">
        <div className="flex items-start gap-4">
          <Megaphone className="w-10 h-10 flex-shrink-0 mt-0.5 opacity-90" aria-hidden="true" />
          <div>
            <h2 className="text-2xl font-serif font-bold mb-1">Your Voice Matters</h2>
            <p className="text-white/85 text-base leading-relaxed max-w-2xl">
              Libraries are under pressure. Use the tools below to contact your elected officials, write
              personalized letters, and defend the freedom to read.
            </p>
          </div>
        </div>
      </div>

      {banTrackingEnabled && (
        <div className="flex items-center gap-2 -mt-4 mb-2">
          <BookOpen className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          <Link
            to="/ban-tracker"
            className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium flex items-center gap-1"
          >
            See what books are being banned
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
            Book Ban Tracker
          </Link>
        </div>
      )}

      {banTrackingEnabled && (
        <BanContextSections banStats={banStats} mostBanned={mostBanned} loading={banDataLoading} />
      )}

      <RepLookupSection selectedRep={selectedRep} onSelectRep={setSelectedRep} />

      <LetterComposerSection selectedRep={selectedRep} />

      <ResourcesSection />
    </StandardPageLayout>
  )
}
