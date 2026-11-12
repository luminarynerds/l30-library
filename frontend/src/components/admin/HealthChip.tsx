/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { CheckCircle2, AlertTriangle, XCircle, Circle } from 'lucide-react'
import { StatusBadge, type StatusTone } from './StatusBadge'

export type HealthStatus = 'ok' | 'warn' | 'err' | 'unknown'

const STATUS_MAP: Record<
  HealthStatus,
  { tone: StatusTone; icon: React.ElementType; defaultLabel: string }
> = {
  ok: { tone: 'success', icon: CheckCircle2, defaultLabel: 'Healthy' },
  warn: { tone: 'warning', icon: AlertTriangle, defaultLabel: 'Degraded' },
  err: { tone: 'danger', icon: XCircle, defaultLabel: 'Down' },
  unknown: { tone: 'muted', icon: Circle, defaultLabel: 'Unknown' },
}

export interface HealthChipProps {
  status: HealthStatus
  label?: string
  size?: 'sm' | 'md'
}

export function HealthChip({ status, label, size = 'md' }: HealthChipProps): React.ReactElement {
  const { tone, icon, defaultLabel } = STATUS_MAP[status]
  return <StatusBadge label={label ?? defaultLabel} tone={tone} icon={icon} size={size} />
}
