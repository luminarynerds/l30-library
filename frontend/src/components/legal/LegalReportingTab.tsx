/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { FileText, Calendar, Users, BookOpen, Calculator, MapPin, BarChart3, AlertCircle } from 'lucide-react'
import { useTranslation } from '@/i18n'

interface LegalReportingTabProps {
  formsTotal: number
  clinicsTotal: number
  providersTotal: number
  guidesTotal: number
  courtsTotal: number
}

export function LegalReportingTab({ formsTotal, clinicsTotal, providersTotal, guidesTotal, courtsTotal }: LegalReportingTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">Analytics & Reporting</h2>

      <div className="grid md:grid-cols-2 gap-4">
        {[
          {
            title: 'Form Downloads',
            description: t('admin.adminLegal.trackWhichLegalFormsAre'),
            metric: `${formsTotal} forms available`,
            icon: <FileText className="w-5 h-5" />,
            color: 'text-lsc-rose dark:text-lsc-rose-light',
          },
          {
            title: 'Clinic Registrations',
            description: t('admin.adminLegal.monitorAttendanceAndWaitlistTrends'),
            metric: `${clinicsTotal} clinics scheduled`,
            icon: <Calendar className="w-5 h-5" />,
            color: 'text-status-success-600',
          },
          {
            title: 'Provider Directory Usage',
            description: t('admin.adminLegal.seeWhichLegalAidProviders'),
            metric: `${providersTotal} providers listed`,
            icon: <Users className="w-5 h-5" />,
            color: 'text-category-600',
          },
          {
            title: 'Guide Helpfulness',
            description: t('admin.adminLegal.trackHelpfulNotHelpfulRatings'),
            metric: `${guidesTotal} guides published`,
            icon: <BookOpen className="w-5 h-5" />,
            color: 'text-lsc-rose',
          },
          {
            title: 'Calculator Usage',
            description: t('admin.adminLegal.monitorUseOfDeadlineFee'),
            metric: '3 calculators active',
            icon: <Calculator className="w-5 h-5" />,
            color: 'text-lsc-rose',
          },
          {
            title: 'Court Directory Views',
            description: t('admin.adminLegal.seeWhichCourtLocationsPatrons'),
            metric: `${courtsTotal} courts listed`,
            icon: <MapPin className="w-5 h-5" />,
            color: 'text-rose-700',
          },
        ].map(report => (
          <div key={report.title} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700">
            <div className={`${report.color} mb-3`}>{report.icon}</div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-1">{report.title}</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{report.description}</p>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-lsc-rose">{report.metric}</span>
              <button
                disabled
                title="Coming soon"
                className="text-xs text-lsc-dark/70 dark:text-lsc-cream/40 cursor-not-allowed flex items-center gap-1"
              >
                <BarChart3 className="w-3 h-3" />
                View Report
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-status-warning-800 dark:text-status-warning-200 text-sm">Detailed Analytics</p>
            <p className="text-xs text-status-warning-700 dark:text-status-warning-300 mt-1">
              Full reporting is available through the backend API at <code className="font-mono">/legal/reporting/</code>.
              Use the analytics dashboard for cross-module statistics and trend analysis.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
