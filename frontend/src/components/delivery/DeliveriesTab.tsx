/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Search, Plus } from 'lucide-react';
import { useTranslation } from '@/i18n';
import type { Delivery, DeliveryStatus } from '../../api/homeDeliveryApi';

interface DeliveriesTabProps {
  deliveries: Delivery[];
  searchQuery: string;
  deliveryFilter: DeliveryStatus | '';
  onSearchChange: (q: string) => void;
  onFilterChange: (f: DeliveryStatus | '') => void;
  onScheduleDelivery: () => void;
  onUpdateStatus: (delivery: Delivery, status: DeliveryStatus) => void;
  getStatusColor: (status: string) => string;
}

export function DeliveriesTab({
  deliveries,
  searchQuery,
  deliveryFilter,
  onSearchChange,
  onFilterChange,
  onScheduleDelivery,
  onUpdateStatus,
  getStatusColor,
}: DeliveriesTabProps) {
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
            value={deliveryFilter}
            onChange={(e) => onFilterChange(e.target.value as DeliveryStatus | '')}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500"
          >
            <option value="">All Statuses</option>
            <option value="scheduled">Scheduled</option>
            <option value="items_selected">Items Selected</option>
            <option value="packed">Packed</option>
            <option value="out_for_delivery">Out for Delivery</option>
            <option value="delivered">Delivered</option>
          </select>
        </div>
        <button
          onClick={onScheduleDelivery}
          className="flex items-center gap-2 px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700"
        >
          <Plus className="w-4 h-4" />
          Schedule Delivery
        </button>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow overflow-hidden">
        <table className="w-full divide-y divide-earth-200 dark:divide-earth-700">
          <thead className="bg-earth-50 dark:bg-earth-900">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Patron</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Scheduled</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Items</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Route</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-earth-200 dark:divide-earth-700">
            {deliveries.map((delivery) => (
              <tr key={delivery.id} className="hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                <td className="px-6 py-4">
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">{delivery.patron_name}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{delivery.patron_library_card}</p>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(delivery.status)}`}>
                    {delivery.status.replace(/_/g, ' ')}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {new Date(delivery.scheduled_date).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{delivery.items_count}</td>
                <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{delivery.route_name || '-'}</td>
                <td className="px-6 py-4">
                  <div className="flex gap-2">
                    {delivery.status === 'scheduled' && (
                      <button
                        onClick={() => onUpdateStatus(delivery, 'items_selected')}
                        className="text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light text-sm"
                      >
                        Select Items
                      </button>
                    )}
                    {delivery.status === 'items_selected' && (
                      <button
                        onClick={() => onUpdateStatus(delivery, 'packed')}
                        className="text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light text-sm"
                      >
                        Pack
                      </button>
                    )}
                    {delivery.status === 'packed' && (
                      <button
                        onClick={() => onUpdateStatus(delivery, 'out_for_delivery')}
                        className="text-category-600 hover:text-category-800 dark:text-category-300 text-sm"
                      >
                        Dispatch
                      </button>
                    )}
                    {delivery.status === 'out_for_delivery' && (
                      <button
                        onClick={() => onUpdateStatus(delivery, 'delivered')}
                        className="text-status-success-600 hover:text-status-success-800 dark:text-status-success-300 text-sm"
                      >
                        Mark Delivered
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {deliveries.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                  No deliveries found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
