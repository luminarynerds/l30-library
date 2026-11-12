/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Search, Calendar, Phone, UserCheck, Truck } from 'lucide-react';
import { useTranslation } from '@/i18n';
import type { HomeDeliveryEnrollment } from '../../api/homeDeliveryApi';

interface EnrollmentsTabProps {
  enrollments: HomeDeliveryEnrollment[];
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onScheduleDelivery: (enrollmentId: number) => void;
  getStatusColor: (status: string) => string;
}

export function EnrollmentsTab({
  enrollments,
  searchQuery,
  onSearchChange,
  onScheduleDelivery,
  getStatusColor,
}: EnrollmentsTabProps) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
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
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {enrollments.map((enrollment) => (
          <div key={enrollment.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{enrollment.patron_name}</h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{enrollment.patron_library_card}</p>
              </div>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(enrollment.status)}`}>
                {enrollment.status}
              </span>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                <Calendar className="w-4 h-4" />
                <span className="capitalize">{enrollment.delivery_frequency.replace('_', ' ')} delivery</span>
              </div>
              <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                <Phone className="w-4 h-4" />
                <span>{enrollment.contact_phone}</span>
              </div>
              {enrollment.assigned_volunteer_name && (
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <UserCheck className="w-4 h-4" />
                  <span>{enrollment.assigned_volunteer_name}</span>
                </div>
              )}
              <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                <Truck className="w-4 h-4" />
                <span>{enrollment.total_deliveries} total deliveries</span>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t flex justify-between items-center">
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                Next: {enrollment.next_scheduled_delivery || 'Not scheduled'}
              </span>
              <button
                onClick={() => onScheduleDelivery(enrollment.id)}
                className="text-status-warning-600 hover:text-status-warning-800 dark:text-status-warning-300 text-sm font-medium"
              >
                Schedule Delivery
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
