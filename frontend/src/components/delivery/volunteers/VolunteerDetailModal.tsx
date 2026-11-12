/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, CheckCircle, XCircle, Star } from 'lucide-react';
import { DeliveryVolunteer } from '../../../api/homeDeliveryApi';
import { VolunteerStatusBadge } from './VolunteerBadges';
import { DAYS_OF_WEEK, formatDate } from './volunteers-data';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface VolunteerDetailModalProps {
  volunteer: DeliveryVolunteer;
  onClose: () => void;
}

export function VolunteerDetailModal({ volunteer, onClose }: VolunteerDetailModalProps) {
  return (
    <ModalBackdrop onClose={onClose} title="Volunteer Profile">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Volunteer Profile</h2>
            <button onClick={onClose} className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{volunteer.user_name}</h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{volunteer.user_email}</p>
              </div>
              <VolunteerStatusBadge status={volunteer.status} />
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Phone</p>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">{volunteer.phone}</p>
              </div>
              <div className="p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Total Hours</p>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">{volunteer.total_volunteer_hours}h</p>
              </div>
              <div className="p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Total Deliveries</p>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">{volunteer.total_deliveries}</p>
              </div>
              <div className="p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Max Deliveries/Week</p>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">{volunteer.max_deliveries_per_week}</p>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                {volunteer.background_check_completed ? (
                  <CheckCircle className="w-4 h-4 text-status-success-500" />
                ) : (
                  <XCircle className="w-4 h-4 text-status-danger-500" />
                )}
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                  Background check
                  {volunteer.background_check_date && ` (${formatDate(volunteer.background_check_date)})`}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {volunteer.training_completed ? (
                  <CheckCircle className="w-4 h-4 text-status-success-500" />
                ) : (
                  <XCircle className="w-4 h-4 text-status-danger-500" />
                )}
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                  Training completed
                  {volunteer.training_date && ` (${formatDate(volunteer.training_date)})`}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {volunteer.has_vehicle ? (
                  <CheckCircle className="w-4 h-4 text-status-success-500" />
                ) : (
                  <XCircle className="w-4 h-4 text-status-danger-500" />
                )}
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                  Has vehicle {volunteer.vehicle_type ? `(${volunteer.vehicle_type})` : ''}
                </span>
              </div>
            </div>

            {volunteer.available_days.length > 0 && (
              <div>
                <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Available Days</p>
                <div className="flex flex-wrap gap-2">
                  {DAYS_OF_WEEK.map((day) => (
                    <span
                      key={day}
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        volunteer.available_days.includes(day)
                          ? 'bg-lsc-rose text-white'
                          : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                      }`}
                    >
                      {day.slice(0, 3)}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {volunteer.emergency_contact_name && (
              <div className="p-3 bg-status-danger-50 dark:bg-status-danger-900/10 border border-status-danger-200 dark:border-status-danger-800 rounded-lg">
                <p className="text-xs font-medium text-status-danger-700 dark:text-status-danger-400 mb-1">Emergency Contact</p>
                <p className="text-sm text-status-danger-800 dark:text-status-danger-300">
                  {volunteer.emergency_contact_name}: {volunteer.emergency_contact_phone}
                </p>
              </div>
            )}

            {volunteer.achievements.length > 0 && (
              <div>
                <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Achievements</p>
                <div className="space-y-1">
                  {volunteer.achievements.map((ach, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Star className="w-3.5 h-3.5 text-status-warning-500" />
                      <span>{ach.name}</span>
                      <span className="text-xs">({formatDate(ach.date)})</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-lsc-cream dark:bg-earth-700 hover:bg-lsc-border dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-lg"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
}
