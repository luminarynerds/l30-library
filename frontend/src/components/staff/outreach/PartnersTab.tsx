/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Search, Building2, Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { PartnerStatus, getPartnerEngagementAudit } from '../../../api/staff-outreach-api'

type EngagementAudit = Awaited<ReturnType<typeof getPartnerEngagementAudit>>

interface Props {
  engagementAudit: EngagementAudit | undefined
  engagementLoading: boolean
  searchQuery: string
  setSearchQuery: (q: string) => void
  partnerStatusFilter: PartnerStatus | ""
  setPartnerStatusFilter: (s: PartnerStatus | "") => void
  selectedPartners: number[]
  setSelectedPartners: (ids: number[]) => void
  onBulkUpdate: () => void
  formatDate: (d: string) => string
}

export function PartnersTab({
  engagementAudit, engagementLoading, searchQuery, setSearchQuery,
  partnerStatusFilter, setPartnerStatusFilter,
  selectedPartners, setSelectedPartners, onBulkUpdate, formatDate,
}: Props) {
  const { t } = useTranslation()
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
            <input
              type="text"
              placeholder={t('placeholder.staffOutreach.searchPartners')}
              aria-label={t('aria.staffOutreach.searchPartners')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <select
            value={partnerStatusFilter}
            onChange={(e) => setPartnerStatusFilter(e.target.value as PartnerStatus | "")}
            className="px-4 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="pending">Pending</option>
            <option value="suspended">Suspended</option>
          </select>
        </div>
        <button
          onClick={onBulkUpdate}
          disabled={selectedPartners.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-400 text-white rounded-lg text-sm"
        >
          Bulk Update Status
        </button>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        {engagementLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : engagementAudit?.partners && engagementAudit.partners.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70 border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/50">
                  <th className="px-4 py-3 font-medium">
                    <input
                      type="checkbox"
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedPartners(engagementAudit.partners.map(p => p.partner_id))
                        } else {
                          setSelectedPartners([])
                        }
                      }}
                      checked={selectedPartners.length === engagementAudit.partners.length}
                      className="rounded"
                    />
                  </th>
                  <th className="px-4 py-3 font-medium">Partner</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Visits</th>
                  <th className="px-4 py-3 font-medium">Checkouts</th>
                  <th className="px-4 py-3 font-medium">Engagement</th>
                  <th className="px-4 py-3 font-medium">Last Activity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {engagementAudit.partners.map((partner) => (
                  <tr key={partner.partner_id} className="hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedPartners.includes(partner.partner_id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedPartners([...selectedPartners, partner.partner_id])
                          } else {
                            setSelectedPartners(selectedPartners.filter(id => id !== partner.partner_id))
                          }
                        }}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">{partner.partner_name}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 capitalize">
                      {partner.partner_type.replace("_", " ")}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {partner.visits_completed}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {partner.bulk_checkouts}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        partner.engagement_score >= 50 ? "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400" :
                        partner.engagement_score >= 20 ? "bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light" :
                        partner.engagement_score > 0 ? "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400" :
                        "bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300"
                      }`}>
                        {partner.engagement_score} pts
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {partner.last_activity ? formatDate(partner.last_activity) : "Never"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
            <Building2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No partners found</p>
          </div>
        )}
      </div>
    </div>
  )
}
