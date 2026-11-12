/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Plus, UserCheck, Truck, Package, Clock } from 'lucide-react';
import type { DeliveryRoute } from '../../api/homeDeliveryApi';

interface RoutesTabProps {
  routes: DeliveryRoute[];
  onCreateRoute: () => void;
  getStatusColor: (status: string) => string;
}

export function RoutesTab({ routes, onCreateRoute, getStatusColor }: RoutesTabProps) {
  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={onCreateRoute}
          className="flex items-center gap-2 px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700"
        >
          <Plus className="w-4 h-4" />
          Create Route
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {routes.map((route) => (
          <div key={route.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{route.name}</h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{new Date(route.date).toLocaleDateString()}</p>
              </div>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(route.status)}`}>
                {route.status.replace('_', ' ')}
              </span>
            </div>

            <div className="space-y-2 text-sm">
              {route.volunteer_name && (
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <UserCheck className="w-4 h-4" />
                  <span>{route.volunteer_name}</span>
                </div>
              )}
              <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                <Truck className="w-4 h-4" />
                <span>
                  {route.completed_stops}/{route.total_stops} stops completed
                </span>
              </div>
              <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                <Package className="w-4 h-4" />
                <span>{route.total_items} total items</span>
              </div>
              {route.estimated_duration_minutes && (
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <Clock className="w-4 h-4" />
                  <span>{route.estimated_duration_minutes} min estimated</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
