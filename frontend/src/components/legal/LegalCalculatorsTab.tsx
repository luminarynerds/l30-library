/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Clock, Shield, CheckCircle, XCircle, Eye, Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { DeadlineRule } from '@/api/legal-api'

interface LegalCalculatorsTabProps {
  deadlineRules: DeadlineRule[] | undefined
  rulesLoading: boolean
}

export function LegalCalculatorsTab({ deadlineRules, rulesLoading }: LegalCalculatorsTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">{t('admin.adminLegal.legalCalculatorsDeadlineRules')}</h2>
        <a
          href="/legal/calculators"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm"
        >
          <Eye className="w-4 h-4" />
          Preview Public View
        </a>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {[
          {
            title: 'Deadline Calculator',
            description: t('admin.adminLegal.calculateLegalDeadlinesAccountingFor'),
            endpoint: '/legal/deadlines/calculate',
            icon: <Clock className="w-6 h-6" />,
            color: 'text-lsc-rose dark:text-lsc-rose-light',
          },
          {
            title: 'Fee Waiver Eligibility',
            description: t('admin.adminLegal.checkPreliminaryEligibilityForCourt'),
            endpoint: '/legal/fee-waiver/check',
            icon: <Shield className="w-6 h-6" />,
            color: 'text-status-success-600',
          },
          {
            title: 'Expungement Eligibility',
            description: t('admin.adminLegal.checkBasicExpungementEligibilityBased'),
            endpoint: '/legal/expungement/check',
            icon: <CheckCircle className="w-6 h-6" />,
            color: 'text-category-600',
          },
        ].map(calc => (
          <div key={calc.title} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700">
            <div className={`${calc.color} mb-3`}>{calc.icon}</div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-2">{calc.title}</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{calc.description}</p>
            <code className="text-xs bg-lsc-cream dark:bg-earth-900 px-2 py-1 rounded text-lsc-dark/70 dark:text-lsc-cream/70">{calc.endpoint}</code>
          </div>
        ))}
      </div>

      <div>
        <h3 className="text-sm font-semibold text-lsc-dark dark:text-earth-50 mb-3">Deadline Rules ({deadlineRules?.length ?? 0})</h3>
        {rulesLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : deadlineRules && deadlineRules.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-lsc-border dark:border-earth-700">
                  <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Rule Name</th>
                  <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Type</th>
                  <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Days</th>
                  <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Business Days</th>
                  <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Jurisdiction</th>
                </tr>
              </thead>
              <tbody>
                {deadlineRules.map(rule => (
                  <tr key={rule.id} className="border-b border-lsc-border/50 dark:border-earth-700/50">
                    <td className="py-2 px-3 font-medium text-lsc-dark dark:text-earth-50">{rule.name}</td>
                    <td className="py-2 px-3 text-lsc-dark/70 dark:text-lsc-cream/70">{rule.deadline_type}</td>
                    <td className="py-2 px-3 text-lsc-dark/70 dark:text-lsc-cream/70">{rule.days}</td>
                    <td className="py-2 px-3">
                      {rule.use_business_days ? (
                        <CheckCircle className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
                      ) : (
                        <XCircle className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                      )}
                    </td>
                    <td className="py-2 px-3 text-lsc-dark/70 dark:text-lsc-cream/70">{rule.jurisdiction || 'All'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminLegal.noDeadlineRulesConfigured')}</p>
          </div>
        )}
      </div>
    </div>
  )
}
