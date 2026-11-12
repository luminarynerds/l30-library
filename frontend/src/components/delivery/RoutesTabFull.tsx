/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Plus, MapPin, Truck, Package, Clock, Eye, Loader2 } from 'lucide-react';
import type { DeliveryRoute, RouteStatus } from '../../api/homeDeliveryApi';
import { DeliveryStatusBadge } from './DeliveryStatusBadge';
import { formatDate } from './delivery-data';
import { useTranslation } from '@/i18n';

interface RoutesTabFullProps {
  routes: DeliveryRoute[];
  loading: boolean;
  statusFilter: RouteStatus | '';
  onStatusFilterChange: (s: RouteStatus | '') => void;
  onCreateRoute: () => void;
  onViewRoute: (route: DeliveryRoute) => void;
  onOptimizeRoute: (id: number) => void;
  onUpdateRouteStatus: (id: number, status: RouteStatus) => void;
  isOptimizing: boolean;
  isUpdating: boolean;
}

export function RoutesTabFull({
  routes,
  loading,
  statusFilter,
  onStatusFilterChange,
  onCreateRoute,
  onViewRoute,
  onOptimizeRoute,
  onUpdateRouteStatus,
  isOptimizing,
  isUpdating,
}: RoutesTabFullProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <select
          value={statusFilter}
          onChange={(e) => onStatusFilterChange(e.target.value as RouteStatus | '')}
          aria-label={t('homeDelivery.filterRoutesByStatus')}
          className="px-3 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="planned">Planned</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <button
          onClick={onCreateRoute}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm font-medium"
        >
          <Plus className="w-4 h-4" /> Create Route
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : routes.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {routes.map((route) => (
            <div
              key={route.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{route.name}</h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{formatDate(route.date)}</p>
                </div>
                <DeliveryStatusBadge status={route.status} />
              </div>

              <div className="space-y-2 text-sm mb-4">
                {route.volunteer_name && (
                  <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="font-medium">Volunteer:</span>
                    <span>{route.volunteer_name}</span>
                  </div>
                )}
                <div className="flex items-center justify-between text-lsc-dark/70 dark:text-lsc-cream/70">
                  <div className="flex items-center gap-1">
                    <Truck className="w-4 h-4" />
                    <span>{route.completed_stops}/{route.total_stops} stops</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Package className="w-4 h-4" />
                    <span>{route.total_items} items</span>
                  </div>
                </div>
                {route.estimated_duration_minutes && (
                  <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Clock className="w-4 h-4" />
                    <span>~{route.estimated_duration_minutes} min</span>
                  </div>
                )}
                {route.planned_start_time && (
                  <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Clock className="w-4 h-4" />
                    <span>
                      {route.planned_start_time}
                      {route.planned_end_time && ` – ${route.planned_end_time}`}
                    </span>
                  </div>
                )}
                {route.total_stops > 0 && (
                  <div className="w-full bg-lsc-border dark:bg-earth-700 rounded-full h-1.5">
                    <div
                      className="bg-lsc-rose h-1.5 rounded-full"
                      style={{ width: `${Math.round((route.completed_stops / route.total_stops) * 100)}%` }}
                    />
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-2 pt-3 border-t border-lsc-border dark:border-earth-700">
                <button
                  onClick={() => onViewRoute(route)}
                  className="flex items-center gap-1 px-2 py-1 text-xs border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded hover:bg-lsc-cream dark:hover:bg-earth-700"
                >
                  <Eye className="w-3 h-3" /> View
                </button>
                {route.status === 'draft' && (
                  <>
                    <button
                      onClick={() => onOptimizeRoute(route.id)}
                      disabled={isOptimizing}
                      className="px-2 py-1 text-xs bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded"
                    >
                      Optimize
                    </button>
                    <button
                      onClick={() => onUpdateRouteStatus(route.id, 'planned')}
                      disabled={isUpdating}
                      className="px-2 py-1 text-xs bg-status-success-600 hover:bg-status-success-700 text-white rounded"
                    >
                      Finalize
                    </button>
                  </>
                )}
                {route.status === 'planned' && (
                  <button
                    onClick={() => onUpdateRouteStatus(route.id, 'in_progress')}
                    disabled={isUpdating}
                    className="px-2 py-1 text-xs bg-category-600 hover:bg-category-700 text-white rounded"
                  >
                    Start
                  </button>
                )}
                {route.status === 'in_progress' && (
                  <button
                    onClick={() => onUpdateRouteStatus(route.id, 'completed')}
                    disabled={isUpdating}
                    className="px-2 py-1 text-xs bg-status-success-600 hover:bg-status-success-700 text-white rounded"
                  >
                    Complete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
          <MapPin className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No routes found</p>
          <button
            onClick={onCreateRoute}
            className="mt-3 text-lsc-rose hover:text-lsc-rose/80 text-sm font-medium"
          >
            Create your first route
          </button>
        </div>
      )}
    </div>
  );
}
