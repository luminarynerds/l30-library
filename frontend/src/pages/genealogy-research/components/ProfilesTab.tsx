/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  Dna, Loader,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'

export default function DNATab({ projectId }: { projectId: number }) {
  const { t } = useTranslation();
  const [profiles, setProfiles] = useState<Array<{
    id: number; test_type: string; testing_company?: string;
    haplogroup?: string; kit_number?: string;
  }>>([])
  const [loading, setLoading] = useState(true)

  async function loadProfiles() {
    try {
      setLoading(true)
      const { dnaApi } = await import('@/api/genealogy-research-api')
      const data = await dnaApi.listProfiles(projectId)
      setProfiles(data)
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToLoadDnaProfiles'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    loadProfiles()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  if (loading) {
    return <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin" /></div>
  }

  return (
    <div className="space-y-4">
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">DNA Matching Interface</h2>
      <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-4">
        <p className="text-sm text-earth-800 dark:text-lsc-rose-light">
          <strong>Future Integration Ready.</strong> This interface is designed to integrate with DNA testing services
          (AncestryDNA, 23andMe, etc.). You can record DNA profiles and matches now, and full automated matching
          will be available in a future update.
        </p>
      </div>
      {profiles.length === 0 ? (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <Dna className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyResearchPageContent.noDnaProfilesYetAdd')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {profiles.map((profile) => (
            <div key={profile.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4">
              <div className="flex items-center gap-3 mb-2">
                <Dna className="w-5 h-5 text-category-500" />
                <span className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">
                  {profile.test_type.replace(/_/g, ' ').toUpperCase()}
                </span>
              </div>
              {profile.testing_company && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Provider: {profile.testing_company}</p>}
              {profile.haplogroup && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Haplogroup: {profile.haplogroup}</p>}
              {profile.kit_number && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Kit: {profile.kit_number}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
