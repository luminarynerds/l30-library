/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Search, Loader2, Users, Eye, Settings, Calendar, Clock, Shield, CheckCircle, Phone, Truck } from 'lucide-react';
import { DeliveryVolunteer, VolunteerStatus } from '../../../api/homeDeliveryApi';
import { useTranslation } from '@/i18n';
import { VolunteerStatusBadge, RecognitionBadge } from './VolunteerBadges';

interface RosterTabProps {
  volunteers: DeliveryVolunteer[];
  volunteersLoading: boolean;
  searchQuery: string;
  statusFilter: VolunteerStatus | '';
  onSearchChange: (v: string) => void;
  onStatusFilterChange: (v: VolunteerStatus | '') => void;
  onViewVolunteer: (v: DeliveryVolunteer) => void;
  onOpenStatusModal: (v: DeliveryVolunteer) => void;
  onOpenScheduleModal: (v: DeliveryVolunteer) => void;
  onOpenHoursModal: (v: DeliveryVolunteer) => void;
}

export function RosterTab({
  volunteers,
  volunteersLoading,
  searchQuery,
  statusFilter,
  onSearchChange,
  onStatusFilterChange,
  onViewVolunteer,
  onOpenStatusModal,
  onOpenScheduleModal,
  onOpenHoursModal,
}: RosterTabProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
          <input
            type="text"
            placeholder={t('placeholder.homeDeliveryVolunteers.searchVolunteers')}
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            aria-label={t('aria.homeDeliveryVolunteers.searchVolunteers')}
            className="w-full pl-10 pr-4 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => onStatusFilterChange(e.target.value as VolunteerStatus | '')}
          aria-label={t('homeDeliveryVolunteers.filterVolunteersByStatus')}
          className="px-3 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="pending_approval">Pending Approval</option>
          <option value="inactive">Inactive</option>
          <option value="on_leave">On Leave</option>
          <option value="terminated">Terminated</option>
        </select>
      </div>

      {volunteersLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : volunteers.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {volunteers.map((volunteer) => (
            <div
              key={volunteer.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{volunteer.user_name}</h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{volunteer.user_email}</p>
                </div>
                <VolunteerStatusBadge status={volunteer.status} />
              </div>

              <div className="space-y-2 text-sm mb-3">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <Phone className="w-3.5 h-3.5" />
                  <span>{volunteer.phone}</span>
                </div>
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <Truck className="w-3.5 h-3.5" />
                  <span>{volunteer.total_deliveries} deliveries</span>
                </div>
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{volunteer.total_volunteer_hours}h total</span>
                </div>
                {volunteer.available_days.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {volunteer.available_days.map((day) => (
                      <span
                        key={day}
                        className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 text-xs rounded text-lsc-dark/70 dark:text-lsc-cream/70"
                      >
                        {day.slice(0, 3)}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2 mb-3">
                <RecognitionBadge level={volunteer.recognition_level} />
                {volunteer.background_check_completed && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400">
                    <Shield className="w-3 h-3" /> BG Check
                  </span>
                )}
                {volunteer.training_completed && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light">
                    <CheckCircle className="w-3 h-3" /> Trained
                  </span>
                )}
              </div>

              {volunteer.status === 'pending_approval' && (
                <div className="p-2 mb-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded text-xs text-status-warning-800 dark:text-status-warning-300">
                  Awaiting background check and approval
                </div>
              )}

              <div className="flex flex-wrap gap-2 pt-3 border-t border-lsc-border dark:border-earth-700">
                <button
                  onClick={() => onViewVolunteer(volunteer)}
                  className="flex items-center gap-1 px-2 py-1 text-xs border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded hover:bg-lsc-cream dark:hover:bg-earth-700"
                >
                  <Eye className="w-3 h-3" /> View
                </button>
                <button
                  onClick={() => onOpenStatusModal(volunteer)}
                  className="flex items-center gap-1 px-2 py-1 text-xs border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded hover:bg-lsc-cream dark:hover:bg-earth-700"
                >
                  <Settings className="w-3 h-3" /> Status
                </button>
                <button
                  onClick={() => onOpenScheduleModal(volunteer)}
                  className="flex items-center gap-1 px-2 py-1 text-xs border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded hover:bg-lsc-cream dark:hover:bg-earth-700"
                >
                  <Calendar className="w-3 h-3" /> Schedule
                </button>
                <button
                  onClick={() => onOpenHoursModal(volunteer)}
                  className="flex items-center gap-1 px-2 py-1 text-xs bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded"
                >
                  <Clock className="w-3 h-3" /> Hours
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
          <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No volunteers found</p>
        </div>
      )}
    </div>
  );
}
