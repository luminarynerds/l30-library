/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Dna, Plus, Loader, Users, Info,
  ExternalLink,
  TrendingUp, Database
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  dnaApi,
  personsApi,
  type DNAProfile,
  type DNAMatch,
  type PersonSummary,
} from '@/api/genealogy-research-api'
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface GenealogyDNAPageProps {
  projectId: number
}

function getTestTypes(t: (key: string, fallback?: string) => string) {
  return [
    { value: 'autosomal', label: t('genealogyDNA.autosomalDnaAtdna', 'Autosomal DNA (atDNA)'), desc: t('genealogyDNA.testsAllChromosomesMatchesWith', 'Tests all chromosomes; matches with relatives up to ~7 generations') },
    { value: 'y_dna', label: t('genealogyDNA.yDna', 'Y-DNA'), desc: t('genealogyDNA.testsTheYChromosomeTraces', 'Tests the Y chromosome; traces direct paternal line') },
    { value: 'mtdna', label: t('genealogyDNA.mitochondrialDnaMtdna', 'Mitochondrial DNA (mtDNA)'), desc: t('genealogyDNA.tracesDirectMaternalLine', 'Traces direct maternal line') },
    { value: 'x_dna', label: t('genealogyDNA.xDna', 'X-DNA'), desc: t('genealogyDNA.specializedXChromosomeAnalysis', 'Specialized X-chromosome analysis') },
  ]
}

const TESTING_COMPANIES = [
  'AncestryDNA', '23andMe', 'MyHeritage DNA', 'FamilyTreeDNA', 'LivingDNA',
  'Nebula Genomics', 'Dante Labs', 'Other'
]

