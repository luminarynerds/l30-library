/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Heart, AlertTriangle, Droplet, AlertCircle, Activity, Shield } from 'lucide-react';

export function getEmergencyIcon(type: string) {
  const iconProps = { className: 'w-5 h-5' };
  switch (type) {
    case 'cardiac_event':
      return <Heart {...iconProps} className="w-5 h-5 text-status-danger-600" />;
    case 'respiratory_distress':
      return <AlertTriangle {...iconProps} className="w-5 h-5 text-status-warning-600" />;
    case 'severe_injury':
      return <Droplet {...iconProps} className="w-5 h-5 text-status-danger-500" />;
    case 'allergic_reaction':
      return <AlertCircle {...iconProps} className="w-5 h-5 text-category-600" />;
    case 'unconscious_unresponsive':
      return <Activity {...iconProps} className="w-5 h-5 text-status-danger-700 dark:text-status-danger-300" />;
    case 'acute_mental_health':
      return <Shield {...iconProps} className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />;
    default:
      return <AlertTriangle {...iconProps} className="w-5 h-5 text-status-warning-600" />;
  }
}

export function getSeverityColor(severity: string) {
  switch (severity) {
    case 'life_threatening':
      return 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300 border-status-danger-300 dark:border-status-danger-700';
    case 'urgent':
      return 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 border-status-warning-300 dark:border-status-warning-700';
    case 'serious':
      return 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 border-status-warning-300 dark:border-status-warning-700';
    default:
      return 'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100 border-lsc-border dark:border-earth-700';
  }
}
