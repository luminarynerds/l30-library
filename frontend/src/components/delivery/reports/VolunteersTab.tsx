/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Star, CheckCircle } from "lucide-react"
import { useTranslation } from "@/i18n"

interface VolunteerReport {
  volunteer_id: number
  volunteer_name: string
  volunteer_status: string
  total_deliveries: number
  total_hours: number
  assigned_patrons_count: number
  average_rating?: number
  recognition_level: string
}

interface VolunteerByHours {
  volunteer_id: number
  name: string
  recognition_level: string
  hours: number
}

interface VolunteerByDeliveries {
  volunteer_id: number
  name: string
  recognition_level: string
  deliveries: number
}

interface Milestone {
  volunteer_id: number
  volunteer_name: string
  milestone: string
  total_hours: number
}

interface VolunteerRecognition {
  top_by_hours: VolunteerByHours[]
  top_by_deliveries: VolunteerByDeliveries[]
  recognition_levels: Record<string, number>
  recent_milestones: Milestone[]
}

interface Props {
  volunteerReports: VolunteerReport[] | undefined
  volunteerReportsLoading: boolean
  volunteerRecognition: VolunteerRecognition | undefined
}

const RANK_COLORS = ['bg-status-warning-500', 'bg-earth-400', 'bg-status-warning-700', 'bg-lsc-rose']

export function VolunteersTab({ volunteerReports, volunteerReportsLoading, volunteerRecognition }: Props) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      {volunteerRecognition && (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{t('homeDeliveryReports.topVolunteersByHours')}</h3>
            <div className="space-y-3">
              {volunteerRecognition.top_by_hours.slice(0, 5).map((v: VolunteerByHours, i: number) => (
                <div key={v.volunteer_id} className="flex items-center gap-3">
                  <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white ${RANK_COLORS[Math.min(i, 3)]}`}>
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={v.name}>{v.name}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{v.recognition_level}</p>
                  </div>
                  <span className="text-sm font-bold text-lsc-rose">{v.hours}h</span>
                </div>
              ))}
              {volunteerRecognition.top_by_hours.length === 0 && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-3">No data available</p>
              )}
            </div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{t('homeDeliveryReports.topVolunteersByDeliveries')}</h3>
            <div className="space-y-3">
              {volunteerRecognition.top_by_deliveries.slice(0, 5).map((v: VolunteerByDeliveries, i: number) => (
                <div key={v.volunteer_id} className="flex items-center gap-3">
                  <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white ${RANK_COLORS[Math.min(i, 3)]}`}>
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={v.name}>{v.name}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{v.recognition_level}</p>
                  </div>
                  <span className="text-sm font-bold text-lsc-rose">{v.deliveries}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {volunteerRecognition && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Recognition Levels Distribution</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(volunteerRecognition.recognition_levels).map(([level, count]) => (
              <div key={level} className="text-center p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
                <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{count}</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{level}</p>
              </div>
            ))}
          </div>
          {volunteerRecognition.recent_milestones.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Recent Milestones</h4>
              <div className="space-y-2">
                {volunteerRecognition.recent_milestones.slice(0, 5).map((milestone) => (
                  <div key={`${milestone.volunteer_id}-${milestone.milestone}`} className="flex items-center gap-2 text-sm">
                    <CheckCircle className="w-4 h-4 text-status-success-500 flex-shrink-0" />
                    <span className="font-medium text-lsc-dark dark:text-lsc-cream">{milestone.volunteer_name}</span>
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{milestone.milestone}</span>
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">({milestone.total_hours}h)</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">All Volunteer Stats</h3>
        </div>
        {volunteerReportsLoading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : volunteerReports && volunteerReports.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/50">
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Volunteer</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Deliveries</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Hours</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Patrons</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Avg Rating</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Recognition</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {volunteerReports.map((v) => (
                  <tr key={v.volunteer_id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                    <td className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">{v.volunteer_name}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        v.volunteer_status === 'active'
                          ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400'
                          : 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300'
                      }`}>
                        {v.volunteer_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">{v.total_deliveries}</td>
                    <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">{v.total_hours}h</td>
                    <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">{v.assigned_patrons_count}</td>
                    <td className="px-4 py-3">
                      {v.average_rating ? (
                        <span className="flex items-center gap-1">
                          <Star className="w-3.5 h-3.5 text-status-warning-500" />
                          {v.average_rating.toFixed(1)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3 capitalize text-lsc-dark/70 dark:text-lsc-cream/70">{v.recognition_level}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-6 text-lsc-dark/70 dark:text-lsc-cream/70">No volunteer data</div>
        )}
      </div>
    </div>
  )
}
