/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  HelpCircle,
  Briefcase,
  MapPin,
  Monitor,
  Baby,
  Heart,
  Building2,
  ChevronDown,
  Phone,
  ArrowRight,
  Users,
  ExternalLink,
} from 'lucide-react'
import { useBranding } from '@/contexts/BrandingContext'
import StandardPageLayout from '@/components/StandardPageLayout'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useCommunityResources } from '@/hooks/useCommunityResources'

interface Situation {
  id: string
  title: string
  icon: React.ReactNode
  color: string
  links: { label: string; to: string; description: string }[]
}

interface CommunityQuickLink {
  name: string
  url: string
}

interface CommunityQuickSection {
  title: string
  icon: React.ReactNode
  links: CommunityQuickLink[]
}

const hardcodedQuickAccess: CommunityQuickSection[] = [
  {
    title: 'Family Services',
    icon: <Baby aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />,
    links: [
      { name: 'Parent Mentors Program', url: '/parent-mentors' },
    ],
  },
]

const situations: Situation[] = [
  {
    id: 'job-loss',
    title: 'I Lost My Job',
    icon: <Briefcase aria-hidden="true" className="w-6 h-6" />,
    color: 'text-status-info-600 dark:text-status-info-400 bg-status-info-50 dark:bg-status-info-900/20',
    links: [
      { label: 'Career Services & Resume Help', to: '/business?tab=career', description: 'Free resume reviews, interview prep, and job search strategies' },
      { label: 'Free Computer & WiFi Access', to: '/tech', description: 'Use library computers for job applications and email' },
      { label: 'Financial Wellness Coaching', to: '#community', description: 'Free budgeting help and benefits enrollment' },
      { label: 'Community Resources', to: '#community', description: 'Food assistance, housing support, and more' },
    ],
  },
  {
    id: 'new-to-town',
    title: "I'm New to Town",
    icon: <MapPin aria-hidden="true" className="w-6 h-6" />,
    color: 'text-status-success-600 dark:text-status-success-400 bg-status-success-50 dark:bg-status-success-900/20',
    links: [
      { label: 'Get a Library Card', to: '/card-application', description: 'Free for all residents - just bring an ID and proof of address' },
      { label: 'Community Resources Directory', to: '#community', description: 'Find local services, organizations, and support' },
      { label: 'Events & Programs', to: '/events', description: 'Meet people at book clubs, classes, and community events' },
      { label: 'Tech Support & WiFi', to: '/tech', description: 'Free WiFi, computer access, and tech help' },
    ],
  },
  {
    id: 'senior-tech',
    title: 'I Need Tech Help (Seniors)',
    icon: <Monitor aria-hidden="true" className="w-6 h-6" />,
    color: 'text-category-600 dark:text-category-400 bg-category-50 dark:bg-category-900/20',
    links: [
      { label: 'Tech Classes & Workshops', to: '/tech', description: 'Free beginner-friendly classes on computers, phones, and email' },
      { label: 'Drop-In Tech Help', to: '/tech', description: 'One-on-one help with your device, no appointment needed' },
      { label: 'Accessibility Settings', to: '/accessibility', description: 'Large text, high contrast, and reading assistance tools' },
      { label: 'Self-Service Tech Guides', to: '/guides', description: 'Step-by-step guides for common tasks like WiFi and printing' },
    ],
  },
  {
    id: 'new-parent',
    title: "I'm a New Parent",
    icon: <Baby aria-hidden="true" className="w-6 h-6" />,
    color: 'text-pink-600 dark:text-pink-400 bg-pink-50 dark:bg-pink-900/20',
    links: [
      { label: "Children's Programs & Storytime", to: '/youth', description: 'Weekly storytime, crafts, and early literacy activities' },
      { label: 'Parenting Resources', to: '#community', description: 'Books, guides, and community support for new parents' },
      { label: 'Family Reading Challenges', to: '/reading-challenge', description: 'Fun reading goals for the whole family' },
      { label: 'Community Family Services', to: '#community', description: 'Childcare resources, parenting programs, and support groups' },
    ],
  },
  {
    id: 'hardship',
    title: "I'm Experiencing Hardship",
    icon: <Heart aria-hidden="true" className="w-6 h-6" />,
    color: 'text-status-danger-600 dark:text-status-danger-400 bg-status-danger-50 dark:bg-status-danger-900/20',
    links: [
      { label: 'Food Assistance', to: '#community', description: 'Local food banks, community kitchens, and meal programs' },
      { label: 'Housing & Shelter Info', to: '#community', description: 'Emergency shelter, affordable housing, and rent assistance' },
      { label: 'Financial Help & Benefits', to: '#community', description: 'Free financial coaching and benefits enrollment assistance' },
      { label: 'Crisis Support Lines', to: '/contact', description: 'Call 211 for services, 988 for crisis support, 911 for emergencies' },
    ],
  },
  {
    id: 'business',
    title: "I'm Starting a Business",
    icon: <Building2 aria-hidden="true" className="w-6 h-6" />,
    color: 'text-status-warning-600 dark:text-status-warning-400 bg-status-warning-50 dark:bg-status-warning-900/20',
    links: [
      { label: 'Business Resources & Databases', to: '/business', description: 'Free access to market research, business planning tools, and databases' },
      { label: 'Meeting Rooms', to: '/rooms', description: 'Free meeting rooms for non-profit groups, affordable for businesses' },
      { label: 'Technology & Printing', to: '/tech', description: 'Computers, WiFi, printing, and scanning for your business needs' },
      { label: 'Networking Events', to: '/events', description: 'Connect with other entrepreneurs and community leaders' },
    ],
  },
]

