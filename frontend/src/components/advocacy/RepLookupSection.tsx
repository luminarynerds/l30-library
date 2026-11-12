/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { MapPin, Loader2, Search, ExternalLink, Users } from 'lucide-react'
import api from '@/lib/api-client'
import { useTranslation } from '@/i18n'
import RepLevelSection from './RepLevelSection'
import type { CivicLookupResponse, RepresentativeInfo } from './types'

interface RepLookupSectionProps {
  selectedRep: RepresentativeInfo | null
  onSelectRep: (rep: RepresentativeInfo) => void
}

export default function RepLookupSection({
  selectedRep,
  onSelectRep,
}: RepLookupSectionProps): React.ReactElement {
  const { t } = useTranslation()
  const [address, setAddress] = useState('')
  const [isLookingUp, setIsLookingUp] = useState(false)
  const [repResults, setRepResults] = useState<CivicLookupResponse | null>(null)

  const handleLookup = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    const trimmed = address.trim()
    if (!trimmed) return

    setIsLookingUp(true)
    setRepResults(null)

    try {
      const data: CivicLookupResponse = await api.get(
        `/api/v1/advocacy/reps?address=${encodeURIComponent(trimmed)}`
      )
      setRepResults(data)
    } catch (err: unknown) {
      const e = err as { status?: number; message?: string }
      if (e?.status === 503 || e?.message?.includes('not configured')) {
        setRepResults({ officials: [], not_configured: true })
      } else {
        setRepResults({ officials: [], error: 'Failed to look up representatives. Please try again.' })
      }
    } finally {
      setIsLookingUp(false)
    }
  }

  const groupedReps: Record<'federal' | 'state' | 'local', RepresentativeInfo[]> = {
    federal: [],
    state: [],
    local: [],
  }
  if (repResults?.officials) {
    for (const rep of repResults.officials) {
      const lvl = rep.level ?? 'local'
      if (lvl in groupedReps) {
        groupedReps[lvl as 'federal' | 'state' | 'local'].push(rep)
      }
    }
  }

  const hasResults =
    repResults !== null &&
    !repResults.not_configured &&
    !repResults.error &&
    repResults.officials.length > 0

  const hasNoResults =
    repResults !== null &&
    !repResults.not_configured &&
    !repResults.error &&
    repResults.officials.length === 0

  return (
    <section aria-labelledby="reps-heading">
      <div className="flex items-center gap-2 mb-4">
        <MapPin className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        <h2 id="reps-heading" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
          Find Your Representatives
        </h2>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 mb-6">
        <form onSubmit={handleLookup} className="flex gap-3 flex-col sm:flex-row">
          <div className="flex-1 relative">
            <MapPin
              className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60"
              aria-hidden="true"
            />
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder={t('advocacy.enterYourFullStreetAddress')}
              className="w-full pl-10 pr-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder-earth-400 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              aria-label={t('advocacy.streetAddressForRepresentativeLookup')}
              disabled={isLookingUp}
            />
          </div>
          <button
            type="submit"
            disabled={isLookingUp || !address.trim()}
            className="px-6 py-3 bg-lsc-rose text-white font-semibold rounded-xl hover:bg-lsc-rose/90 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose dark:focus:ring-offset-earth-800 disabled:opacity-50 flex items-center gap-2 justify-center whitespace-nowrap"
          >
            {isLookingUp ? (
              <>
                <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
                Looking up...
              </>
            ) : (
              <>
                <Search className="w-5 h-5" aria-hidden="true" />
                Find Representatives
              </>
            )}
          </button>
        </form>
      </div>

      {!repResults && !isLookingUp && (
        <div className="text-center py-10 text-lsc-dark/70 dark:text-lsc-cream/60">
          <MapPin className="w-12 h-12 mx-auto mb-3 opacity-30" aria-hidden="true" />
          <p>{t('advocacy.enterYourAddressAboveTo')}</p>
        </div>
      )}

      {repResults?.not_configured && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-700 rounded-xl p-6 text-center">
          <p className="text-status-warning-800 dark:text-status-warning-200 mb-3">
            Representative lookup is being configured. In the meantime, visit these resources:
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <a
              href="https://www.congress.gov/members/find-your-member"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 border border-status-warning-400 dark:border-status-warning-600 rounded-lg text-status-warning-800 dark:text-status-warning-200 hover:bg-status-warning-100 dark:hover:bg-status-warning-900/30 transition-colors text-sm font-medium"
            >
              <ExternalLink className="w-4 h-4" aria-hidden="true" />
              congress.gov
            </a>
            <a
              href="https://openstates.org"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 border border-status-warning-400 dark:border-status-warning-600 rounded-lg text-status-warning-800 dark:text-status-warning-200 hover:bg-status-warning-100 dark:hover:bg-status-warning-900/30 transition-colors text-sm font-medium"
            >
              <ExternalLink className="w-4 h-4" aria-hidden="true" />
              openstates.org
            </a>
          </div>
        </div>
      )}

      {repResults?.error && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-700 rounded-xl p-4 text-status-danger-700 dark:text-status-danger-300 text-sm">
          {repResults.error}
        </div>
      )}

      {hasNoResults && (
        <div className="text-center py-10 text-lsc-dark/70 dark:text-lsc-cream/60">
          <MapPin className="w-12 h-12 mx-auto mb-3 opacity-30" aria-hidden="true" />
          <p>{t('advocacy.weCouldnTFindRepresentatives')}</p>
          <p className="text-sm mt-1">{t('advocacy.pleaseTryAMoreComplete')}</p>
        </div>
      )}

      {hasResults && (
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 flex items-center gap-1.5">
            <Users className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            {selectedRep
              ? 'Click a representative to select them for the letter composer below.'
              : 'Click a representative card to select them for the letter composer.'}
          </p>
          {(['federal', 'state', 'local'] as const).map((level) => (
            <RepLevelSection
              key={level}
              level={level}
              reps={groupedReps[level]}
              selectedRep={selectedRep}
              onSelectRep={onSelectRep}
            />
          ))}
        </div>
      )}
    </section>
  )
}
