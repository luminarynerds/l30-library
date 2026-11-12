/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useMemo, useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Monitor,
  Wifi,
  Smartphone,
  Laptop,
  HelpCircle,
  Search,
  BookOpen,
} from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import {
  getUpcomingClasses,
  getTechHelpOptions,
  getQuickAccessSections,
  getTechResources,
  getTechFacilities,
  TechClass,
  TechHelpOption,
  QuickAccessSection,
  TechResource,
  TechFacilitySection,
} from '@/api/tech-support-api'
import { useTranslation } from '@/i18n'
import TriageTiles from '@/components/tech-support/TriageTiles'
import TalkToAPerson from '@/components/tech-support/TalkToAPerson'
import FacilitiesSection from '@/components/tech-support/FacilitiesSection'
import ClassesSection from '@/components/tech-support/ClassesSection'
import ExternalResourcesSection from '@/components/tech-support/ExternalResourcesSection'
import { GUIDES, findGuide } from '@/pages/guides/_data'

/**
 * QR triage params — fixed enum.
 *
 * Maps a generic service-desk / card-sleeve QR sticker (`/tech?p=…`)
 * to the matching triage tile guide id. Per-context stickers (e.g. one
 * AT the printer) link directly to /guides/* and bypass /tech.
 *
 * Add a value here only if there's a matching triage tile + guide.
 */
// Exported for the staff QR poster (/tech/poster) — keep this the single source of truth.
export const QR_PARAM_TO_GUIDE_ID = {
  password: 'password-reset',
  login: 'library-card',
  printer: 'check-print-jobs',
  wifi: 'wifi-troubleshooting',
} as const

export type QrParam = keyof typeof QR_PARAM_TO_GUIDE_ID

/** Aria-live announcement strings keyed off the validated `?p=` value. */
const QR_ANNOUNCEMENTS: Record<QrParam, string> = {
  password: 'Tech help for resetting your password — choose an option below.',
  login: 'Tech help for library card or login — choose an option below.',
  printer: 'Tech help for printing — choose an option below.',
  wifi: 'Tech help for WiFi — choose an option below.',
}

function parseQrParam(raw: string | null): QrParam | null {
  if (!raw) return null
  return raw in QR_PARAM_TO_GUIDE_ID ? (raw as QrParam) : null
}

const categories = [
  { id: 'basics', labelKey: 'techSupport.category.computerBasics', label: 'Computer Basics', icon: <Monitor aria-hidden="true" className="w-4 h-4" /> },
  { id: 'internet', labelKey: 'techSupport.category.internetAndEmail', label: 'Internet & Email', icon: <Wifi aria-hidden="true" className="w-4 h-4" /> },
  { id: 'mobile', labelKey: 'techSupport.category.smartphonesAndTablets', label: 'Smartphones & Tablets', icon: <Smartphone aria-hidden="true" className="w-4 h-4" /> },
  { id: 'safety', labelKey: 'techSupport.category.onlineSafety', label: 'Online Safety', icon: <HelpCircle aria-hidden="true" className="w-4 h-4" /> },
  { id: 'apps', labelKey: 'techSupport.category.productivityApps', label: 'Productivity Apps', icon: <Laptop aria-hidden="true" className="w-4 h-4" /> },
]

