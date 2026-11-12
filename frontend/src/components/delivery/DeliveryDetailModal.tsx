/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, MapPin, Calendar, Clock, Package } from 'lucide-react';
import type { Delivery } from '../../api/homeDeliveryApi';
import { DeliveryStatusBadge, DeliveryProgressBar } from './DeliveryStatusBadge';
import { formatDate } from './delivery-data';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface DeliveryDetailModalProps {
  delivery: Delivery;
  onClose: () => void;
}

export function DeliveryDetailModal({ delivery, onClose }: DeliveryDetailModalProps) {
  return (
    <ModalBackdrop onClose={onClose} title="Delivery Details">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Delivery Details</h2>
            <button onClick={onClose} className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{delivery.patron_name}</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{delivery.patron_library_card}</p>
              </div>
              <DeliveryStatusBadge status={delivery.status} />
            </div>

            <div className="p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg space-y-2 text-sm">
              <div className="flex items-start gap-2">
                <MapPin className="w-4 h-4 mt-0.5 text-lsc-rose flex-shrink-0" />
                <span className="text-lsc-dark dark:text-lsc-cream">{delivery.delivery_address}</span>
              </div>
              {delivery.delivery_instructions && (
                <div className="text-lsc-dark/70 dark:text-lsc-cream/70 italic ml-6">
                  {delivery.delivery_instructions}
                </div>
              )}
              <div className="flex items-center gap-2 ml-0">
                <Calendar className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                <span className="text-lsc-dark/80 dark:text-lsc-cream/80">{formatDate(delivery.scheduled_date)}</span>
              </div>
              {delivery.scheduled_time_start && (
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  <span className="text-lsc-dark/80 dark:text-lsc-cream/80">
                    {delivery.scheduled_time_start}
                    {delivery.scheduled_time_end && ` – ${delivery.scheduled_time_end}`}
                  </span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                <span className="text-lsc-dark/80 dark:text-lsc-cream/80">{delivery.items_count} items</span>
              </div>
            </div>

            <div>
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Delivery Progress</p>
              <DeliveryProgressBar status={delivery.status} />
            </div>

            {delivery.staff_notes && (
              <div>
                <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Staff Notes</p>
                <p className="text-sm text-lsc-dark dark:text-lsc-cream">{delivery.staff_notes}</p>
              </div>
            )}
            {delivery.patron_notes && (
              <div>
                <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Patron Notes</p>
                <p className="text-sm text-lsc-dark dark:text-lsc-cream">{delivery.patron_notes}</p>
              </div>
            )}
            {delivery.failure_reason && (
              <div className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg">
                <p className="text-xs font-medium text-status-danger-700 dark:text-status-danger-400 mb-1">Failure Reason</p>
                <p className="text-sm text-status-danger-800 dark:text-status-danger-300">{delivery.failure_reason}</p>
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
