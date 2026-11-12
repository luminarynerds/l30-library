/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Users, TrendingUp, Star, Clock } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'
import { AnimatedCounter, StaggeredList } from './DemoAnimations'
import { SCENES } from './board-demo-data'

export function WelcomeScene() {
  const branding = useBranding()
  const { t } = useTranslation()
  return (
    <div className="space-y-8">
      <div className="text-center space-y-4">
        <h2 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream">
          {branding.product_name} System
        </h2>
        <p className="text-xl text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mx-auto">
          A modern library platform built for our community&mdash;by people who understand what a small town library means.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
        <StaggeredList staggerMs={120}>
          {[
            { label: 'Active Patrons', value: 2847, icon: Users, color: 'text-lsc-rose dark:text-lsc-rose-light' },
            { label: 'Items in Collection', value: 31450, icon: BookOpen, color: 'text-emerald-600' },
            { label: 'Checkouts This Year', value: 48293, icon: TrendingUp, color: 'text-status-warning-600' },
            { label: 'Programs Run', value: 186, icon: Star, color: 'text-violet-600' },
          ].map((stat) => (
            <div key={stat.label} className="text-center p-4 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 hover:shadow-md hover:-translate-y-0.5 transition-all">
              <stat.icon className={`w-6 h-6 ${stat.color} mx-auto mb-2`} />
              <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                <AnimatedCounter end={stat.value} />
              </div>
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{stat.label}</div>
            </div>
          ))}
        </StaggeredList>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 max-w-2xl mx-auto">
        <div className="flex items-start gap-3">
          <Clock className="w-5 h-5 text-lsc-rose mt-0.5 shrink-0" />
          <div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('boardDemo.todayAposSAgendaMinutes')}</h3>
            <div className="mt-3 space-y-2">
              {SCENES.slice(1).map((scene) => (
                <div key={scene.id} className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <scene.icon className={`w-4 h-4 ${scene.color} shrink-0`} />
                  <span>{scene.title}</span>
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70 ml-auto">{scene.durationMinutes} min</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
