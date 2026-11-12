/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { FileText, Loader2, Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getLegalFormPackets } from '@/api/legal-api'
import DownloadPacketButton from '../DownloadPacketButton'
import type { LegalForm } from '@/api/legal-api'
import { useTranslation } from '@/i18n'
import ExpandableFormCard from '../ExpandableFormCard'

interface FormsTabProps {
  forms: LegalForm[]
  isLoading: boolean
  searchQuery: string
  onSearchChange: (value: string) => void
}

export default function FormsTab({
  forms,
  isLoading,
  searchQuery,
  onSearchChange,
}: FormsTabProps): React.ReactElement {
  const { t } = useTranslation()

  const { data: packetsData } = useQuery({
    queryKey: ['legal-packets-for-forms'],
    queryFn: () => getLegalFormPackets({ limit: 50 }),
  })
  const packets = packetsData?.packets || []

  return (
    <div className="space-y-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 mb-6">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <input
              type="text"
              placeholder={t('placeholder.legalResources.searchLegalForms')}
              aria-label={t('aria.legalResources.searchLegalForms')}
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 min-h-[44px] border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {packets.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {packets.map((p) => (
            <DownloadPacketButton
              key={p.id}
              packetId={p.id}
              packetName={p.name}
              formCount={p.form_count}
            />
          ))}
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : forms.length > 0 ? (
        <div className="space-y-4">
          {forms.map((form) => (
            <ExpandableFormCard key={form.id} form={form} />
          ))}
        </div>
      ) : (
        <div className="text-center py-16">
          <FileText aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-4" />
          <h3 className="text-lg font-medium text-lsc-dark dark:text-earth-50 mb-2">{t('components.legal.formsTab.noFormsFound', 'No forms found')}</h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {searchQuery
              ? t('components.legal.formsTab.tryAdjustingYourSearch', 'Try adjusting your search.')
              : t('components.legal.formsTab.legalFormsWillAppear', 'Legal forms will appear here once they are added to the system.')}
          </p>
        </div>
      )}
    </div>
  )
}
