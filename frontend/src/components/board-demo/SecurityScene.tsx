/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Shield, AlertTriangle, Lock, FileText, Scale } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { StaggeredList } from './DemoAnimations'

export function SecurityScene() {
  const { t } = useTranslation()
  const [showPrivacyDemo, setShowPrivacyDemo] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setShowPrivacyDemo(true), 1000)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="space-y-6">
      <div className="bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-xl p-6 border border-lsc-rose/30 dark:border-lsc-rose/30">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="w-6 h-6 text-lsc-rose" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{t('boardDemo.alaPrivacyPrinciplesBuiltIn')}</h3>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
          Reading history is private by default. Patrons opt in to reading history tracking&mdash;it&apos;s never assumed.
          When law enforcement requests come, there&apos;s a documented compliance workflow that protects patron rights.
        </p>
      </div>

      {showPrivacyDemo && (
        <div className="bg-earth-900 dark:bg-earth-950 rounded-xl p-6 font-mono text-sm border-2 border-earth-700">
          <div className="text-earth-600 mb-3"># Privacy Ledger - What gets logged when patron data is accessed:</div>
          <div className="space-y-2">
            <div className="text-status-success-400">
              <span className="text-earth-600">2026-02-27 09:14:22</span> {t('boardDemo.staffLookupPatronIdBy')} <span className="text-earth-600">[ROUTINE]</span>
            </div>
            <div className="text-status-warning-400">
              <span className="text-earth-600">2026-02-27 09:30:01</span> {t('boardDemo.adminExportTypeQuotReading')} <span className="text-status-danger-400">[REQUIRES_CONSENT]</span> status=BLOCKED
            </div>
            <div className="text-status-success-400">
              <span className="text-earth-600">2026-02-27 09:30:15</span> PATRON_CONSENT patron_id=4821 grant=&quot;reading_history_export&quot; expires=2026-03-27
            </div>
            <div className="text-status-success-400">
              <span className="text-earth-600">2026-02-27 09:30:16</span> {t('boardDemo.adminExportTypeQuotReading2')} <span className="text-status-success-400">[AUTHORIZED]</span> status=OK
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <StaggeredList staggerMs={120}>
          {[
            { title: 'Rate Limiting', detail: 'Redis-backed distributed rate limiting prevents automated attacks', icon: AlertTriangle },
            { title: 'Security Headers', detail: 'CSP, HSTS, X-Frame-Options on every response', icon: Lock },
            { title: 'Privacy Ledger', detail: 'Every data access is logged and auditable', icon: FileText },
            { title: 'Law Enforcement Workflow', detail: 'Documented subpoena response with legal review', icon: Scale },
          ].map((f) => (
            <div key={f.title} className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700 hover:shadow-md hover:-translate-y-0.5 transition-all">
              <div className="flex items-center gap-2 mb-2">
                <f.icon className="w-4 h-4 text-lsc-rose" />
                <h4 className="font-medium text-lsc-dark dark:text-lsc-cream text-sm">{f.title}</h4>
              </div>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{f.detail}</p>
            </div>
          ))}
        </StaggeredList>
      </div>
    </div>
  )
}
