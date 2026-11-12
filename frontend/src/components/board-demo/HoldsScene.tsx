/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Search, BookOpen, CheckCircle2, Volume2, RefreshCw } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { AnimatedCounter } from './DemoAnimations'

export function HoldsScene() {
  const { t } = useTranslation()
  const [holdStep, setHoldStep] = useState(0)
  const holdSteps = [
    { label: 'Staff searches patron', detail: 'Type "Rodriguez" \u2192 instant match', icon: Search },
    { label: 'Select title', detail: '"Lessons in Chemistry" by Bonnie Garmus', icon: BookOpen },
    { label: 'Hold placed', detail: 'Position #3 in queue \u2014 est. 2 weeks', icon: CheckCircle2 },
    { label: 'Patron notified', detail: 'SMS sent: "Hold placed! We\'ll let you know."', icon: Volume2 },
  ]

  useEffect(() => {
    if (holdStep >= holdSteps.length - 1) return
    const timer = setTimeout(() => setHoldStep((s) => s + 1), 1500)
    return () => clearTimeout(timer)
  }, [holdStep, holdSteps.length])

  return (
    <div className="space-y-6">
      <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Hold Placement Workflow</h3>

      <div className="relative">
        {holdSteps.map((s, i) => (
          <div
            key={i}
            className={`flex items-start gap-4 p-4 rounded-lg mb-3 transition-all duration-500 ${
              i <= holdStep
                ? 'bg-violet-50 dark:bg-violet-950/30 border border-violet-200 dark:border-violet-800'
                : 'bg-earth-50 dark:bg-earth-800/50 border border-lsc-border dark:border-earth-700 opacity-40'
            }`}
          >
            <div className={`p-2 rounded-full shrink-0 ${
              i <= holdStep ? 'bg-violet-100 dark:bg-violet-900/50' : 'bg-earth-100 dark:bg-earth-700'
            }`}>
              <s.icon className={`w-5 h-5 ${i <= holdStep ? 'text-violet-600 dark:text-violet-400' : 'text-earth-600'}`} />
            </div>
            <div>
              <div className={`font-medium ${i <= holdStep ? 'text-lsc-dark dark:text-lsc-cream' : 'text-earth-600'}`}>
                {s.label}
              </div>
              <div className={`text-sm ${i <= holdStep ? 'text-lsc-dark/70 dark:text-lsc-cream/70' : 'text-earth-600'}`}>
                {s.detail}
              </div>
            </div>
            {i <= holdStep && i < holdStep && (
              <CheckCircle2 className="w-5 h-5 text-status-success-500 ml-auto shrink-0 mt-1" />
            )}
            {i === holdStep && i < holdSteps.length - 1 && (
              <RefreshCw className="w-4 h-4 text-violet-500 ml-auto shrink-0 mt-1 motion-safe:animate-spin" />
            )}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
          <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">Hold Queue Intelligence</h4>
          <ul className="space-y-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-status-success-500 shrink-0" /> {t('boardDemo.autoExpirationAfterDaysOn')}</li>
            <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-status-success-500 shrink-0" /> {t('boardDemo.multiChannelNotificationsSmsEmail')}</li>
            <li className="flex items-center gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-status-success-500 shrink-0" /> {t('boardDemo.suspendHoldsForVacation')}</li>
          </ul>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
          <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">This Month</h4>
          <div className="space-y-3">
            <div>
              <div className="text-2xl font-bold text-violet-600">
                <AnimatedCounter end={342} />
              </div>
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Holds placed</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-status-success-600">
                <AnimatedCounter end={89} suffix="%" />
              </div>
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Fulfilled within estimate</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
