/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Loader2 } from 'lucide-react';
import { UseMutationResult } from '@tanstack/react-query';
import { VolunteerStatus } from '../../../api/homeDeliveryApi';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface StatusUpdateModalProps {
  newStatus: VolunteerStatus;
  bgCheckCompleted: boolean;
  bgCheckDate: string;
  bgCheckExpiry: string;
  trainingCompleted: boolean;
  trainingDate: string;
  updateStatusMutation: UseMutationResult<unknown, Error, void>;
  onClose: () => void;
  onNewStatusChange: (v: VolunteerStatus) => void;
  onBgCheckCompletedChange: (v: boolean) => void;
  onBgCheckDateChange: (v: string) => void;
  onBgCheckExpiryChange: (v: string) => void;
  onTrainingCompletedChange: (v: boolean) => void;
  onTrainingDateChange: (v: string) => void;
}

export function StatusUpdateModal({
  newStatus,
  bgCheckCompleted,
  bgCheckDate,
  bgCheckExpiry,
  trainingCompleted,
  trainingDate,
  updateStatusMutation,
  onClose,
  onNewStatusChange,
  onBgCheckCompletedChange,
  onBgCheckDateChange,
  onBgCheckExpiryChange,
  onTrainingCompletedChange,
  onTrainingDateChange,
}: StatusUpdateModalProps) {
  return (
    <ModalBackdrop onClose={onClose} title="Update Volunteer Status">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Update Volunteer Status</h2>
            <button onClick={onClose} className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Status</label>
              <select
                value={newStatus}
                onChange={(e) => onNewStatusChange(e.target.value as VolunteerStatus)}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="on_leave">On Leave</option>
                <option value="pending_approval">Pending Approval</option>
                <option value="terminated">Terminated</option>
              </select>
            </div>

            <div className="space-y-3 p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Background Check</p>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={bgCheckCompleted}
                  onChange={(e) => onBgCheckCompletedChange(e.target.checked)}
                  className="rounded border-lsc-border text-lsc-rose"
                />
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">Completed</span>
              </label>
              {bgCheckCompleted && (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Check Date</label>
                    <input
                      type="date"
                      value={bgCheckDate}
                      onChange={(e) => onBgCheckDateChange(e.target.value)}
                      className="w-full px-2 py-1.5 bg-lsc-white dark:bg-earth-600 border border-lsc-border dark:border-earth-700 rounded text-sm text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Expires</label>
                    <input
                      type="date"
                      value={bgCheckExpiry}
                      onChange={(e) => onBgCheckExpiryChange(e.target.value)}
                      className="w-full px-2 py-1.5 bg-lsc-white dark:bg-earth-600 border border-lsc-border dark:border-earth-700 rounded text-sm text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-3 p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Training</p>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={trainingCompleted}
                  onChange={(e) => onTrainingCompletedChange(e.target.checked)}
                  className="rounded border-lsc-border text-lsc-rose"
                />
                <span className="text-sm text-lsc-dark dark:text-lsc-cream">Training Completed</span>
              </label>
              {trainingCompleted && (
                <div>
                  <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Training Date</label>
                  <input
                    type="date"
                    value={trainingDate}
                    onChange={(e) => onTrainingDateChange(e.target.value)}
                    className="w-full px-2 py-1.5 bg-lsc-white dark:bg-earth-600 border border-lsc-border dark:border-earth-700 rounded text-sm text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
              Cancel
            </button>
            <button
              onClick={() => updateStatusMutation.mutate()}
              disabled={updateStatusMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium"
            >
              {updateStatusMutation.isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Save
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
}