export default function TechSupportPage(): React.ReactElement {
  const { t, language } = useTranslation()
  const [searchParams] = useSearchParams()
  const qrParam = parseQrParam(searchParams.get('p'))
  const highlightGuideId = qrParam ? QR_PARAM_TO_GUIDE_ID[qrParam] : null

  const [searchQuery, setSearchQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [liveMessage, setLiveMessage] = useState('')

  const [upcomingClasses, setUpcomingClasses] = useState<TechClass[]>([])
  const [techHelpOptions, setTechHelpOptions] = useState<TechHelpOption[]>([])
  const [quickAccessSections, setQuickAccessSections] = useState<QuickAccessSection[]>([])
  const [techResources, setTechResources] = useState<TechResource[]>([])
  const [facilities, setFacilities] = useState<TechFacilitySection[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // E5 — Set the aria-live announcement post-mount so SRs reliably
  // pick it up (live regions present at first render are often ignored).
  useEffect(() => {
    if (qrParam) {
      setLiveMessage(QR_ANNOUNCEMENTS[qrParam])
    } else {
      setLiveMessage('')
    }
  }, [qrParam])

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)
        const [classes, helpOptions, sections, resources, fac] = await Promise.all([
          getUpcomingClasses(),
          getTechHelpOptions(language),
          getQuickAccessSections(),
          getTechResources(),
          getTechFacilities(),
        ])
        setUpcomingClasses(classes)
        setTechHelpOptions(helpOptions)
        setQuickAccessSections(sections)
        setTechResources(resources)
        setFacilities(fac)
      } catch (err: unknown) {
        setError('We had trouble loading some tech support information. Please try refreshing the page.')
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      } finally {
        setLoading(false)
      }
    }
    fetchData()
    // getTechHelpOptions returns Spanish-translated content when language
    // is 'es'; refetch on language change so the patron sees the switch.
  }, [language])

  const normalizedSearch = searchQuery.toLowerCase().trim()

  const filteredResources = techResources.filter((resource) => {
    const matchesCategory = !activeCategory || resource.category === activeCategory
    const matchesSearch =
      !normalizedSearch ||
      resource.title.toLowerCase().includes(normalizedSearch) ||
      resource.description.toLowerCase().includes(normalizedSearch)
    return matchesCategory && matchesSearch
  })

  // E4 — Merge matching /guides articles into the resources search.
  // Category chips remain resource-only (guides have a different taxonomy).
  // Match the lowercased localized title OR the stable guide id.
  const matchingGuides = useMemo(() => {
    if (!normalizedSearch) return []
    return GUIDES.filter((g) => {
      const title = t(g.titleKey).toLowerCase()
      return (
        title.includes(normalizedSearch) ||
        g.id.toLowerCase().includes(normalizedSearch)
      )
    })
  }, [normalizedSearch, t])

  return (
    <StandardPageLayout
      title={t('techSupport.pageTitle', 'Tech Help')}
      subtitle={t(
        'techSupport.pageSubtitle',
        'Common problems, fixed step-by-step. No appointment needed.',
      )}
      icon={Laptop}
      isLoading={loading}
    >
      {/* Error Alert */}
      {error && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/30 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-4 mb-6">
          <p className="text-status-danger-800 dark:text-status-danger-200">{error}</p>
        </div>
      )}

      {/* E5 — aria-live announcement for QR deep-link landings.
          Rendered only when ?p= resolved to a valid value, so the
          status node toggles in (post-mount via useEffect) and SRs
          reliably announce. Visually hidden via sr-only. */}
      {qrParam && (
        <div
          data-testid="tech-qr-announcement"
          role="status"
          aria-live="polite"
          className="sr-only"
        >
          {liveMessage}
        </div>
      )}

      {/* E1 — Triage tiles above the fold. E2: pass the resolved
          guide id so a QR-deep-link patron lands focus on the right tile. */}
      <TriageTiles highlightGuideId={highlightGuideId} />

      {/* I2 — Talk to a person block */}
      <TalkToAPerson options={techHelpOptions} />

      {/* Resources section (kept, moved out of tab) */}
      <section aria-labelledby="tech-resources-heading" className="mb-10">
        <h2
          id="tech-resources-heading"
          className="font-serif text-xl font-semibold text-lsc-dark dark:text-earth-50 mb-4"
        >
          {t('techSupport.resourcesHeading', 'Resources')}
        </h2>

        {/* Search */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 mb-4">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <input
                type="text"
                placeholder={t('placeholder.techSupport.searchTechResources')}
                aria-label={t('aria.techSupport.searchTechResources')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 min-h-[44px] border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Categories */}
        <div
          className="flex flex-wrap gap-2 mb-6"
          role="group"
          aria-label={t('aria.techSupport.filterByCategory')}
        >
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(activeCategory === cat.id ? null : cat.id)}
              aria-pressed={activeCategory === cat.id}
              className={`flex items-center gap-2 px-4 py-2 min-h-[44px] rounded-full border transition-colors ${
                activeCategory === cat.id
                  ? 'bg-lsc-rose text-white border-earth-600'
                  : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream/80 border-lsc-border dark:border-earth-700 hover:border-earth-400'
              }`}
            >
              {cat.icon}
              <span className="text-sm font-medium">{t(cat.labelKey, cat.label)}</span>
            </button>
          ))}
        </div>

        {/* E4 — Step-by-step guides subsection, only when the search box
            has content AND at least one guide matches. Renders above the
            DB resource cards so the most actionable result wins. */}
        {matchingGuides.length > 0 && (
          <div
            data-testid="tech-guides-results"
            className="mb-6"
            aria-labelledby="tech-guides-results-heading"
          >
            <h3
              id="tech-guides-results-heading"
              className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50 mb-3"
            >
              {t('techSupport.stepByStepGuidesHeading', 'Step-by-step guides')}
            </h3>
            <div className="grid md:grid-cols-2 gap-4">
              {matchingGuides.map((guide) => {
                const resolved = findGuide(guide.id)
                if (!resolved) return null
                return (
                  <Link
                    key={guide.id}
                    to={resolved.href}
                    data-guide-id={guide.id}
                    className="block bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 hover:border-lsc-rose/40 transition-colors"
                  >
                    <h4 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 mb-2">
                      {t(guide.titleKey)}
                    </h4>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                      {t(guide.descriptionKey)}
                    </p>
                    <div className="flex items-center justify-between text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span>{t('techSupport.stepByStepGuideLabel', 'Step-by-step guide')}</span>
                      <span>{t('techSupport.minutesLabel', '{{n}} min').replace('{{n}}', String(guide.estimatedMinutes))}</span>
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        )}

        {filteredResources.length > 0 ? (
          <div className="grid md:grid-cols-2 gap-4">
            {filteredResources.map((resource) => (
              <a
                key={resource.title}
                href={resource.href}
                className="block bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 hover:border-lsc-rose/40 transition-colors"
              >
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 mb-2">
                  {resource.title}
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                  {resource.description}
                </p>
                <div className="flex items-center justify-between text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <span>{resource.format}</span>
                  <span>{resource.duration}</span>
                </div>
              </a>
            ))}
          </div>
        ) : !error && matchingGuides.length === 0 ? (
          // I3: When `error` is set, suppress the "No tech resources found"
          // empty state — the top-of-page banner already explains the outage,
          // and "no resources" copy would make the failure look like deliberate
          // empty content.
          <div className="text-center py-12">
            <Monitor aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-3" />
            <h3 className="text-base font-medium text-lsc-dark dark:text-earth-50 mb-1">
              {t('techSupport.noResourcesFound', 'No tech resources found')}
            </h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('techSupport.tryAdjustingSearch', 'Try adjusting your search or filters.')}
            </p>
          </div>
        ) : null}
      </section>

      {/* I3: Skip per-section rendering on outage — the banner above is
          the single source of truth. These components return null on
          empty data anyway, but gating here documents the intent and is
          directly testable. */}
      {!error && (
        <>
          {/* I6 — Facilities from API */}
          <FacilitiesSection sections={facilities} />

          {/* I5 — Demoted Classes */}
          <ClassesSection classes={upcomingClasses} />

          {/* I5 — Demoted external resources */}
          <ExternalResourcesSection sections={quickAccessSections} />
        </>
      )}

      {/* Related Services */}
      <section
        aria-labelledby="related-services-heading"
        className="mt-12 pt-8 border-t border-lsc-border dark:border-earth-700"
      >
        <h2
          id="related-services-heading"
          className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 mb-4"
        >
          {t('techSupport.relatedServicesHeading', 'Related Services')}
        </h2>
        <div className="grid md:grid-cols-3 gap-4">
          <Link to="/wifi" className="block">
            <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5 hover:border-sage-400/60 dark:hover:border-sage-600/50 transition-colors">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-sage-100 dark:bg-sage-900/30 rounded-lg flex-shrink-0">
                  <Wifi aria-hidden="true" className="w-5 h-5 text-sage-700 dark:text-sage-400" />
                </div>
                <div>
                  <h3 className="font-medium text-lsc-dark dark:text-earth-50 mb-1">
                    {t('techSupport.freeWifiTitle', 'Free WiFi & Internet Access')}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('techSupport.freeWifiDescription', 'Connect to free WiFi throughout the library. Get connection details, hotspot lending info, and more.')}
                  </p>
                </div>
              </div>
            </div>
          </Link>
          <Link to="/guides" className="block">
            <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5 hover:border-sage-400/60 dark:hover:border-sage-600/50 transition-colors">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-sage-100 dark:bg-sage-900/30 rounded-lg flex-shrink-0">
                  <BookOpen aria-hidden="true" className="w-5 h-5 text-sage-700 dark:text-sage-400" />
                </div>
                <div>
                  <h3 className="font-medium text-lsc-dark dark:text-earth-50 mb-1">
                    {t('techSupport.selfServiceGuidesTitle', 'Self-Service Tech Guides')}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('techSupport.selfServiceGuidesDescription', 'Step-by-step guides for passwords, printing, email setup, and common tech tasks.')}
                  </p>
                </div>
              </div>
            </div>
          </Link>
          <Link to="/digital" className="block">
            <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5 hover:border-sage-400/60 dark:hover:border-sage-600/50 transition-colors">
              <div className="flex items-start gap-4">
                <div className="p-2 bg-sage-100 dark:bg-sage-900/30 rounded-lg flex-shrink-0">
                  <Monitor aria-hidden="true" className="w-5 h-5 text-sage-700 dark:text-sage-400" />
                </div>
                <div>
                  <h3 className="font-medium text-lsc-dark dark:text-earth-50 mb-1">
                    {t('techSupport.digitalResourcesTitle', 'Digital Resources & eBooks')}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('techSupport.digitalResourcesDescription', 'Access eBooks, databases, streaming services, and other digital resources with your library card.')}
                  </p>
                </div>
              </div>
            </div>
          </Link>
        </div>
      </section>
    </StandardPageLayout>
  )
}
