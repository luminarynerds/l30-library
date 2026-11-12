/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Filter, Loader2, HelpCircle, CheckCircle,
} from "lucide-react"
import type { ClaimsReturnedDispute } from "../../api/staff-api"
import { getClaimStatusColor } from "../../utils/status-colors"
import { formatStatus, formatDate } from "../../utils/format-utils"
import { useTranslation } from '@/i18n'

interface ClaimsReturnedTabProps {
  claimsData: { items: ClaimsReturnedDispute[]; total: number } | undefined
  claimsLoading: boolean
  claimStatusFilter: string
  setClaimStatusFilter: (v: string) => void
  setSelectedClaim: (claim: ClaimsReturnedDispute) => void
  setShowResolveClaimModal: (v: boolean) => void
}

export function ClaimsReturnedTab({
  claimsData,
  claimsLoading,
  claimStatusFilter,
  setClaimStatusFilter,
  setSelectedClaim,
  setShowResolveClaimModal,
}: ClaimsReturnedTabProps): React.ReactElement {
  const { t } = useTranslation()
  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Filters:</span>
        </div>
        <select
          value={claimStatusFilter}
          onChange={(e) => setClaimStatusFilter(e.target.value)}
          className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        >
          <option value="">All Statuses</option>
          <option value="filed">Filed</option>
          <option value="under_review">Under Review</option>
          <option value="searching">Searching</option>
          <option value="resolved_approved">Resolved - Approved</option>
          <option value="resolved_denied">Resolved - Denied</option>
          <option value="resolved_found">Resolved - Found</option>
        </select>
      </div>

      {/* Claims Table */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        {claimsLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : claimsData?.items && claimsData.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-lsc-cream/50 dark:bg-earth-700/50">
                <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 font-medium">Patron</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Filed</th>
                  <th className="px-4 py-3 font-medium">Claimed Return</th>
                  <th className="px-4 py-3 font-medium">Previous Claims</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {claimsData.items.map((claim) => (
                  <tr key={claim.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-xs" title={claim.item_title || `Item #${claim.item_copy_id}`}>
                        {claim.item_title || `Item #${claim.item_copy_id}`}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {claim.patron_name || "-"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getClaimStatusColor(claim.status)}`}>
                        {formatStatus(claim.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {formatDate(claim.filed_at)}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {claim.claimed_return_date ? formatDate(claim.claimed_return_date) : "-"}
                    </td>
                    <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {claim.patron_previous_claims_count > 0 && (
                        <span className={`${claim.patron_previous_claims_count >= 3 ? "text-status-danger-600 dark:text-status-danger-400" : ""}`}>
                          {claim.patron_previous_claims_count}
                        </span>
                      )}
                      {claim.patron_previous_claims_count === 0 && "0"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {!claim.status.startsWith("resolved") && (
                          <button
                            onClick={() => { setSelectedClaim(claim); setShowResolveClaimModal(true) }}
                            className="p-1.5 text-lsc-rose dark:text-lsc-rose-light hover:bg-earth-100 dark:bg-earth-800/30 dark:hover:bg-earth-800/30 rounded-lg transition-colors"
                            title="Resolve Claim"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
            <HelpCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>{t('components.staffLostDamaged.claimsReturnedTab.noClaimsReturnedDisputesFound')}</p>
          </div>
        )}
      </div>
      {claimsData && (
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Showing {claimsData.items.length} of {claimsData.total} claims
        </div>
      )}
    </div>
  )
}
