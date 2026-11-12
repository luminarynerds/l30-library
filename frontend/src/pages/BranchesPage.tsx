/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Building2 } from 'lucide-react'
import { BranchFinder } from '@/components/BranchFinder'
import { BranchDetailModal } from '@/components/BranchDetailModal'
import { Branch } from '@/api/branch-api'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useTranslation } from '@/i18n'
import { usePageTitle } from '@/hooks/usePageTitle'

export function BranchesPage() {
  usePageTitle('Library Branches & Locations')
  const { t } = useTranslation()
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'bookmobile'>('all')
  const [selectedBranch, setSelectedBranch] = useState<Branch | null>(null)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)

  const handleSelectBranch = (branch: Branch) => {
    setSelectedBranch(branch)
    setIsDetailModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsDetailModalOpen(false)
    setSelectedBranch(null)
  }

  // Footer deep-links to /branches#hours. ScrollToTop resets scroll on route
  // change and the SPA does not honor the hash natively, so scroll the hours
  // section into view ourselves once it has rendered.
  const location = useLocation()
  const hoursRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (location.hash !== '#hours') return
    const id = window.requestAnimationFrame(() => {
      hoursRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
    return () => window.cancelAnimationFrame(id)
  }, [location.hash])

  return (
    <StandardPageLayout
      title={t('branches.pageTitle', 'Our Branches')}
      subtitle={t('branches.locateYourNearestLibraryBranch')}
      icon={Building2}
      maxWidth="7xl"
    >
      {/* Quick filters */}
      <div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedFilter('all')}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors min-h-[44px] focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 ${
              selectedFilter === 'all'
                ? 'bg-lsc-rose text-white'
                : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700 hover:bg-earth-50 dark:hover:bg-earth-800'
            }`}
          >
            {t('branches.allLocations', 'All Locations')}
          </button>
          <button
            onClick={() => setSelectedFilter('bookmobile')}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors min-h-[44px] focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 ${
              selectedFilter === 'bookmobile'
                ? 'bg-category-600 text-white'
                : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700 hover:bg-earth-50 dark:hover:bg-earth-800'
            }`}
          >
            {t('branches.bookmobilesOnlyButton', 'Bookmobiles Only')}
          </button>
        </div>
      </div>

      {/* Branch finder */}
      <div
        id="hours"
        ref={hoursRef}
        className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-4 sm:p-6 scroll-mt-24"
      >
        <h2 className="sr-only">{t('branches.branchList', 'Library branches')}</h2>
        <BranchFinder
          {...(selectedFilter === 'bookmobile' ? { branchTypes: ['bookmobile'] as const } : {})}
          onSelectBranch={handleSelectBranch}
          showBookmobileFeatures={selectedFilter === 'bookmobile'}
        />
      </div>

      {/* Bookmobile info section */}
      {selectedFilter === 'bookmobile' && (
        <div>
          <div className="bg-category-50 dark:bg-category-900/20 rounded-lg p-6">
            <h2 className="font-serif text-lg font-semibold text-category-900 dark:text-category-200 mb-2">{t('branches.aboutBookmobiles', 'About Our Bookmobiles')}</h2>
            <p className="text-category-800 dark:text-category-300 mb-4">
              {t('branches.aboutBookmobilesIntro', 'Our bookmobiles bring library services directly to your neighborhood! Each bookmobile carries a rotating collection of books, audiobooks, DVDs, and more. You can also place holds and return items at any bookmobile stop.')}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4">
                <h3 className="font-medium text-category-900 dark:text-category-200">{t('branches.checkoutReturns', 'Checkout & Returns')}</h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  {t('branches.checkoutReturnsBlurb', 'Borrow and return items at any bookmobile stop. Works even when offline!')}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4">
                <h3 className="font-medium text-category-900 dark:text-category-200">{t('branches.libraryCards', 'Library Cards')}</h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  {t('branches.libraryCardsBlurb', 'Sign up for a new library card or renew your existing card on the bookmobile.')}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4">
                <h3 className="font-medium text-category-900 dark:text-category-200">{t('branches.specialPrograms', 'Special Programs')}</h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  {t('branches.specialProgramsBlurb', 'Bookmobiles host story times, summer reading programs, and community events.')}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Branch Detail Modal */}
      {selectedBranch && (
        <BranchDetailModal
          branch={selectedBranch}
          isOpen={isDetailModalOpen}
          onClose={handleCloseModal}
        />
      )}
    </StandardPageLayout>
  )
}

export default BranchesPage
