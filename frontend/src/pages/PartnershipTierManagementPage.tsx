/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import { useTranslation} from '../i18n/I18nContext'
import toast from 'react-hot-toast'
import { fetchApi } from '@/api/fetchApi'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

// GET /school-partnerships/partnership-tiers returns
// {tiers: [{tier: "bronze", details: {name, color, features: [...], ...}}]}
// (tiers.py:162). Normalize each item into this flat shape.
interface PartnershipTier {
  slug: string
  name: string
  benefits: string[]
}

// GET /school-partnerships/schools returns
// {id, name, address, city, state, partnership_tier} (snake_case).
interface SchoolTier {
  schoolId: number
  schoolName: string
  currentTier: string
}

const TIER_COLORS: { [key: string]: string } = {
  BRONZE: 'bg-status-warning-100 dark:bg-status-warning-900/30 border-status-warning-300 dark:border-status-warning-700 text-status-warning-900 dark:text-status-warning-200',
  SILVER: 'bg-earth-100 dark:bg-earth-700 border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream',
  GOLD: 'bg-status-warning-100 dark:bg-status-warning-900/30 border-status-warning-300 dark:border-status-warning-700 text-status-warning-900 dark:text-status-warning-200',
  PLATINUM: 'bg-category-100 dark:bg-category-900/30 border-category-300 dark:border-category-700 text-category-900 dark:text-category-200',
}

export default function PartnershipTierManagementPage() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [tiers, setTiers] = useState<PartnershipTier[]>([])
  const [schools, setSchools] = useState<SchoolTier[]>([])
  const [selectedSchool, setSelectedSchool] = useState<SchoolTier | null>(null)
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  const [selectedNewTier, setSelectedNewTier] = useState('')
  const [view, setView] = useState<'tiers' | 'schools'>('tiers')

  const fetchSchools = async () => {
    try {
      const data = await fetchApi('/school-partnerships/schools')
      const list = Array.isArray(data) ? data : (data?.schools ?? [])
      setSchools(
        list.map((s: { id: number; name: string; partnership_tier?: string }) => ({
          schoolId: s.id,
          schoolName: s.name,
          currentTier: s.partnership_tier ?? 'bronze',
        })),
      )
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('partnershipTierManagement.failedToLoadSchools'))
    } finally {
      setLoading(false)
    }
  }


  const fetchTiers = async () => {
    try {
      const data = await fetchApi('/school-partnerships/partnership-tiers')
      const raw = Array.isArray(data) ? data : (data?.tiers ?? [])
      setTiers(
        raw.map((t: { tier: string; details?: { name?: string; features?: string[] } }) => ({
          slug: t.tier,
          name: t.details?.name ?? t.tier,
          benefits: t.details?.features ?? [],
        })),
      )
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('partnershipTierManagement.failedToLoadPartnershipTiers'))
    }
  }


  useEffect(() => {
    fetchTiers()
    fetchSchools()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleUpgradeTier = async () => {
    if (!selectedSchool || !selectedNewTier) return

    try {
      await fetchApi(
        `/school-partnerships/schools/${selectedSchool.schoolId}/upgrade-tier/${selectedNewTier}`,
        { method: 'POST' }
      )
      toast.success(t('toast.partnershipTierManagement.successfullyUpgradedSchoolnameToSelectednewtier', { schoolName: selectedSchool.schoolName, selectedNewTier: selectedNewTier }))
      setShowUpgradeModal(false)
      setSelectedSchool(null)
      setSelectedNewTier('')
      fetchSchools()
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('partnershipTierManagement.errorUpdatingPartnershipTier'))
    }
  }

  return (

    <AdminShell title="Partnership Tier Management">    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Partnership Tier Management
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Manage school partnership tiers and benefits
          </p>
        </div>

        {/* View Tabs */}
        <div className="flex gap-4 mb-8">
          <button
            onClick={() => setView('tiers')}
            className={`px-6 py-3 rounded-lg font-medium transition ${
              view === 'tiers'
                ? 'bg-earth-600 text-white'
                : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-earth-100 dark:hover:bg-earth-700'
            }`}
          >
            Partnership Tiers
          </button>
          <button
            onClick={() => setView('schools')}
            className={`px-6 py-3 rounded-lg font-medium transition ${
              view === 'schools'
                ? 'bg-earth-600 text-white'
                : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-earth-100 dark:hover:bg-earth-700'
            }`}
          >
            Schools & Tiers
          </button>
        </div>

        {/* Partnership Tiers View */}
        {view === 'tiers' && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {tiers.map((tier) => (
                <div
                  key={tier.slug}
                  className={`rounded-xl shadow-lg p-6 border-2 ${TIER_COLORS[tier.slug?.toUpperCase()] ?? ''}`}
                >
                  <h3 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">{tier.name}</h3>
                  <div className="space-y-2">
                    <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Benefits:</h4>
                    <ul className="space-y-1">
                      {tier.benefits.map((benefit, idx) => (
                        <li key={idx} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-start">
                          <span className="mr-2">✓</span>
                          <span>{benefit}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Schools & Tiers View */}
        {view === 'schools' && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">Loading schools...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-earth-100 dark:bg-earth-700 border-b border-lsc-border dark:border-earth-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        School Name
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Current Tier
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Benefits
                      </th>
                      <th className="px-6 py-3 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-earth-200 dark:divide-earth-700">
                    {schools.map((school) => (
                      <tr
                        key={school.schoolId}
                        className="hover:bg-earth-50 dark:hover:bg-earth-700 transition"
                      >
                        <td className="px-6 py-4 text-lsc-dark dark:text-lsc-cream">{school.schoolName}</td>
                        <td className="px-6 py-4">
                          <span className={`px-3 py-1 rounded-full text-sm font-semibold capitalize ${TIER_COLORS[school.currentTier?.toUpperCase()] ?? ''}`}>
                            {school.currentTier}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          {tiers.find((tier) => tier.slug === school.currentTier)?.benefits.length ?? 0} benefits
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() => {
                              setSelectedSchool(school)
                              setShowUpgradeModal(true)
                            }}
                            className="px-4 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 transition text-sm"
                          >
                            Manage Tier
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Upgrade Modal */}
        {showUpgradeModal && selectedSchool && (
          <ModalBackdrop onClose={() => { setShowUpgradeModal(false); setSelectedSchool(null); setSelectedNewTier('') }} title="Upgrade Tier">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-8">
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                Upgrade Tier for {selectedSchool.schoolName}
              </h2>

              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
                Current tier: <span className="font-semibold">{selectedSchool.currentTier}</span>
              </p>

              <div className="mb-6">
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                  Select New Tier
                </label>
                <select
                  value={selectedNewTier}
                  onChange={(e) => setSelectedNewTier(e.target.value)}
                  className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
                >
                  <option value="">-- Choose a tier --</option>
                  {tiers.map((tier) => (
                    <option key={tier.slug} value={tier.slug}>
                      {tier.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => {
                    setShowUpgradeModal(false)
                    setSelectedSchool(null)
                    setSelectedNewTier('')
                  }}
                  className="flex-1 px-4 py-2 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-300 dark:hover:bg-earth-600 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpgradeTier}
                  disabled={!selectedNewTier}
                  className="flex-1 px-4 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 disabled:bg-earth-400 transition"
                >
                  Update Tier
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}
      </div>
    </div>
  </AdminShell>
  )
}