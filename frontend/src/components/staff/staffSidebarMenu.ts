/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Zap, Library, Heart, BarChart3, Building2, Settings, HelpCircle, LayoutDashboard } from 'lucide-react'
import type { OrganizationFeatures } from '../../contexts/OrganizationFeaturesContext'

export type FeatureFlag = keyof OrganizationFeatures

export interface RailItem {
  label: string
  path: string
  icon: React.ElementType
  /** ROLE_SIDEBAR_ACCESS ability that must be present for this item to render. */
  access: string
  featureFlag?: FeatureFlag
  badge?: 'pendingFlags'
}

/** Clickable logo target. */
export const DASHBOARD_PATH = '/staff'
export const DASHBOARD_ICON = LayoutDashboard

// Role -> ability mapping (single source of truth). Lowercase backend UserRole.
// Board membership is additive — handled in the sidebar component.
export const ROLE_SIDEBAR_ACCESS: Record<string, string[]> = {
  super_admin: ['help', 'dashboard', 'front_desk', 'collection', 'library_life', 'board', 'reports_outreach', 'system', 'configuration'],
  admin:       ['help', 'dashboard', 'front_desk', 'collection', 'library_life', 'board', 'reports_outreach', 'system', 'configuration'],
  director:    ['help', 'dashboard', 'front_desk', 'collection', 'library_life', 'board', 'reports_outreach', 'system', 'configuration'],
  legal:       ['help', 'dashboard', 'front_desk', 'collection', 'library_life', 'board', 'reports_outreach'],
  staff:       ['help', 'dashboard', 'front_desk', 'collection', 'library_life', 'reports_outreach'],
  bookmobile:  ['help', 'dashboard', 'front_desk', 'collection', 'library_life', 'reports_outreach'],
  homebond:    ['help', 'dashboard', 'front_desk', 'collection', 'library_life', 'reports_outreach'],
}

// Primary areas — the only fixed body list. Each routes to an existing hub page.
export const AREAS: RailItem[] = [
  { label: 'Front Desk',   path: '/staff/front-desk-hub', icon: Zap,       access: 'front_desk',      featureFlag: 'front_desk_enabled' },
  { label: 'Collection',   path: '/staff/collection-hub', icon: Library,   access: 'collection',      featureFlag: 'collection_management_enabled' },
  { label: 'Programs',     path: '/staff/library-hub',    icon: Heart,     access: 'library_life',    featureFlag: 'community_features_enabled' },
  { label: 'Reports',      path: '/staff/report-hub',     icon: BarChart3, access: 'reports_outreach' },
  { label: 'Board',        path: '/staff/board-hub',      icon: Building2, access: 'board',            featureFlag: 'board_features_enabled' },
]

// Footer utility links (Accessibility + Collapse are rendered by the component).
export const FOOTER_ITEMS: RailItem[] = [
  { label: 'Admin', path: '/staff/admin/settings', icon: Settings,    access: 'configuration' },
  { label: 'Help',  path: '/staff/knowledge-base', icon: HelpCircle,  access: 'help', badge: 'pendingFlags' },
]
