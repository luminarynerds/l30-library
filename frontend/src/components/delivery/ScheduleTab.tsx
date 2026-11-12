/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Truck, Clock, MapPin, Package, Eye, ChevronRight, Loader2 } from 'lucide-react';
import type { Delivery } from '../../api/homeDeliveryApi';
import { DeliveryStatusBadge, DeliveryProgressBar } from './DeliveryStatusBadge';
import { useTranslation, getCurrentLocale } from '@/i18n';

interface ScheduleTabProps {
  selectedDate: string;
  onDateChange: (date: string) => void;
  deliveries: Delivery[];
  loading: boolean;
  onViewDelivery: (delivery: Delivery) => void;
  onAdvanceStatus: (delivery: Delivery) => void;
  onScheduleForDate: (date: string) => void;
  isAdvancing: boolean;
}

export function ScheduleTab({
  selectedDate,
  onDateChange,
  deliveries,
  loading,
  onViewDelivery,
  onAdvanceStatus,
  onScheduleForDate,
  isAdvancing,
}: ScheduleTabProps) {
  const { t } = useTranslation();
  const todayDeliveries = deliveries.filter((d) => d.scheduled_date === selectedDate);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <label className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Viewing date:</label>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => onDateChange(e.target.value)}
          className="px-3 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
        />
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {todayDeliveries.length} deliveries scheduled
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total', count: todayDeliveries.length, color: 'text-lsc-dark dark:text-lsc-cream', bg: 'bg-lsc-white dark:bg-earth-800' },
          { label: 'Scheduled', count: todayDeliveries.filter((d) => d.status === 'scheduled').length, color: 'text-status-warning-700 dark:text-status-warning-400', bg: 'bg-status-warning-50 dark:bg-status-warning-900/20' },
          { label: 'Out for Delivery', count: todayDeliveries.filter((d) => d.status === 'out_for_delivery').length, color: 'text-category-700 dark:text-category-400', bg: 'bg-category-50 dark:bg-category-900/20' },
          { label: 'Delivered', count: todayDeliveries.filter((d) => d.status === 'delivered').length, color: 'text-status-success-700 dark:text-status-success-400', bg: 'bg-status-success-50 dark:bg-status-success-900/20' },
        ].map((stat) => (
          <div key={stat.label} className={`${stat.bg} rounded-xl p-4 border border-lsc-border dark:border-earth-700`}>
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.count}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/50">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Deliveries for {new Date(selectedDate + 'T00:00:00').toLocaleDateString(getCurrentLocale(), { weekday: 'long', month: 'long', day: 'numeric' })}
          </h3>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : todayDeliveries.length === 0 ? (
          <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
            <Truck className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>{t('homeDelivery.noDeliveriesScheduledForThis')}</p>
            <button
              onClick={() => onScheduleForDate(selectedDate)}
              className="mt-3 text-lsc-rose hover:text-lsc-rose/80 text-sm font-medium"
            >
              Schedule a delivery for this date
            </button>
          </div>
        ) : (
          <div className="divide-y divide-lsc-border dark:divide-earth-700">
            {todayDeliveries.map((delivery) => (
              <div key={delivery.id} className="p-4 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{delivery.patron_name}</p>
                      <DeliveryStatusBadge status={delivery.status} />
                    </div>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2 truncate" title={delivery.delivery_address}>{delivery.delivery_address}</p>
                    {(delivery.scheduled_time_start || delivery.scheduled_time_end) && (
                      <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                        <Clock className="w-3 h-3" />
                        <span>
                          {delivery.scheduled_time_start && delivery.scheduled_time_end
                            ? `${delivery.scheduled_time_start} – ${delivery.scheduled_time_end}`
                            : delivery.scheduled_time_start || delivery.scheduled_time_end}
                        </span>
                      </div>
                    )}
                    {delivery.status !== 'delivered' && delivery.status !== 'delivery_failed' && delivery.status !== 'cancelled' && (
                      <div className="mt-2">
                        <DeliveryProgressBar status={delivery.status} />
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Package className="w-3 h-3" />
                      <span>{delivery.items_count}</span>
                    </div>
                    {delivery.route_name && (
                      <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        <MapPin className="w-3 h-3" />
                        <span>{delivery.route_name}</span>
                      </div>
                    )}
                    <button
                      onClick={() => onViewDelivery(delivery)}
                      className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose rounded"
                      title="View details"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    {!['delivered', 'delivery_failed', 'cancelled', 'picked_up'].includes(delivery.status) && (
                      <button
                        onClick={() => onAdvanceStatus(delivery)}
                        disabled={isAdvancing}
                        className="flex items-center gap-1 px-2 py-1 text-xs bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded font-medium"
                      >
                        <ChevronRight className="w-3 h-3" />
                        Advance
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
