/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { Building2, ExternalLink, ArrowRight, BookOpen, Monitor, Users } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useCommunityResources } from '@/hooks/useCommunityResources'

const federalResources = [
  { name: 'Small Business Administration (SBA)', url: 'https://www.sba.gov', description: 'Loans, grants, and business development resources' },
  { name: 'SCORE Mentoring', url: 'https://www.score.org', description: 'Free mentoring from experienced business professionals' },
  { name: 'Grants.gov', url: 'https://www.grants.gov', description: 'Federal grant opportunities for businesses and nonprofits' },
]

const libraryResources = [
  { label: 'Business Databases & Research', to: '/databases', description: 'IBISWorld, Business Source Complete, ReferenceUSA and more' },
  { label: 'Meeting Rooms', to: '/rooms', description: 'Free for nonprofits, affordable for businesses' },
  { label: 'Technology & Printing', to: '/tech', description: 'Computers, WiFi, printing, and scanning' },
  { label: 'Career Services', to: '/business?tab=career', description: 'Resume reviews, interview prep, and job search tools' },
]

export default function BusinessResourcesPage(): React.ReactElement {
  const { data: categories = [], isLoading } = useCommunityResources('business')

  return (
    <StandardPageLayout
      title="Business Resources"
      subtitle="Tools, databases, and local support for entrepreneurs, job seekers, and small businesses — all free with your library card."
      icon={Building2}
    >
      {/* Library resources — always shown, real internal links */}
      <section className="mb-10">
        <div className="flex items-center gap-3 mb-5">
          <div className="p-3 rounded-xl text-lsc-rose bg-lsc-rose/10">
            <BookOpen aria-hidden="true" className="w-6 h-6" />
          </div>
          <div>
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Library Services</h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Free with your library card</p>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          {libraryResources.map(({ label, to, description }) => (
            <Link
              key={label}
              to={to}
              className="flex items-start gap-3 p-4 rounded-xl bg-lsc-cream/50 dark:bg-earth-800/30 hover:bg-lsc-cream dark:hover:bg-earth-700 border border-lsc-border dark:border-earth-700 transition-colors group"
            >
              <ArrowRight
                aria-hidden="true"
                className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5 group-hover:translate-x-0.5 transition-transform"
              />
              <div>
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">
                  {label}
                </span>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">{description}</p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Dynamic local/regional resources */}
      {!isLoading && categories.length > 0 && (
        <section className="mb-10">
          <div className="flex items-center gap-3 mb-5">
            <div className="p-3 rounded-xl text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-900/20">
              <Users aria-hidden="true" className="w-6 h-6" />
            </div>
            <div>
              <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Local & Regional Resources</h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Organizations and programs in your area</p>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {categories.map((category) => (
              <div
                key={category.category}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700"
              >
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-3">{category.title}</h3>
                <ul className="space-y-2">
                  {category.links.map((link) => (
                    <li key={link.name}>
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline flex items-center gap-1"
                      >
                        {link.name}
                        <ExternalLink aria-hidden="true" className="w-3 h-3 flex-shrink-0" />
                      </a>
                      {link.description && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">{link.description}</p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Federal resources — always shown, real URLs */}
      <section>
        <div className="flex items-center gap-3 mb-5">
          <div className="p-3 rounded-xl text-status-info-600 dark:text-status-info-400 bg-status-info-50 dark:bg-status-info-900/20">
            <Monitor aria-hidden="true" className="w-6 h-6" />
          </div>
          <div>
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Federal Resources</h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">National programs available to all businesses</p>
          </div>
        </div>
        <div className="grid sm:grid-cols-3 gap-4">
          {federalResources.map((resource) => (
            <a
              key={resource.name}
              href={resource.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex flex-col gap-2 p-5 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors group"
            >
              <span className="font-medium text-lsc-dark dark:text-earth-50 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors flex items-center gap-1">
                {resource.name}
                <ExternalLink aria-hidden="true" className="w-3 h-3 flex-shrink-0" />
              </span>
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{resource.description}</span>
            </a>
          ))}
        </div>
      </section>

      {/* CTA */}
      <div className="mt-10 bg-lsc-cream dark:bg-earth-800/20 rounded-xl p-6 text-center">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Have a specific question? A librarian can help you find what you need.
        </p>
        <Link
          to="/contact"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl text-sm font-medium transition-colors"
        >
          Contact Us
        </Link>
      </div>
    </StandardPageLayout>
  )
}