function getRelationshipRanges(t: (key: string, fallback?: string) => string): Record<string, { label: string; cm: string; desc: string; color: string }> {
  return {
    'Parent/Child': { label: t('genealogyDNA.relationshipParentChild', 'Parent/Child'), cm: '~3,400–3,900 cM', desc: t('genealogyDNA.parentChildOrIdenticalTwin', 'Parent, child, or identical twin'), color: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300' },
    'Full Sibling': { label: t('genealogyDNA.relationshipFullSibling', 'Full Sibling'), cm: '~2,300–3,900 cM', desc: t('genealogyDNA.fullSibling', 'Full sibling'), color: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light' },
    '1st Cousin': { label: t('genealogyDNA.relationshipFirstCousin', '1st Cousin'), cm: '~550–1,200 cM', desc: t('genealogyDNA.firstCousinOrGrandparentgrandchild', 'First cousin or grandparent/grandchild'), color: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300' },
    '2nd Cousin': { label: t('genealogyDNA.relationshipSecondCousin', '2nd Cousin'), cm: '~200–650 cM', desc: t('genealogyDNA.secondCousinOrGreatgrandparent', 'Second cousin or great-grandparent'), color: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300' },
    '3rd Cousin': { label: t('genealogyDNA.relationshipThirdCousin', '3rd Cousin'), cm: '~50–200 cM', desc: t('genealogyDNA.thirdCousinOrMoreDistant', 'Third cousin or more distant'), color: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300' },
    'Distant': { label: t('genealogyDNA.relationshipDistant', 'Distant'), cm: '<50 cM', desc: t('genealogyDNA.fourthCousinOrMoreDistant', 'Fourth cousin or more distant'), color: 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300' },
  }
}

export default function GenealogyDNAPage({ projectId }: GenealogyDNAPageProps) {
  const { t } = useTranslation()
  const [profiles, setProfiles] = useState<DNAProfile[]>([])
  const [persons, setPersons] = useState<PersonSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedProfile, setSelectedProfile] = useState<DNAProfile | null>(null)
  const [profileMatches, setProfileMatches] = useState<DNAMatch[]>([])
  const [matchesLoading, setMatchesLoading] = useState(false)
  const [showAddProfile, setShowAddProfile] = useState(false)
  const [showAddMatch, setShowAddMatch] = useState(false)
  const [activeTab, setActiveTab] = useState<'profiles' | 'matches' | 'guidance'>('profiles')

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [profilesData, personsData] = await Promise.all([
        dnaApi.listProfiles(projectId),
        personsApi.list(projectId),
      ])
      setProfiles(profilesData as DNAProfile[])
      setPersons(personsData as PersonSummary[])
    } catch {
      toast.error(t('genealogyDNA.failedToLoadDnaProfiles'))
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function loadMatches(profileId: number) {
    try {
      setMatchesLoading(true)
      const matches = await dnaApi.getMatches(projectId, profileId)
      setProfileMatches(matches as DNAMatch[])
    } catch {
      toast.error(t('genealogyDNA.failedToLoadDnaMatches'))
    } finally {
      setMatchesLoading(false)
    }
  }

  async function selectProfile(profile: DNAProfile) {
    setSelectedProfile(profile)
    setActiveTab('matches')
    await loadMatches(profile.id)
  }

  function getPersonName(personId: number | null) {
    if (!personId) return t('genealogyDNA.unknown', 'Unknown')
    const p = persons.find(x => x.id === personId)
    return p ? `${p.given_names} ${p.surname || ''}`.trim() : t('genealogyDNA.personHashId', { personId })
  }

  function getMatchStrength(cM: number | null): { label: string; color: string } {
    if (!cM) return { label: t('genealogyDNA.unknown', 'Unknown'), color: 'text-lsc-dark/70 dark:text-lsc-cream/70' }
    if (cM >= 2000) return { label: t('genealogyDNA.veryClose', 'Very Close'), color: 'text-category-600 dark:text-category-400' }
    if (cM >= 900) return { label: t('genealogyDNA.close', 'Close'), color: 'text-lsc-rose dark:text-lsc-rose-light' }
    if (cM >= 400) return { label: t('genealogyDNA.moderate', 'Moderate'), color: 'text-status-success-600 dark:text-status-success-400' }
    if (cM >= 100) return { label: t('genealogyDNA.distant', 'Distant'), color: 'text-status-warning-600 dark:text-status-warning-400' }
    return { label: t('genealogyDNA.veryDistant', 'Very Distant'), color: 'text-status-danger-600 dark:text-status-danger-400' }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader className="w-8 h-8 motion-safe:animate-spin text-status-warning-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <Dna className="w-5 h-5 text-category-500" />
            {t('genealogyDNA.dnaAnalysis', 'DNA Analysis')}
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {t('genealogyDNA.profileCount', { count: profiles.length })} &bull; {t('genealogyDNA.matchesLoadedCount', { count: profileMatches.length })}
          </p>
        </div>
        <button
          onClick={() => setShowAddProfile(true)}
          className="flex items-center gap-2 px-3 py-2 bg-category-600 text-white rounded-lg hover:bg-category-700 text-sm"
        >
          <Plus className="w-4 h-4" />
          {t('genealogyDNA.addDnaProfile', 'Add DNA Profile')}
        </button>
      </div>

      {/* Info Banner */}
      <div className="bg-category-50 dark:bg-category-900/20 border border-category-200 dark:border-category-800 rounded-lg p-4 flex gap-3">
        <Info className="w-5 h-5 text-category-500 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-category-800 dark:text-category-300">
          <strong>{t('genealogyDNA.dnaResearchHub', 'DNA Research Hub.')}</strong> {t('genealogyDNA.trackDnaTestResultsRecordGenetic', 'Track DNA test results, record genetic matches, and use centimorgans (cM) data to estimate relationships. This interface integrates with external services like AncestryDNA, 23andMe, and FamilyTreeDNA as reference data.')}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-lsc-border dark:border-earth-700">
        <nav className="flex gap-1 -mb-px">
          {([
            { id: 'profiles', label: t('genealogyDNA.dnaProfiles', 'DNA Profiles'), count: profiles.length },
            { id: 'matches', label: t('genealogyDNA.matches', 'Matches'), count: selectedProfile ? profileMatches.length : null },
            { id: 'guidance', label: t('genealogyDNA.researchGuidance', 'Research Guidance') },
          ] as { id: typeof activeTab; label: string; count?: number | null }[]).map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-category-500 text-category-600 dark:text-category-400'
                  : 'border-transparent text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300'
              }`}
            >
              {tab.label}
              {tab.count !== null && tab.count !== undefined && (
                <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab: Profiles */}
      {activeTab === 'profiles' && (
        <div className="space-y-4">
          {profiles.length === 0 ? (
            <div className="text-center py-16 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
              <Dna className="w-14 h-14 mx-auto text-earth-300 mb-4" />
              <h3 className="font-serif font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{t('genealogyDNA.noDnaProfilesYet')}</h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-5 max-w-sm mx-auto">
                {t('genealogyDNA.addDnaTestResultsForFamily', 'Add DNA test results for family members to track genetic connections and analyze matches across testing platforms.')}
              </p>
              <button onClick={() => setShowAddProfile(true)}
                className="px-5 py-2 bg-category-600 text-white rounded-lg hover:bg-category-700">
                {t('genealogyDNA.addFirstProfile', 'Add First Profile')}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {profiles.map(profile => {
                const person = persons.find(p => p.id === profile.person_id)
                const testType = getTestTypes(t).find(tt => tt.value === profile.test_type)
                return (
                  <div
                    key={profile.id}
                    className={`bg-lsc-white dark:bg-earth-800 rounded-xl border p-5 cursor-pointer transition-all hover:shadow-md ${
                      selectedProfile?.id === profile.id
                        ? 'border-category-400 ring-2 ring-category-200 dark:ring-category-800'
                        : 'border-lsc-border dark:border-earth-700'
                    }`}
                    onClick={() => selectProfile(profile)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => selectProfile(profile))(); } }}
                  >
                    <div className="flex items-start gap-3 mb-3">
                      <div className="w-10 h-10 rounded-full bg-category-100 dark:bg-category-900/30 flex items-center justify-center flex-shrink-0">
                        <Dna className="w-5 h-5 text-category-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                          {person ? `${person.given_names} ${person.surname || ''}`.trim() : t('genealogyDNA.personHashId', { personId: profile.person_id })}
                        </p>
                        <p className="text-sm text-category-600 dark:text-category-400">
                          {testType?.label || profile.test_type.replace(/_/g, ' ').toUpperCase()}
                        </p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {profile.testing_company && (
                        <div>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyDNA.companyLabel', 'Company:')}</span> {profile.testing_company}
                        </div>
                      )}
                      {profile.kit_number && (
                        <div>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyDNA.kitLabel', 'Kit:')}</span> {profile.kit_number}
                        </div>
                      )}
                      {profile.haplogroup && (
                        <div>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyDNA.haplogroupLabel', 'Haplogroup:')}</span>
                          <span className="font-mono ml-1 text-category-600 dark:text-category-400">{profile.haplogroup}</span>
                        </div>
                      )}
                      {profile.test_date && (
                        <div>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyDNA.testedLabel', 'Tested:')}</span> {profile.test_date}
                        </div>
                      )}
                    </div>
                    {profile.ethnicity_estimate && (
                      <div className="mt-3 pt-3 border-t border-earth-100 dark:border-earth-700">
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.ethnicityEstimate', 'Ethnicity Estimate')}</p>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{profile.ethnicity_estimate}</p>
                      </div>
                    )}
                    <div className="mt-3 pt-3 border-t border-earth-100 dark:border-earth-700 flex items-center justify-between">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        profile.consent_given
                          ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300'
                          : 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300'
                      }`}>
                        {profile.consent_given ? t('genealogyDNA.consentGiven', 'Consent Given') : t('genealogyDNA.noConsent', 'No Consent')}
                      </span>
                      <span className="text-xs text-category-600 dark:text-category-400 font-medium">
                        {t('genealogyDNA.viewMatchesArrow', 'View Matches →')}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab: Matches */}
      {activeTab === 'matches' && (
        <div className="space-y-4">
          {!selectedProfile ? (
            <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
              <Dna className="w-12 h-12 mx-auto text-earth-300 mb-3" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyDNA.selectADnaProfileFrom')}</p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                    {t('genealogyDNA.matchesFor', { name: getPersonName(selectedProfile.person_id) })}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {selectedProfile.testing_company} &bull; {selectedProfile.test_type.replace(/_/g, ' ').toUpperCase()}
                  </p>
                </div>
                <button
                  onClick={() => setShowAddMatch(true)}
                  className="flex items-center gap-2 px-3 py-2 bg-category-600 text-white rounded-lg hover:bg-category-700 text-sm"
                >
                  <Plus className="w-4 h-4" />
                  {t('genealogyDNA.recordMatch', 'Record Match')}
                </button>
              </div>

              {matchesLoading ? (
                <div className="flex justify-center py-12">
                  <Loader className="w-6 h-6 motion-safe:animate-spin text-category-500" />
                </div>
              ) : profileMatches.length === 0 ? (
                <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
                  <Users className="w-12 h-12 mx-auto text-earth-300 mb-3" />
                  <h3 className="font-serif font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{t('genealogyDNA.noMatchesRecorded', 'No Matches Recorded')}</h3>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-4 max-w-sm mx-auto">
                    {t('genealogyDNA.recordDnaMatchesFromYourTesting', "Record DNA matches from your testing platform's results. Enter shared centimorgans (cM) and segment data for relationship analysis.")}
                  </p>
                  <button onClick={() => setShowAddMatch(true)}
                    className="px-5 py-2 bg-category-600 text-white rounded-lg hover:bg-category-700">
                    {t('genealogyDNA.recordFirstMatch', 'Record First Match')}
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {profileMatches
                    .sort((a, b) => (b.shared_centimorgans || 0) - (a.shared_centimorgans || 0))
                    .map(match => {
                      const strength = getMatchStrength(match.shared_centimorgans)
                      const otherProfileId = match.profile1_id === selectedProfile.id
                        ? match.profile2_id : match.profile1_id

                      return (
                        <div key={match.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
                          <div className="flex items-start gap-4 justify-between">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-3 mb-2">
                                <div className="w-9 h-9 rounded-full bg-category-100 dark:bg-category-900/30 flex items-center justify-center">
                                  <Users className="w-4 h-4 text-category-500" />
                                </div>
                                <div>
                                  <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">
                                    {t('genealogyDNA.profileHashId', { profileId: otherProfileId })}
                                  </p>
                                  {match.predicted_relationship && (
                                    <p className="text-xs text-category-600 dark:text-category-400">
                                      {match.predicted_relationship}
                                    </p>
                                  )}
                                </div>
                              </div>
                              <div className="grid grid-cols-3 gap-3 text-xs">
                                {match.shared_centimorgans !== null && match.shared_centimorgans !== undefined && (
                                  <div>
                                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyDNA.sharedCm', 'Shared cM')}</p>
                                    <p className={`font-semibold text-sm ${strength.color}`}>
                                      {match.shared_centimorgans.toFixed(1)} cM
                                    </p>
                                    <p className={`text-[10px] ${strength.color}`}>{strength.label}</p>
                                  </div>
                                )}
                                {match.shared_segments !== null && match.shared_segments !== undefined && (
                                  <div>
                                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyDNA.segments', 'Segments')}</p>
                                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">{match.shared_segments}</p>
                                  </div>
                                )}
                                {match.longest_segment !== null && match.longest_segment !== undefined && (
                                  <div>
                                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyDNA.longest', 'Longest')}</p>
                                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">{match.longest_segment.toFixed(1)} cM</p>
                                  </div>
                                )}
                              </div>
                              {match.confidence_level !== null && match.confidence_level !== undefined && (
                                <div className="mt-2">
                                  <div className="flex items-center gap-2">
                                    <div className="flex-1 h-1.5 bg-earth-200 dark:bg-earth-700 rounded-full overflow-hidden">
                                      <div className="h-full bg-category-500 rounded-full" style={{ width: `${match.confidence_level * 100}%` }} />
                                    </div>
                                    <span className="text-[10px] text-lsc-dark/70 dark:text-lsc-cream/70">
                                      {t('genealogyDNA.percentConfidence', { percent: Math.round(match.confidence_level * 100) })}
                                    </span>
                                  </div>
                                </div>
                              )}
                              {match.notes && (
                                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 italic">{match.notes}</p>
                              )}
                            </div>
                            <span className={`text-[10px] px-2 py-0.5 rounded-full flex-shrink-0 ${
                              match.status === 'confirmed' ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300' :
                              match.status === 'disputed' ? 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300' :
                              'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300'
                            }`}>
                              {match.status === 'confirmed' ? t('genealogyDNA.statusConfirmed', 'confirmed')
                                : match.status === 'disputed' ? t('genealogyDNA.statusDisputed', 'disputed')
                                : match.status === 'pending' ? t('genealogyDNA.statusPending', 'pending')
                                : match.status}
                            </span>
                          </div>
                        </div>
                      )
                    })
                  }
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Tab: Research Guidance */}
      {activeTab === 'guidance' && (
        <DNAResearchGuidance persons={persons} profiles={profiles} />
      )}

      {/* Modals */}
      {showAddProfile && (
        <AddDNAProfileModal
          projectId={projectId}
          persons={persons}
          onClose={() => setShowAddProfile(false)}
          onCreated={() => { setShowAddProfile(false); loadData() }}
        />
      )}
      {showAddMatch && selectedProfile && (
        <AddDNAMatchModal
          profileId={selectedProfile.id}
          projectId={projectId}
          profiles={profiles}
          onClose={() => setShowAddMatch(false)}
          onCreated={() => { setShowAddMatch(false); loadMatches(selectedProfile.id) }}
        />
      )}
    </div>
  )
}

// ============================================================================
// DNA Research Guidance Component
// ============================================================================

function DNAResearchGuidance({ persons, profiles }: { persons: PersonSummary[]; profiles: DNAProfile[] }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-6">
      {/* cM Reference Chart */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-category-500" />
          {t('genealogyDNA.sharedDnaReferenceChart', 'Shared DNA Reference Chart')}
        </h3>
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('genealogyDNA.useSharedCentimorgansCmTo', 'Use shared centimorgans (cM) to estimate relationships. Ranges overlap — use in combination with family tree information.')}
        </p>
        <div className="space-y-2">
          {Object.entries(getRelationshipRanges(t)).map(([rel, data]) => (
            <div key={rel} className="flex items-center gap-3">
              <div className="w-28 flex-shrink-0">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${data.color}`}>{data.label}</span>
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-lsc-dark/70 dark:text-lsc-cream/70">{data.cm}</span>
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{data.desc}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Test Type Guide */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Dna className="w-4 h-4 text-category-500" />
          {t('genealogyDNA.dnaTestTypeGuide', 'DNA Test Type Guide')}
        </h3>
        <div className="space-y-3">
          {getTestTypes(t).map(type => (
            <div key={type.value} className="p-3 rounded-lg bg-earth-50 dark:bg-earth-700/50">
              <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{type.label}</p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{type.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* External Databases */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Database className="w-4 h-4 text-earth-600" />
          {t('genealogyDNA.recommendedDnaDatabases', 'Recommended DNA Databases')}
        </h3>
        <div className="space-y-3">
          {[
            { name: 'GEDmatch', url: 'https://gedmatch.com', desc: t('genealogyDNA.uploadRawDnaFromAny', 'Upload raw DNA from any provider; compare with matches from multiple companies') },
            { name: 'DNA Painter', url: 'https://dnapainter.com', desc: t('genealogyDNA.mapChromosomeSegmentsAndVisualize', 'Map chromosome segments and visualize shared DNA with matches') },
            { name: 'The WATO Tool', url: 'https://dnapainter.com/tools/wato', desc: t('genealogyDNA.whatAreTheOddsTest', 'What Are The Odds? - Test relationship hypotheses using cM data') },
            { name: 'Shared cM Project', url: 'https://dnapainter.com/tools/sharedcmv4', desc: t('genealogyDNA.calculateProbabilityOfVariousRelationships', 'Calculate probability of various relationships from cM amounts') },
            { name: 'FamilyTreeDNA', url: 'https://familytreedna.com', desc: t('genealogyDNA.bestForYdnaAndMtdna', 'Best for Y-DNA and mtDNA deep ancestry testing') },
          ].map(db => (
            <a
              key={db.name}
              href={db.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg bg-earth-50 dark:bg-earth-700/50 hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm text-lsc-rose dark:text-lsc-rose-light">{db.name}</span>
                <ExternalLink className="w-3.5 h-3.5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </div>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{db.desc}</p>
            </a>
          ))}
        </div>
      </div>

      {/* Profile Summary */}
      {profiles.length > 0 && (
        <div className="bg-category-50 dark:bg-category-900/20 border border-category-200 dark:border-category-800 rounded-lg p-4">
          <h3 className="font-semibold text-category-900 dark:text-category-300 mb-3 text-sm">{t('genealogyDNA.yourProjectSDnaCoverage')}</h3>
          <div className="space-y-2">
            {profiles.map(p => {
              const person = persons.find(x => x.id === p.person_id)
              return (
                <div key={p.id} className="flex items-center justify-between text-sm">
                  <span className="text-category-800 dark:text-category-300">
                    {person ? `${person.given_names} ${person.surname || ''}`.trim() : t('genealogyDNA.personHashId', { personId: p.person_id })}
                  </span>
                  <span className="text-xs px-2 py-0.5 bg-category-100 dark:bg-category-800 text-category-700 dark:text-category-300 rounded-full">
                    {p.test_type.replace(/_/g, ' ').toUpperCase()} &bull; {p.testing_company || t('genealogyDNA.unknown', 'Unknown')}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Add DNA Profile Modal
// ============================================================================

function AddDNAProfileModal({ projectId, persons, onClose, onCreated }: {
  projectId: number
  persons: PersonSummary[]
  onClose: () => void
  onCreated: () => void
}) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    person_id: '',
    test_type: 'autosomal',
    testing_company: '',
    kit_number: '',
    test_date: '',
    haplogroup: '',
    ethnicity_estimate: '',
    consent_given: true,
    consent_scope: '',
  })
  const [saving, setSaving] = useState(false)

  async function handleSubmit() {
    if (!formData.person_id) return
    try {
      setSaving(true)
      await dnaApi.createProfile(projectId, {
        person_id: Number(formData.person_id),
        project_id: projectId,
        test_type: formData.test_type,
        testing_company: formData.testing_company || undefined,
        kit_number: formData.kit_number || undefined,
        test_date: formData.test_date || undefined,
        haplogroup: formData.haplogroup || undefined,
        ethnicity_estimate: formData.ethnicity_estimate || undefined,
        consent_given: formData.consent_given,
        consent_scope: formData.consent_scope || undefined,
      } as Partial<DNAProfile>)
      toast.success(t('toast.genealogyDNA.dnaProfileAdded'))
      onCreated()
    } catch {
      toast.error(t('genealogyDNA.failedToAddDnaProfile'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title={t('genealogyDNA.dialogTitle', 'Dialog')}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="font-serif text-xl font-bold mb-5 text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <Dna className="w-5 h-5 text-category-500" />
          {t('genealogyDNA.addDnaProfile', 'Add DNA Profile')}
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.personLabel', 'Person *')}</label>
            <select value={formData.person_id} onChange={e => setFormData(p => ({ ...p, person_id: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm">
              <option value="">{t('genealogyDNA.selectAPerson', 'Select a person...')}</option>
              {persons.map(p => (
                <option key={p.id} value={p.id}>{p.given_names} {p.surname || ''}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.testTypeLabel', 'Test Type')}</label>
            <select value={formData.test_type} onChange={e => setFormData(p => ({ ...p, test_type: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm">
              {getTestTypes(t).map(tt => <option key={tt.value} value={tt.value}>{tt.label}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.testingCompanyLabel', 'Testing Company')}</label>
              <select value={formData.testing_company} onChange={e => setFormData(p => ({ ...p, testing_company: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm">
                <option value="">{t('genealogyDNA.selectEllipsis', 'Select...')}</option>
                {TESTING_COMPANIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.kitNumberLabel', 'Kit Number')}</label>
              <input type="text" value={formData.kit_number} onChange={e => setFormData(p => ({ ...p, kit_number: e.target.value }))}
                placeholder={t('placeholder.genealogyDNA.egA123456')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.testDateLabel', 'Test Date')}</label>
              <input type="date" value={formData.test_date} onChange={e => setFormData(p => ({ ...p, test_date: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.haplogroupLabel2', 'Haplogroup')}</label>
              <input type="text" value={formData.haplogroup} onChange={e => setFormData(p => ({ ...p, haplogroup: e.target.value }))}
                placeholder={t('placeholder.genealogyDNA.egRm269OrH1a')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm font-mono" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.ethnicityEstimate', 'Ethnicity Estimate')}</label>
            <textarea value={formData.ethnicity_estimate} onChange={e => setFormData(p => ({ ...p, ethnicity_estimate: e.target.value }))}
              rows={2} placeholder={t('placeholder.genealogyDNA.egIreland45Scotland')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm resize-none" />
          </div>
          <label className="flex items-start gap-3 p-3 rounded-lg bg-earth-50 dark:bg-earth-700/50 cursor-pointer">
            <input type="checkbox" checked={formData.consent_given} onChange={e => setFormData(p => ({ ...p, consent_given: e.target.checked }))} className="mt-0.5 accent-category-500" />
            <div>
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{t('genealogyDNA.privacyConsentGiven', 'Privacy Consent Given')}</p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{t('genealogyDNA.thePersonWhoseDnaWas')}</p>
            </div>
          </label>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800">{t('genealogyDNA.cancel', 'Cancel')}</button>
          <button onClick={handleSubmit} disabled={!formData.person_id || saving}
            className="px-5 py-2 bg-category-600 text-white rounded-lg hover:bg-category-700 disabled:opacity-50 font-medium">
            {saving ? t('genealogyDNA.adding', 'Adding...') : t('genealogyDNA.addProfile', 'Add Profile')}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

// ============================================================================
// Add DNA Match Modal
// ============================================================================

function AddDNAMatchModal({ profileId, projectId, profiles, onClose, onCreated }: {
  profileId: number
  projectId: number
  profiles: DNAProfile[]
  onClose: () => void
  onCreated: () => void
}) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    profile2_id: '',
    shared_centimorgans: '',
    shared_segments: '',
    longest_segment: '',
    predicted_relationship: '',
    confidence_level: '0.8',
    notes: '',
  })
  const [saving, setSaving] = useState(false)

  async function handleSubmit() {
    if (!formData.profile2_id) return
    try {
      setSaving(true)
      await dnaApi.createMatch(projectId, {
        profile1_id: profileId,
        profile2_id: Number(formData.profile2_id),
        shared_centimorgans: formData.shared_centimorgans ? Number(formData.shared_centimorgans) : undefined,
        shared_segments: formData.shared_segments ? Number(formData.shared_segments) : undefined,
        longest_segment: formData.longest_segment ? Number(formData.longest_segment) : undefined,
        predicted_relationship: formData.predicted_relationship || undefined,
        confidence_level: Number(formData.confidence_level),
        notes: formData.notes || undefined,
        status: 'pending',
      } as Partial<DNAMatch>)
      toast.success(t('toast.genealogyDNA.dnaMatchRecorded'))
      onCreated()
    } catch {
      toast.error(t('genealogyDNA.failedToRecordMatch'))
    } finally {
      setSaving(false)
    }
  }

  const otherProfiles = profiles.filter(p => p.id !== profileId)

  return (
    <ModalBackdrop onClose={onClose} title={t('genealogyDNA.recordDnaMatch', 'Record DNA Match')}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full p-6">
        <h2 className="font-serif text-xl font-bold mb-5 text-lsc-dark dark:text-lsc-cream">{t('genealogyDNA.recordDnaMatch', 'Record DNA Match')}</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.matchingProfileLabel', 'Matching Profile *')}</label>
            <select value={formData.profile2_id} onChange={e => setFormData(p => ({ ...p, profile2_id: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm">
              <option value="">{t('genealogyDNA.selectAProfile', 'Select a profile...')}</option>
              {otherProfiles.map(p => (
                <option key={p.id} value={p.id}>{t('genealogyDNA.profileOptionLine', { profileId: p.id, testType: p.test_type.replace(/_/g, ' '), company: p.testing_company || t('genealogyDNA.unknown', 'Unknown') })}</option>
              ))}
            </select>
            {otherProfiles.length === 0 && (
              <p className="text-xs text-status-warning-600 mt-1">{t('genealogyDNA.addAtLeastDnaProfiles')}</p>
            )}
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.sharedCm', 'Shared cM')}</label>
              <input type="number" min="0" step="0.1" value={formData.shared_centimorgans}
                onChange={e => setFormData(p => ({ ...p, shared_centimorgans: e.target.value }))}
                placeholder={t('placeholder.genealogyDNA.eg8472')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.segments', 'Segments')}</label>
              <input type="number" min="0" value={formData.shared_segments}
                onChange={e => setFormData(p => ({ ...p, shared_segments: e.target.value }))}
                placeholder={t('placeholder.genealogyDNA.eg24')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.longestCm', 'Longest (cM)')}</label>
              <input type="number" min="0" step="0.1" value={formData.longest_segment}
                onChange={e => setFormData(p => ({ ...p, longest_segment: e.target.value }))}
                placeholder={t('placeholder.genealogyDNA.eg645')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.predictedRelationshipLabel', 'Predicted Relationship')}</label>
            <input type="text" value={formData.predicted_relationship}
              onChange={e => setFormData(p => ({ ...p, predicted_relationship: e.target.value }))}
              placeholder={t('placeholder.genealogyDNA.eg2ndCousinGrandparentgrandchild')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              {t('genealogyDNA.confidencePercent', { percent: Math.round(Number(formData.confidence_level) * 100) })}
            </label>
            <input type="range" min="0" max="1" step="0.05" value={formData.confidence_level}
              onChange={e => setFormData(p => ({ ...p, confidence_level: e.target.value }))}
              className="w-full accent-category-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDNA.notesLabel', 'Notes')}</label>
            <textarea value={formData.notes} onChange={e => setFormData(p => ({ ...p, notes: e.target.value }))}
              rows={2} placeholder={t('genealogyDNA.additionalObservationsAboutThisMatch')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm resize-none" />
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800">{t('genealogyDNA.cancel', 'Cancel')}</button>
          <button onClick={handleSubmit} disabled={!formData.profile2_id || saving || otherProfiles.length === 0}
            className="px-5 py-2 bg-category-600 text-white rounded-lg hover:bg-category-700 disabled:opacity-50 font-medium">
            {saving ? t('genealogyDNA.recording', 'Recording...') : t('genealogyDNA.recordMatch', 'Record Match')}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
