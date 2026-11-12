/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Truck, Search, Loader2, Eye } from 'lucide-react';
import type { Delivery, DeliveryStatus, DeliveryRoute } from '../../api/homeDeliveryApi';
import { DeliveryStatusBadge } from './DeliveryStatusBadge';
import { formatDate } from './delivery-data';
import { useTranslation } from '@/i18n';

interface AllDeliveriesTabProps {
  deliveries: Delivery[];
  loading: boolean;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  statusFilter: DeliveryStatus | '';
  onStatusFilterChange: (s: DeliveryStatus | '') => void;
  selectedDeliveryIds: number[];
  onToggleSelection: (id: number) => void;
  routes: DeliveryRoute[];
  onAssignToRoute: (routeId: number) => void;
  onViewDelivery: (delivery: Delivery) => void;
  onUpdateStatus: (id: number, status: DeliveryStatus) => void;
  onUpdateStatusWithReason: (id: number, status: DeliveryStatus) => void;
}

export function AllDeliveriesTab({
  deliveries,
  loading,
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  selectedDeliveryIds,
  onToggleSelection,
  routes,
  onAssignToRoute,
  onViewDelivery,
  onUpdateStatus,
  onUpdateStatusWithReason,
}: AllDeliveriesTabProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
            <input
              type="text"
              placeholder={t('placeholder.homeDelivery.searchPatron')}
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              aria-label={t('homeDelivery.searchDeliveriesByPatron')}
              className="pl-10 pr-4 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose text-lsc-dark dark:text-lsc-cream text-sm"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value as DeliveryStatus | '')}
            aria-label={t('homeDelivery.filterByDeliveryStatus')}
            className="px-3 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          >
            <option value="">All Statuses</option>
            <option value="scheduled">Scheduled</option>
            <option value="items_selected">Items Selected</option>
            <option value="packed">Packed</option>
            <option value="out_for_delivery">Out for Delivery</option>
            <option value="delivered">Delivered</option>
            <option value="delivery_failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
          {selectedDeliveryIds.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {selectedDeliveryIds.length} selected
              </span>
              <select
                onChange={(e) => {
                  const routeId = Number(e.target.value);
                  if (routeId) {
                    onAssignToRoute(routeId);
                    e.target.value = '';
                  }
                }}
                className="px-3 py-1.5 text-sm bg-lsc-rose text-white rounded-lg"
              >
                <option value="">Assign to Route...</option>
                {routes.filter((r) => ['draft', 'planned'].includes(r.status)).map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : deliveries.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-lsc-dark/70 dark:text-lsc-cream/70 border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/50">
                  <th className="px-4 py-3"><span className="sr-only">Select</span></th>
                  <th className="px-4 py-3 font-medium">Patron</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Time</th>
                  <th className="px-4 py-3 font-medium">Items</th>
                  <th className="px-4 py-3 font-medium">Route</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {deliveries.map((delivery) => (
                  <tr
                    key={delivery.id}
                    className={`hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors ${
                      selectedDeliveryIds.includes(delivery.id) ? 'bg-lsc-rose/5' : ''
                    }`}
                  >
                    <td className="px-4 py-3">
                      {!delivery.route_id && ['scheduled', 'items_selected'].includes(delivery.status) && (
                        <input
                          type="checkbox"
                          checked={selectedDeliveryIds.includes(delivery.id)}
                          onChange={() => onToggleSelection(delivery.id)}
                          className="w-4 h-4 text-lsc-rose rounded border-lsc-border"
                          aria-label={`Select delivery for ${delivery.patron_name}`}
                        />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">{delivery.patron_name}</p>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{delivery.patron_library_card}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <DeliveryStatusBadge status={delivery.status} />
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">
                      {formatDate(delivery.scheduled_date)}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {delivery.scheduled_time_start
                        ? `${delivery.scheduled_time_start}${delivery.scheduled_time_end ? ` – ${delivery.scheduled_time_end}` : ''}`
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">
                      {delivery.items_count ?? 0}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {delivery.route_name ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => onViewDelivery(delivery)}
                          className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose rounded"
                          title="View details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {delivery.status === 'scheduled' && (
                          <button
                            onClick={() => onUpdateStatus(delivery.id, 'items_selected')}
                            className="px-2 py-1 text-xs bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded"
                          >
                            Select Items
                          </button>
                        )}
                        {delivery.status === 'items_selected' && (
                          <button
                            onClick={() => onUpdateStatus(delivery.id, 'packed')}
                            className="px-2 py-1 text-xs bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded"
                          >
                            Pack
                          </button>
                        )}
                        {delivery.status === 'packed' && (
                          <button
                            onClick={() => onUpdateStatus(delivery.id, 'out_for_delivery')}
                            className="px-2 py-1 text-xs bg-category-600 hover:bg-category-700 text-white rounded"
                          >
                            Dispatch
                          </button>
                        )}
                        {delivery.status === 'out_for_delivery' && (
                          <>
                            <button
                              onClick={() => onUpdateStatus(delivery.id, 'delivered')}
                              className="px-2 py-1 text-xs bg-status-success-600 hover:bg-status-success-700 text-white rounded"
                            >
                              Delivered
                            </button>
                            <button
                              onClick={() => onUpdateStatusWithReason(delivery.id, 'delivery_failed')}
                              className="px-2 py-1 text-xs bg-status-danger-600 hover:bg-status-danger-700 text-white rounded"
                            >
                              Failed
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
            <Truck className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No deliveries found</p>
          </div>
        )}
      </div>
    </div>
  );
}
