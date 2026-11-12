/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Wifi, Layers, Sparkles, AlertTriangle, Globe, Heart } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { ConfettiBurst, StaggeredList } from './DemoAnimations'

export function WowScene() {
  const { t } = useTranslation()
  const [showConfetti, setShowConfetti] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setShowConfetti(true), 1500)
    return () => clearTimeout(timer)
  }, [])

  const wowFeatures = [
    {
      title: 'Real-Time Notifications',
      detail: 'Hold ready? Know in seconds via WebSocket push. No refreshing, no waiting for email.',
      icon: Wifi,
      gradient: 'from-status-warning-400 to-orange-500',
    },
    {
      title: 'RFID Inventory Scanning',
      detail: 'Walk down a shelf with an RFID reader. Entire section inventoried in 30 seconds. Missing items flagged automatically.',
      icon: Layers,
      gradient: 'from-category-400 to-violet-500',
    },
    {
      title: 'AI Reading Recommendations',
      detail: 'Privacy-respecting AI suggests "You liked Piranesi? Try The Starless Sea." Only works if patron opts in.',
      icon: Sparkles,
      gradient: 'from-pink-400 to-rose-500',
    },
    {
      title: 'Emergency Operations Mode',
      detail: 'Internet down? L30 switches to offline mode. Checkouts continue. Data syncs when connectivity returns.',
      icon: AlertTriangle,
      gradient: 'from-red-400 to-orange-500',
    },
    {
      title: 'Community Pulse',
      detail: 'Live feed of library activity: books checked out, events happening, new arrivals\u2014all anonymized, all real-time.',
      icon: Globe,
      gradient: 'from-blue-400 to-cyan-500',
    },
    {
      title: t('boardDemo.builtForL30'),
      detail: "This isn't a generic system configured for our library. It was built knowing our patrons, our collection, our values.",
      icon: Heart,
      gradient: 'from-green-400 to-emerald-500',
    },
  ]

  return (
    <div className="space-y-6">
      {showConfetti && <ConfettiBurst />}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StaggeredList staggerMs={150}>
          {wowFeatures.map((f) => (
            <div
              key={f.title}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-300 group"
            >
              <div className={`bg-gradient-to-r ${f.gradient} p-4 flex items-center gap-3`}>
                <f.icon className="w-6 h-6 text-white group-hover:scale-110 transition-transform" />
                <h4 className="font-serif font-semibold text-white">{f.title}</h4>
              </div>
              <div className="p-4">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{f.detail}</p>
              </div>
            </div>
          ))}
        </StaggeredList>
      </div>

      <div className="bg-gradient-to-r from-earth-800 to-earth-900 dark:from-earth-700 dark:to-earth-800 rounded-xl p-8 text-center text-white relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-status-warning-500/10 to-orange-500/10 motion-safe:animate-pulse" />
        <div className="relative">
          <Sparkles className="w-8 h-8 text-status-warning-400 mx-auto mb-3 motion-safe:animate-bounce" />
          <h3 className="text-2xl font-serif font-bold mb-2">This Is L30</h3>
          <p className="text-earth-300 max-w-lg mx-auto">
            A modern, accessible, secure library system that respects patron privacy,
            empowers staff, and demonstrates measurable community value.
            Built with care for our community.
          </p>
        </div>
      </div>
    </div>
  )
}
