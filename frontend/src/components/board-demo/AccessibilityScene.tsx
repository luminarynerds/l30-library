/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Eye, Volume2, Keyboard, RefreshCw, CheckCircle2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { AnimatedCounter, StaggeredList } from './DemoAnimations'

export function AccessibilityScene() {
  const { t } = useTranslation()
  return (
    <div className="space-y-6">
      <div className="bg-teal-50 dark:bg-teal-950/20 rounded-xl p-6 border border-teal-200 dark:border-teal-800">
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 bg-teal-100 dark:bg-teal-900/50 rounded-full flex items-center justify-center shrink-0">
            <Eye className="w-7 h-7 text-teal-600" />
          </div>
          <div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{t('boardDemo.margaretAposSStory')}</h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Margaret, 74, is legally blind. Before L30, she couldn&apos;t use any library website independently.
              Now she searches the catalog, places holds, and manages her account&mdash;all with a screen reader.
            </p>
            <blockquote className="mt-3 pl-4 border-l-3 border-teal-400 italic text-lsc-dark/70 dark:text-lsc-cream/70">
              &ldquo;This is the first library website I can actually use on my own. I don&apos;t need to call and ask someone to look things up for me anymore.&rdquo;
            </blockquote>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <StaggeredList staggerMs={120}>
          {[
            { title: 'Screen Reader Support', detail: 'ARIA labels, live regions, semantic HTML throughout', icon: Volume2, status: 'WCAG 2.1 AA' },
            { title: 'Keyboard Navigation', detail: 'Every feature accessible without a mouse', icon: Keyboard, status: 'Full Coverage' },
            { title: 'High Contrast Mode', detail: 'Toggle in user preferences, persisted across sessions', icon: Eye, status: 'Built In' },
            { title: 'Reduced Motion', detail: 'Respects prefers-reduced-motion, no forced animations', icon: RefreshCw, status: 'Automatic' },
          ].map((f) => (
            <div key={f.title} className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700 hover:shadow-md hover:-translate-y-0.5 transition-all">
              <div className="flex items-center gap-2 mb-2">
                <f.icon className="w-4 h-4 text-teal-600" />
                <h4 className="font-medium text-lsc-dark dark:text-lsc-cream text-sm">{f.title}</h4>
              </div>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{f.detail}</p>
              <span className="inline-flex items-center gap-1 text-xs font-medium text-teal-700 dark:text-teal-400 bg-teal-50 dark:bg-teal-900/20 px-2 py-0.5 rounded-full">
                <CheckCircle2 className="w-3 h-3" /> {f.status}
              </span>
            </div>
          ))}
        </StaggeredList>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
        <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-status-success-500" />
          Automated Accessibility Testing
        </h4>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-3xl font-bold text-status-success-600"><AnimatedCounter end={100} suffix="%" /></div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Pages passing axe-core</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-status-success-600"><AnimatedCounter end={247} /></div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('boardDemo.aYTestsPerBuild')}</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-status-success-600"><AnimatedCounter end={0} /></div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Critical violations</div>
          </div>
        </div>
      </div>
    </div>
  )
}
