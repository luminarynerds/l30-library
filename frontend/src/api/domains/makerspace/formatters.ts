/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type {
  ResourceStatus,
  ReservationStatus,
  JobStatus,
  ResourceType,
  WorkshopLevel,
  WaitlistStatus,
  RegistrationStatus,
  CertificationStatus,
} from './makerspace-api'

export function getStatusColor(status: ResourceStatus | ReservationStatus | JobStatus): string {
  const colors: Record<string, string> = {
    available: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
    in_use: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    maintenance: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    out_of_order: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    reserved: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
    retired: 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300',
    pending: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    confirmed: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
    checked_in: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
    completed: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
    cancelled: 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300',
    no_show: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    expired: 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300',
    submitted: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
    pending_review: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    rejected: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    approved: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
    queued: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
    in_progress: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    paused: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    failed: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    ready_pickup: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
    picked_up: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
  }
  return colors[status] || 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300'
}

export function formatResourceType(type: ResourceType): string {
  const labels: Record<ResourceType, string> = {
    '3d_printer': '3D Printer',
    laser_cutter: 'Laser Cutter',
    cnc_router: 'CNC Router',
    vinyl_cutter: 'Vinyl Cutter',
    embroidery_machine: 'Embroidery Machine',
    sewing_machine: 'Sewing Machine',
    soldering_station: 'Soldering Station',
    electronics_workbench: 'Electronics Workbench',
    woodworking_station: 'Woodworking Station',
    recording_studio: 'Recording Studio',
    video_editing_station: 'Video Editing Station',
    vr_station: 'VR Station',
    other: 'Other',
  }
  return labels[type] || type
}

export function formatStatus(status: string): string {
  return status.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

export function formatWorkshopLevel(level: WorkshopLevel): string {
  const labels: Record<WorkshopLevel, string> = {
    beginner: 'Beginner',
    intermediate: 'Intermediate',
    advanced: 'Advanced',
    all_levels: 'All Levels',
  }
  return labels[level] || level
}

export function getWorkshopLevelColor(level: WorkshopLevel): string {
  const colors: Record<WorkshopLevel, string> = {
    beginner: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
    intermediate: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    advanced: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    all_levels: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
  }
  return colors[level] || 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300'
}

export function getWaitlistStatusColor(status: WaitlistStatus): string {
  const colors: Record<WaitlistStatus, string> = {
    waiting: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    notified: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
    expired: 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300',
    cancelled: 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300',
    fulfilled: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
  }
  return colors[status] || 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300'
}

export function getRegistrationStatusColor(status: RegistrationStatus): string {
  const colors: Record<RegistrationStatus, string> = {
    registered: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
    waitlisted: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    confirmed: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
    attended: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
    no_show: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    cancelled: 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300',
  }
  return colors[status] || 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300'
}

export function getCertificationStatusColor(status: CertificationStatus): string {
  const colors: Record<CertificationStatus, string> = {
    active: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400',
    pending: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    expired: 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300',
    suspended: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    revoked: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400',
  }
  return colors[status] || 'bg-earth-100 text-earth-700 dark:bg-earth-900/30 dark:text-earth-300'
}
