/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Award } from 'lucide-react';
import { VolunteerStatus } from '../../../api/homeDeliveryApi';
import { STATUS_COLORS, RECOGNITION_COLORS } from './volunteers-data';

export function VolunteerStatusBadge({ status }: { status: VolunteerStatus }) {
  const label = status.replace(/_/g, ' ');
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[status] ?? 'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100'}`}>
      {label}
    </span>
  );
}

export function RecognitionBadge({ level }: { level: string }) {
  if (!level || level === 'none') return null;
  const colorClass = RECOGNITION_COLORS[level.toLowerCase()] ?? RECOGNITION_COLORS.bronze;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
      <Award className="w-3 h-3" />
      {level.charAt(0).toUpperCase() + level.slice(1)}
    </span>
  );
}
