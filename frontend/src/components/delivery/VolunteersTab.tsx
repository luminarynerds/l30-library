/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { DeliveryVolunteer } from '../../api/homeDeliveryApi';

interface VolunteersTabProps {
  volunteers: DeliveryVolunteer[];
  onApprove: (volunteer: DeliveryVolunteer) => void;
  getStatusColor: (status: string) => string;
}

export function VolunteersTab({ volunteers, onApprove, getStatusColor }: VolunteersTabProps) {
  return (
    <div className="space-y-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow overflow-hidden">
        <table className="w-full divide-y divide-earth-200 dark:divide-earth-700">
          <thead className="bg-earth-50 dark:bg-earth-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Volunteer</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Recognition</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Deliveries</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Hours</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-earth-200 dark:divide-earth-700">
            {volunteers.map((volunteer) => (
              <tr key={volunteer.id} className="hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                <td className="px-6 py-4">
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">{volunteer.user_name}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{volunteer.user_email}</p>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(volunteer.status)}`}>
                    {volunteer.status.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <span className="capitalize text-sm">{volunteer.recognition_level}</span>
                </td>
                <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{volunteer.total_deliveries}</td>
                <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{volunteer.total_volunteer_hours.toFixed(1)}</td>
                <td className="px-6 py-4">
                  {volunteer.status === 'pending_approval' && (
                    <button
                      onClick={() => onApprove(volunteer)}
                      className="text-status-success-600 hover:text-status-success-800 dark:text-status-success-300 font-medium text-sm"
                    >
                      Approve
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
