/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Scale } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import {
  getLegalCollections,
  getLegalForms,
  getLegalGuides,
  getLegalProviders,
  getLegalTopics,
  getUpcomingLegalClinics,
} from '@/api/legal-api'
import FeaturedCollections from '../components/legal/FeaturedCollections'
import QuickAccessProviders from '../components/legal/QuickAccessProviders'
import ClinicsTab from '../components/legal/tabs/ClinicsTab'
import FormsTab from '../components/legal/tabs/FormsTab'
import PrivacyTab from '../components/legal/tabs/PrivacyTab'
import ResourcesTab from '../components/legal/tabs/ResourcesTab'
import { useTranslation } from '@/i18n'
import LegalTriageWizard, { RestartTriageLink } from '../components/legal/LegalTriageWizard'

type SectionId = 'resources' | 'clinics' | 'forms' | 'privacy'

const JUMP_ANNOUNCEMENT_KEYS: Record<SectionId, { key: string; fallback: string }> = {
  resources: { key: 'legalResources.jumpedToResources', fallback: 'Jumped to Legal Resources' },
  clinics: { key: 'legalResources.jumpedToClinics', fallback: 'Jumped to Free Legal Clinics' },
  forms: { key: 'legalResources.jumpedToForms', fallback: 'Jumped to Common Forms' },
  privacy: { key: 'legalResources.jumpedToPrivacy', fallback: 'Jumped to Online Privacy & Removal' },
}

function isSectionId(value: string): value is SectionId {
  return value === 'resources' || value === 'clinics' || value === 'forms' || value === 'privacy'
}
const PAGE_SECTIONS = [
  { id: 'legal-triage-section', key: 'legalResources.jumpNavGetStarted', fallback: 'Get Started' },
  { id: 'legal-quick-access-section', key: 'legalResources.jumpNavQuickAccess', fallback: 'Quick Access' },
  { id: 'legal-resources-heading', key: 'legalResources.sectionResources', fallback: 'Legal Resources' },
  { id: 'legal-clinics-heading', key: 'legalResources.jumpNavClinics', fallback: 'Free Clinics' },
  { id: 'legal-forms-heading', key: 'legalResources.sectionForms', fallback: 'Common Forms' },
  { id: 'legal-privacy-heading', key: 'legalResources.jumpNavPrivacy', fallback: 'Online Privacy' },
  { id: 'legal-collections-section', key: 'legalResources.jumpNavCollections', fallback: 'Collections' },
] as const