export default function LifeSituationsPage(): React.ReactElement {
  const branding = useBranding()
  usePageTitle('Life Situations Guide')
  const { data: dbCategories = [] } = useCommunityResources('life_situations')
  const [openSituation, setOpenSituation] = useState<string | null>(null)
  const location = useLocation()

  const toggleSituation = (id: string) => {
    setOpenSituation(openSituation === id ? null : id)
  }

  // Scroll to #community anchor when arriving from redirect
  useEffect(() => {
    if (location.hash === '#community') {
      // Small delay to let the page render
      const timer = setTimeout(() => {
        const el = document.getElementById('community')
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [location.hash])

  // Handle anchor links within the same page
  const handleLinkClick = (to: string) => {
    if (to === '#community') {
      const el = document.getElementById('community')
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }
  }

  return (
    <StandardPageLayout
      title="How Can We Help?"
      subtitle="Whatever you're going through, the library has resources for you. Click a situation below to find what you need."
      icon={HelpCircle}
    >
      <div className="space-y-4">
        {situations.map((situation) => (
          <div
            key={situation.id}
            className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden"
          >
            <button
              onClick={() => toggleSituation(situation.id)}
              aria-expanded={openSituation === situation.id}
              className="w-full flex items-center justify-between gap-4 p-5 text-left hover:bg-lsc-cream/50 dark:hover:bg-earth-800/50 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl ${situation.color}`}>
                  {situation.icon}
                </div>
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  {situation.title}
                </h2>
              </div>
              <ChevronDown
                className={`w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/50 transition-transform ${
                  openSituation === situation.id ? 'rotate-180' : ''
                }`}
                aria-hidden="true"
              />
            </button>

            {openSituation === situation.id && (
              <div className="px-5 pb-5 border-t border-lsc-border dark:border-earth-700">
                <div className="grid sm:grid-cols-2 gap-3 pt-4">
                  {situation.links.map(({ label, to, description }) => (
                    <Link
                      key={label}
                      to={to}
                      onClick={() => handleLinkClick(to)}
                      className="flex items-start gap-3 p-4 rounded-xl bg-lsc-cream/50 dark:bg-earth-800/30 hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors group"
                    >
                      <ArrowRight
                        aria-hidden="true"
                        className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5 group-hover:translate-x-0.5 transition-transform"
                      />
                      <div>
                        <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">
                          {label}
                        </span>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">
                          {description}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>

                <div className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-700">
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-2">
                    <Phone aria-hidden="true" className="w-4 h-4" />
                    Not sure where to start? Call us at{' '}
                    {branding.phone && <a href={`tel:${branding.phone.replace(/\D/g, '')}`} className="text-lsc-rose dark:text-lsc-rose-light font-medium hover:underline">
                      {branding.phone}
                    </a>}
                  </p>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Community Resources Section */}
      <div id="community" className="mt-12 scroll-mt-24">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 rounded-xl text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-900/20">
            <Users aria-hidden="true" className="w-6 h-6" />
          </div>
          <div>
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
              Community Resources
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
              Food, housing, health, jobs, and family services — all free, no judgment.
            </p>
          </div>
        </div>

        {/* Crisis Help Banner */}
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6 mb-6">
          <h3 className="font-serif font-semibold text-status-danger-800 dark:text-status-danger-200 mb-2">Need Immediate Help?</h3>
          <p className="text-status-danger-700 dark:text-status-danger-300 text-sm mb-4">
            You don&apos;t need to explain. You don&apos;t need an appointment. Just call.
          </p>
          <div className="flex flex-wrap gap-4">
            <a
              href="tel:211"
              className="inline-flex items-center gap-2 px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-xl text-sm font-medium transition-colors"
            >
              <Phone aria-hidden="true" className="w-4 h-4" />
              Call 211 for Community Services
            </a>
            <a
              href="tel:988"
              className="inline-flex items-center gap-2 px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-xl text-sm font-medium transition-colors"
            >
              <Phone aria-hidden="true" className="w-4 h-4" />
              988 Crisis Line
            </a>
          </div>
        </div>

        {/* Quick Access Resource Cards */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {dbCategories.map((category) => (
            <div
              key={category.category}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700"
            >
              <div className="flex items-center gap-2 mb-3">
                <h3 className="font-medium text-lsc-dark dark:text-earth-50">{category.title}</h3>
              </div>
              <ul className="space-y-2">
                {category.links.map((link) => (
                  <li key={link.name}>
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:hover:text-lsc-rose flex items-center gap-1"
                    >
                      {link.name}
                      <ExternalLink aria-hidden="true" className="w-3 h-3" />
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {hardcodedQuickAccess.map((section) => (
            <div
              key={section.title}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700"
            >
              <div className="flex items-center gap-2 mb-3">
                {section.icon}
                <h3 className="font-medium text-lsc-dark dark:text-earth-50">{section.title}</h3>
              </div>
              <ul className="space-y-2">
                {section.links.map((link) => (
                  <li key={link.name}>
                    <a
                      href={link.url}
                      className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:hover:text-lsc-rose flex items-center gap-1"
                    >
                      {link.name}
                      <ExternalLink aria-hidden="true" className="w-3 h-3" />
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="mt-8 bg-lsc-cream dark:bg-earth-800/20 rounded-xl p-6 text-center">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Don&apos;t see your situation? We can still help.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/ask-librarian"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl text-sm font-medium transition-colors"
          >
            Chat with a Librarian
          </Link>
          {branding.phone && <a
            href={`tel:${branding.phone.replace(/\D/g, '')}`}
            className="inline-flex items-center gap-2 px-5 py-2.5 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl text-sm font-medium hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
          >
            <Phone aria-hidden="true" className="w-4 h-4" />
            Call {branding.phone}
          </a>}
        </div>
      </div>
    </StandardPageLayout>
  )
}
