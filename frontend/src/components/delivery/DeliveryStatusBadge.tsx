/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { getStatusColor } from './delivery-data';

export function DeliveryStatusBadge({ status }: { status: string }) {
  const label = status.replace(/_/g, ' ');
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(status)}`}>
      {label}
    </span>
  );
}

export function DeliveryProgressBar({ status }: { status: string }) {
  const steps = ['scheduled', 'items_selected', 'packed', 'out_for_delivery', 'delivered'];
  const currentIndex = steps.indexOf(status);
  return (
    <div className="flex items-center gap-1 w-full">
      {steps.map((step, idx) => (
        <div key={step} className="flex items-center flex-1">
          <div
            className={`h-2 flex-1 rounded-full transition-colors ${
              idx <= currentIndex
                ? 'bg-lsc-rose'
                : 'bg-lsc-border dark:bg-earth-700'
            }`}
          />
          {idx < steps.length - 1 && (
            <div className={`w-2 h-2 rounded-full mx-0.5 ${idx < currentIndex ? 'bg-lsc-rose' : 'bg-lsc-border dark:bg-earth-700'}`} />
          )}
        </div>
      ))}
    </div>
  );
}