function LegalJumpNav(): React.ReactElement {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  const handleJump = (id: string) => {
    const el = document.getElementById(id)
    if (!el) return
    el.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    el.focus({ preventScroll: true })
    setOpen(false)
  }

  return (
    <nav aria-label={t('aria.legalResources.pageSections', 'Page sections')} className="mb-6">
      {/* Mobile: collapsible */}
      <div className="sm:hidden">
        <button
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="w-full flex items-center justify-between px-4 py-2.5 bg-lsc-cream dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl text-sm font-medium text-lsc-dark dark:text-earth-50"
        >
          <span>{t('legalResources.onThisPage', 'On this page')}</span>
          <span aria-hidden="true" className={`transition-transform ${open ? 'rotate-180' : ''}`}>▾</span>
        </button>
        {open && (
          <ul className="mt-1 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden divide-y divide-lsc-border dark:divide-earth-700">
            {PAGE_SECTIONS.map(({ id, key, fallback }) => (
              <li key={id}>
                <button
                  onClick={() => handleJump(id)}
                  className="w-full text-left px-4 py-2.5 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
                >
                  {t(key, fallback)}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {/* Desktop: horizontal pill row */}
      <div className="hidden sm:flex flex-wrap gap-2" aria-label={t('aria.legalResources.jumpToSection', 'Jump to section')}>
        {PAGE_SECTIONS.map(({ id, key, fallback }) => (
          <button
            key={id}
            onClick={() => handleJump(id)}
            className="px-3 py-1.5 text-xs font-medium bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-cream/80 dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700 rounded-full transition-colors"
          >
            {t(key, fallback)}
          </button>
        ))}
      </div>
    </nav>
  )
}


export default function LegalResourcesPage(): React.ReactElement {
  const { t, language } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [jumpAnnouncement, setJumpAnnouncement] = useState('')
  const [guidesLimit, setGuidesLimit] = useState(6)
  const [activeCategory, setActiveCategory] = useState<number | null>(null)
  const [triageKey, setTriageKey] = useState(0)

  const { data: topicsData, isLoading: topicsLoading } = useQuery({
    queryKey: ['legal-topics', language],
    queryFn: () => getLegalTopics({ is_active: true, limit: 50 }, language),
  })

  const { data: guidesData, isLoading: guidesLoading } = useQuery({
    queryKey: ['legal-guides', activeCategory],
    queryFn: () => getLegalGuides({
      ...(activeCategory ? { topic_id: activeCategory } : {}),
      limit: 20,
    }),
  })

  const { data: formsData, isLoading: formsLoading } = useQuery({
    queryKey: ['legal-forms', searchQuery],
    queryFn: () => getLegalForms({
      ...(searchQuery ? { query: searchQuery } : {}),
      limit: 50,
    }),
  })

  const { data: clinicsData, isLoading: clinicsLoading } = useQuery({
    queryKey: ['legal-clinics-upcoming'],
    queryFn: () => getUpcomingLegalClinics({ days: 60, limit: 10 }),
  })

  const { data: providersData } = useQuery({
    queryKey: ['legal-providers'],
    queryFn: () => getLegalProviders({ is_active: true, limit: 20 }),
  })

  const { data: collectionsData, isLoading: collectionsLoading } = useQuery({
    queryKey: ['legal-collections-featured'],
    queryFn: () => getLegalCollections({ is_featured: true, limit: 10 }),
  })

  const topics = topicsData?.topics || []
  const guides = guidesData?.guides || []
  const forms = formsData?.forms || []
  const clinics = clinicsData || []
  const providers = providersData?.providers || []
  const collections = collectionsData?.collections || []

  // E2/E5 — Wizard jump semantics: scroll the matching section into
  // view, focus its <h2> (which is tabIndex=-1 for programmatic focus),
  // and announce via aria-live for screen-reader users. Mirrors the
  // /tech ?p= aria-live pattern.
  const handleJumpToSection = useCallback((section: string) => {
    if (!isSectionId(section)) return
    const heading = document.getElementById(`legal-${section}-heading`)
    if (!heading) return
    heading.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    heading.focus({ preventScroll: true })
    const { key, fallback } = JUMP_ANNOUNCEMENT_KEYS[section]
    setJumpAnnouncement(t(key, fallback))
  }, [t])

  return (
    <StandardPageLayout
      title={t('legalResources.pageTitle', 'Legal Help')}
      subtitle={t(
        'legalResources.pageSubtitle',
        'Free legal information, forms, and connections to legal aid — start with the questions below.',
      )}
      icon={Scale}
    >
      {/* Crosslink to policy pages */}
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
        {t('legalResources.lookingForLibraryPolicies', 'Looking for library policies?')}{' '}
        <a href="/privacy" className="text-lsc-rose hover:underline">{t('legalResources.policyPrivacy', 'Privacy')}</a>
        {' · '}
        <a href="/terms" className="text-lsc-rose hover:underline">{t('legalResources.policyTerms', 'Terms')}</a>
        {' · '}
        <a href="/accessibility" className="text-lsc-rose hover:underline">{t('footer.accessibility')}</a>
      </p>

      {/* Page-level last updated stamp — mirrors /privacy and /terms pattern */}
      <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mb-4">{t('legalResources.lastUpdatedStamp', 'Last updated June 2026')}</p>

      {/* Legal disclaimer banner — kept above the wizard so patrons see it
          before engaging with any legal content. I4: solid text tokens
          for AA contrast in both themes (was dark:text-lsc-rose-light/50,
          which is sub-AA on bg-lsc-dark/20). I2: max-w-prose clamps the
          block at ~65ch so it doesn't span 140ch at desktop widths. */}
      <div
        role="note"
        aria-label={t('aria.legalResources.legalDisclaimer')}
        className="bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-800 rounded-xl p-4 mb-6 max-w-prose"
      >
        <p className="text-sm text-lsc-dark dark:text-lsc-cream">
          <strong>{t('legalResources.disclaimerLabel', 'Disclaimer:')}</strong>{' '}
          {t(
            'legalResources.disclaimerText',
            'The information provided here is for general educational purposes only and does not constitute legal advice. For specific legal matters, please consult with a qualified attorney or legal aid service.',
          )}
        </p>
      </div>

      {/* E1: Sticky jump-nav */}
      <LegalJumpNav />

      {/* E5 — aria-live status region for wizard section-jumps. Always
          rendered (no conditional mount) so SRs can announce updates
          reliably; sr-only so it stays visually hidden. */}
      <div
        data-testid="legal-jump-announcement"
        role="status"
        aria-live="polite"
        className="sr-only"
      >
        {jumpAnnouncement}
      </div>

      <section id="legal-triage-section" aria-label={t('aria.legalResources.guidedJourneysSection', 'Guided Legal Journeys')} className="mb-6" tabIndex={-1}>
      <LegalTriageWizard
        key={triageKey}
        topics={topics}
        providers={providers}
        onSelectTopic={setActiveCategory}
        onJumpToSection={handleJumpToSection}
      />
        <div className="mt-4">
          <RestartTriageLink onRestart={() => setTriageKey((k) => k + 1)} />
        </div>
      </section>

      <section id="legal-quick-access-section" aria-label={t('aria.legalResources.quickAccessSection', 'Quick Access to Legal Help')} className="mb-6" tabIndex={-1}>
        <QuickAccessProviders providers={providers} />
      </section>

      <section id="legal-collections-section" aria-label={t('aria.legalResources.collectionsSection', 'Featured Legal Collections')} className="mb-6" tabIndex={-1}>
        <FeaturedCollections collections={collections} isLoading={collectionsLoading} />
      </section>

      {/* I1 — Always-visible stacked sections (no tabs). Ordering: Resources
          first because that's where the wizard most often routes patrons. */}
      <section
        aria-labelledby="legal-resources-heading"
        className="mb-10 pt-2"
        data-section-id={'resources' satisfies SectionId}
      >
        <h2
          id="legal-resources-heading"
          tabIndex={-1}
          className="font-serif text-xl font-semibold text-lsc-dark dark:text-earth-50 mb-4"
        >
          {t('legalResources.sectionResources', 'Legal Resources')}
        </h2>
        <ResourcesTab
          topics={topics}
          topicsLoading={topicsLoading}
          guides={guides}
          guidesLoading={guidesLoading}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          activeCategory={activeCategory}
          onActiveCategoryChange={setActiveCategory}
          guidesLimit={guidesLimit}
          onShowMore={() => setGuidesLimit((prev) => prev + 6)}
        />
      </section>

      <section
        aria-labelledby="legal-clinics-heading"
        className="mb-10 pt-2"
        data-section-id={'clinics' satisfies SectionId}
      >
        <h2
          id="legal-clinics-heading"
          tabIndex={-1}
          className="font-serif text-xl font-semibold text-lsc-dark dark:text-earth-50 mb-4"
        >
          {t('legalResources.sectionClinics', 'Free Legal Clinics')}
        </h2>
        <ClinicsTab clinics={clinics} isLoading={clinicsLoading} />
      </section>

      <section
        aria-labelledby="legal-forms-heading"
        className="mb-10 pt-2"
        data-section-id={'forms' satisfies SectionId}
      >
        <h2
          id="legal-forms-heading"
          tabIndex={-1}
          className="font-serif text-xl font-semibold text-lsc-dark dark:text-earth-50 mb-4"
        >
          {t('legalResources.sectionForms', 'Common Forms')}
        </h2>
        <FormsTab
          forms={forms}
          isLoading={formsLoading}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />
      </section>

      <section
        aria-labelledby="legal-privacy-heading"
        className="mb-10 pt-2"
        data-section-id={'privacy' satisfies SectionId}
      >
        <h2
          id="legal-privacy-heading"
          tabIndex={-1}
          className="font-serif text-xl font-semibold text-lsc-dark dark:text-earth-50 mb-4"
        >
          {t('legalResources.sectionPrivacy', 'Online Privacy & Removal')}
        </h2>
        <PrivacyTab />
      </section>
    </StandardPageLayout>
  )
}
