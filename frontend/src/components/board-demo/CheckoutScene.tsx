/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import {
  UserCheck, CreditCard, BookOpen, CheckCircle2,
  Timer, BarChart3, Monitor, Pause, Play,
} from 'lucide-react'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'

export function CheckoutScene() {
  const { settings } = useAccessibility()
  const [step, setStep] = useState(0)
  const [autoPlay, setAutoPlay] = useState(!settings.reduceMotion)

  const timeline = [
    { time: '0.0s', action: 'Patron approaches desk', result: 'Staff clicks checkout field \u2014 auto-focused', icon: UserCheck },
    { time: '0.8s', action: 'Library card scanned', result: 'Patron identified: Maria Santos \u2014 Active, no blocks', icon: CreditCard },
    { time: '1.5s', action: 'First book scanned', result: '"The House in the Cerulean Sea" \u2014 Due Mar 13', icon: BookOpen },
    { time: '2.3s', action: 'Second book scanned', result: '"Piranesi" \u2014 Due Mar 13', icon: BookOpen },
    { time: '3.1s', action: 'Third book scanned', result: '"Klara and the Sun" \u2014 Due Mar 13', icon: BookOpen },
    { time: '4.0s', action: 'Receipt printed', result: '3 items checked out. Total time: 4 seconds.', icon: CheckCircle2 },
  ]

  useEffect(() => {
    if (!autoPlay) return
    if (step >= timeline.length - 1) return
    const timer = setTimeout(() => setStep((s) => s + 1), 1200)
    return () => clearTimeout(timer)
  }, [step, autoPlay, timeline.length])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Live Checkout Simulation</h3>
        <button
          onClick={() => { setAutoPlay(!autoPlay); if (!autoPlay && step >= timeline.length - 1) setStep(0) }}
          aria-label={autoPlay ? 'Pause demo animation' : 'Replay demo animation'}
          className="flex items-center gap-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
        >
          {autoPlay ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          {autoPlay ? 'Pause' : 'Replay'}
        </button>
      </div>

      <div className="bg-earth-900 dark:bg-earth-950 rounded-xl p-6 font-mono text-sm border-2 border-earth-700">
        <div className="flex items-center gap-2 mb-4 pb-3 border-b border-earth-700">
          <div className="w-3 h-3 rounded-full bg-status-danger-500" />
          <div className="w-3 h-3 rounded-full bg-status-warning-500" />
          <div className="w-3 h-3 rounded-full bg-status-success-500" />
          <span className="text-earth-600 text-xs ml-2">L30 Circulation Terminal</span>
        </div>
        <div className="space-y-1.5 min-h-[180px]">
          {timeline.slice(0, step + 1).map((event, i) => (
            <div
              key={i}
              className={`flex items-start gap-2 transition-all duration-300 ${i === step ? 'text-status-success-400' : 'text-earth-600'}`}
            >
              <span className="text-earth-600 dark:text-earth-200 w-10 shrink-0">{event.time}</span>
              <span className="text-earth-600">&gt;</span>
              <span>{event.result}</span>
            </div>
          ))}
          {step < timeline.length - 1 && (
            <span className="inline-block w-2 h-4 bg-status-success-400 motion-safe:animate-pulse" />
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Avg Checkout Time', value: '4.2s', detail: 'per transaction', icon: Timer },
          { label: 'Daily Checkouts', value: '187', detail: 'across all desks', icon: BarChart3 },
          { label: 'Self-Checkout %', value: '34%', detail: 'and growing', icon: Monitor },
        ].map((m) => (
          <div key={m.label} className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700 text-center">
            <m.icon className="w-5 h-5 text-earth-600 mx-auto mb-1" />
            <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{m.value}</div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{m.label}</div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{m.detail}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
