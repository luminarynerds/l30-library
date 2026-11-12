/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * TeacherHomePage — landing hub at /teacher that surfaces all six teacher
 * surfaces as link-cards. Previously /teacher redirected to
 * /teacher/reading-dashboard, which obscured the rest of the area. This
 * page restores discoverability.
 *
 * v1 is intentionally static — no live data, just cards. Counts/badges
 * (e.g. "3 pending requests") are a v2 follow-up.
 */
import type React from 'react'
import { Link } from 'react-router-dom'
import {
  BookOpenCheck,
  ListChecks,
  Award,
  MessageCircleQuestion,
  Users,
  Calendar,
  GraduationCap,
} from 'lucide-react'
import { useTranslation } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

interface TeacherCard {
  to: string
  icon: React.ElementType
  labelKey: string
  descKey: string
}

const CARDS: readonly TeacherCard[] = [
  {
    to: '/teacher/reading-dashboard',
    icon: BookOpenCheck,
    labelKey: 'navigation.teacherReadingDashboard',
    descKey: 'navigation.teacherReadingDashboardDesc',
  },
  {
    to: '/teacher/reading-lists',
    icon: ListChecks,
    labelKey: 'navigation.teacherReadingLists',
    descKey: 'navigation.teacherReadingListsDesc',
  },
  {
    to: '/teacher/professional-development',
    icon: Award,
    labelKey: 'navigation.professionalDevelopment',
    descKey: 'navigation.professionalDevelopmentDesc',
  },
  {
    to: '/teacher/library-consultations',
    icon: MessageCircleQuestion,
    labelKey: 'navigation.librarianConsultations',
    descKey: 'navigation.librarianConsultationsDesc',
  },
  {
    to: '/teacher/family-challenges',
    icon: Users,
    labelKey: 'navigation.familyReadingChallenges',
    descKey: 'navigation.familyReadingChallengesDesc',
  },
  {
    to: '/teacher/library-visits',
    icon: Calendar,
    labelKey: 'navigation.libraryVisitScheduling',
    descKey: 'navigation.libraryVisitSchedulingDesc',
  },
]

export default function TeacherHomePage(): React.ReactElement {
  const { t } = useTranslation()

  return (
    <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark">
      {/* Page header */}
      <div className="bg-lsc-white dark:bg-earth-950 border-b border-lsc-dark/10 dark:border-lsc-cream/10">
        <PageContainer width="wide" className="py-8">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-education-primary/10 rounded-lg">
              <GraduationCap
                className="w-8 h-8 text-education-primary"
                aria-hidden="true"
              />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                {t('teacherHome.title')}
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                {t('teacherHome.subtitle')}
              </p>
            </div>
          </div>
        </PageContainer>
      </div>

      {/* Cards grid */}
      <PageContainer width="wide" className="py-8">
        <ul
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          aria-label={t('teacherHome.title')}
        >
          {CARDS.map((card) => {
            const Icon = card.icon
            return (
              <li key={card.to}>
                <Link
                  to={card.to}
                  className="block h-full bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-dark/10 dark:border-lsc-cream/10 shadow-sm p-6 hover:border-education-primary/40 hover:shadow-md transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-education-primary"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-education-primary/10 rounded-lg shrink-0">
                      <Icon
                        className="w-6 h-6 text-education-primary"
                        aria-hidden="true"
                      />
                    </div>
                    <div className="min-w-0">
                      <h2 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                        {t(card.labelKey)}
                      </h2>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {t(card.descKey)}
                      </p>
                    </div>
                  </div>
                </Link>
              </li>
            )
          })}
        </ul>
      </PageContainer>
    </div>
  )
}
