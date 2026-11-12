/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Users,
  AlertCircle,
  Info,
  Mail,
} from 'lucide-react'
import YouthSubNav from '@/pages/youth/YouthSubNav'
import PageContainer from '@/components/layout/PageContainer'

export default function YouthTeenMentorsPage(): React.ReactElement {
  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <YouthSubNav />
      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <PageContainer className="py-8">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <Users aria-hidden="true" className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-earth-50">
                Teen Tech Mentors
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                Connect with experienced teen mentors or become a mentor yourself
              </p>
            </div>
          </div>
        </PageContainer>
      </div>

      <PageContainer className="py-8">
        {/* Info Banner */}
        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-6 mb-8">
          <div className="flex gap-3">
            <AlertCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-earth-800 dark:text-lsc-rose-light text-sm mb-3">
                Our Teen Tech Mentors program pairs you with experienced youth mentors in tech and STEM fields. Get personalized guidance, build projects together, and grow your skills!
              </p>
              <p className="text-earth-800 dark:text-lsc-rose-light text-sm">
                Interested in mentoring others? Apply to become a mentor and earn volunteer hours!
              </p>
            </div>
          </div>
        </div>

        {/* Coming Soon Card */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-12 border border-lsc-border dark:border-earth-700 text-center max-w-2xl mx-auto">
          <Info aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-rose dark:text-lsc-rose-light mb-4" />
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-earth-50 mb-4">
            Teen Tech Mentors -- Coming Soon
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-8 max-w-lg mx-auto">
            We are developing a mentorship program where teens can share their tech skills with younger students and earn volunteer hours. Applications, mentor matching, and hour logging are all in the works.
          </p>
          <a
            href="mailto:library@l30.org?subject=Teen%20Tech%20Mentors%20-%20Notify%20Me"
            className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-semibold transition-colors"
          >
            <Mail aria-hidden="true" className="w-5 h-5" />
            Get notified when we launch
          </a>
        </div>
      </PageContainer>
    </div>
  )
}
