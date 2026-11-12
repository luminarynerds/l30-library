/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Search } from 'lucide-react';
import { useTranslation } from '@/i18n';
import type { HomeDeliveryApplication, HomeDeliveryApplicationStatus } from '../../api/homeDeliveryApi';

interface ApplicationsTabProps {
  applications: HomeDeliveryApplication[];
  searchQuery: string;
  appFilter: HomeDeliveryApplicationStatus | '';
  onSearchChange: (q: string) => void;
  onFilterChange: (f: HomeDeliveryApplicationStatus | '') => void;
  onReview: (app: HomeDeliveryApplication) => void;
  getStatusColor: (status: string) => string;
}

export function ApplicationsTab({
  applications,
  searchQuery,
  appFilter,
  onSearchChange,
  onFilterChange,
  onReview,
  getStatusColor,
}: ApplicationsTabProps) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <input
              type="text"
              placeholder={t('placeholder.homeDeliveryManagement.searchPatrons')}
              aria-label={t('aria.homeDeliveryManagement.searchPatrons')}
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500"
            />
          </div>
          <select
            value={appFilter}
            onChange={(e) => onFilterChange(e.target.value as HomeDeliveryApplicationStatus | '')}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="under_review">Under Review</option>
            <option value="approved">Approved</option>
            <option value="denied">Denied</option>
            <option value="waitlisted">Waitlisted</option>
          </select>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow overflow-hidden">
        <table className="w-full divide-y divide-earth-200 dark:divide-earth-700">
          <thead className="bg-earth-50 dark:bg-earth-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Patron</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Submitted</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Frequency</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-earth-200 dark:divide-earth-700">
            {applications.map((app) => (
              <tr key={app.id} className="hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                <td className="px-6 py-4">
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">{app.patron_name}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{app.patron_library_card}</p>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(app.status)}`}>
                    {app.status.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {new Date(app.submitted_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                  {app.preferred_frequency.replace('_', ' ')}
                </td>
                <td className="px-6 py-4">
                  {app.status === 'pending' && (
                    <button
                      onClick={() => onReview(app)}
                      className="text-status-warning-600 hover:text-status-warning-800 dark:text-status-warning-300 font-medium text-sm"
                    >
                      Review
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {applications.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                  No applications found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
