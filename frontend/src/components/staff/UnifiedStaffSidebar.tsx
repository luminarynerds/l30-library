/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useMemo, useEffect, useCallback } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ChevronsLeft, ChevronsRight, X, Star, Shield, PersonStanding } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import { useOrganizationFeatures } from '../../contexts/OrganizationFeaturesContext'
import { clsx } from '../../utils/helpers'
import { t } from '@/i18n'
import { useAllHubFavorites } from '@/hooks/useAllHubFavorites'
import { usePendingFlagCount } from '@/hooks/usePendingFlagCount'
import { buildHubRegistry } from '../navigation/hubRegistry'
import { staffNavIndex } from '../header-search/staff-nav-index'
import { FeatureFlag, RailItem, AREAS, FOOTER_ITEMS, ROLE_SIDEBAR_ACCESS, DASHBOARD_PATH } from './staffSidebarMenu'
import { isActive as isActiveShared } from '../../utils/nav'

interface UnifiedStaffSidebarProps {
  isOpen?: boolean
  onClose?: () => void
  isMobile?: boolean
  collapsed?: boolean
  onToggleCollapse?: () => void
  /** Opens the accessibility quick-settings panel (staff shell trigger). */
  onOpenAccessibility?: () => void
}

export const UnifiedStaffSidebar: React.FC<UnifiedStaffSidebarProps> = ({
  isOpen = true,
  onClose,
  isMobile = false,
  collapsed = false,
  onToggleCollapse,
  onOpenAccessibility,
}) => {
  const location = useLocation()
  const { user } = useAuth()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const role = (user?.role || '').toLowerCase()
  const isStaff = !!user
  const pendingFlags = usePendingFlagCount(isStaff)

  const abilities = useMemo(() => {
    const set = new Set(ROLE_SIDEBAR_ACCESS[role] || [])
    if (user?.is_board_member) { set.add('dashboard'); set.add('board') }
    return set
  }, [role, user?.is_board_member])

  const canSee = useCallback((item: RailItem) => {
    if (!abilities.has(item.access)) return false
    if (item.featureFlag && !isFeatureEnabled(item.featureFlag as FeatureFlag)) return false
    return true
  }, [abilities, isFeatureEnabled])

  const areas = useMemo(() => AREAS.filter(canSee), [canSee])
  const footer = useMemo(() => FOOTER_ITEMS.filter(canSee), [canSee])

  // Favorites come from the shared server-side hub-favorites store (the Star
  // toggles on hub pages write to it). Refetch on navigation so a freshly
  // starred item shows up in the rail.
  const { favoritePaths } = useAllHubFavorites(location.pathname)

  const labelByPath = useMemo(() => {
    const map = new Map<string, string>()
    for (const a of AREAS) map.set(a.path, a.label)
    for (const f of FOOTER_ITEMS) map.set(f.path, f.label)
    for (const e of buildHubRegistry()) if (!map.has(e.itemPath)) map.set(e.itemPath, e.itemLabel)
    for (const e of staffNavIndex) if (!map.has(e.route)) map.set(e.route, e.title)
    return map
  }, [])

  const favoriteItems = useMemo(
    () => favoritePaths
      .map((path) => { const label = labelByPath.get(path); return label ? { path, label } : null })
      .filter(Boolean) as { path: string; label: string }[],
    [favoritePaths, labelByPath],
  )

  // One-time cleanup of legacy persisted keys from the old tree sidebar and the
  // abandoned localStorage-favorites experiment.
  useEffect(() => {
    if (!role) return
    for (const k of [
      'staff-sidebar-favorites', 'staff-sidebar-favorites-seeded', 'staff-recents',
      'staff-sidebar-show-full-nav', 'staff-sidebar-expanded-categories', 'staff-sidebar-collapsed-subgroups',
      `staff-sidebar-favorites-${role}`, `staff-sidebar-favorites-seeded-${role}`,
      `staff-recents-${role}`, `staff-sidebar-show-full-nav-${role}`,
      `staff-sidebar-expanded-categories-${role}`, `staff-sidebar-collapsed-subgroups-${role}`,
    ]) localStorage.removeItem(k)
  }, [role])

  const knownPaths = useMemo(
    () => [...areas.map((a) => a.path), ...footer.map((f) => f.path), ...favoritePaths, DASHBOARD_PATH],
    [areas, footer, favoritePaths],
  )

  const isActive = useCallback((path: string): boolean => {
    if (path === '/staff') return location.pathname === '/staff'
    return isActiveShared(location.pathname, path, { knownPaths })
  }, [location.pathname, knownPaths])

  const roleLabel = useMemo(() => {
    const labels: Record<string, string> = {
      super_admin: 'Administrator', admin: 'Administrator', director: 'Director',
      legal: 'Legal', staff: 'Staff', bookmobile: 'Bookmobile', homebond: 'Home Delivery',
    }
    const label = labels[role] || 'Staff'
    return user?.is_board_member ? label + ' / Board' : label
  }, [role, user?.is_board_member])

  const renderLink = (item: Pick<RailItem, "label" | "path" | "badge"> & { icon?: React.ElementType }) => {
    const ItemIcon = item.icon
    const active = isActive(item.path)
    return (
      <Link
        key={item.path}
        to={item.path}
        onClick={isMobile && onClose ? () => setTimeout(onClose, 0) : undefined}
        aria-current={active ? 'page' : undefined}
        title={collapsed ? item.label : undefined}
        className={clsx(
          'flex items-center rounded-xl text-sm font-medium transition-colors',
          collapsed ? 'justify-center px-2 py-2' : 'gap-3 px-3 py-2.5',
          active
            ? 'bg-lsc-rose/10 dark:bg-lsc-rose/15 text-lsc-rose dark:text-lsc-cream font-semibold'
            : 'text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 hover:text-lsc-rose',
        )}
      >
        {ItemIcon && <ItemIcon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />}
        {!collapsed && <span className="whitespace-normal">{item.label}</span>}
        {!collapsed && item.badge === 'pendingFlags' && pendingFlags > 0 && (
          <span
            className="ml-auto min-w-[18px] h-[18px] px-1 flex items-center justify-center text-xs font-bold bg-lsc-rose text-white rounded-full"
            aria-label={t('aria.staffSidebar.pendingFlags', '{count} flagged articles pending review').replace('{count}', String(pendingFlags))}
          >
            {pendingFlags > 99 ? '99+' : pendingFlags}
          </span>
        )}
      </Link>
    )
  }

  if (isMobile && !isOpen) return null

  return (
    <aside
      id={isMobile ? 'mobile-staff-sidebar' : undefined}
      role={isMobile ? 'dialog' : undefined}
      aria-modal={isMobile ? 'true' : undefined}
      aria-label={isMobile ? 'Staff navigation' : undefined}
      className={clsx(
        'bg-lsc-white dark:bg-earth-800 overflow-y-auto overflow-x-hidden scrollbar-thin transition-all duration-200 flex flex-col',
        isMobile
          ? 'fixed inset-0 top-0 z-50 w-72 shadow-lg'
          : collapsed
            ? 'w-16 flex-shrink-0 rounded-xl my-2 ml-3 mr-2'
            : 'w-64 flex-shrink-0 rounded-xl my-2 ml-3 mr-2',
      )}
    >
      <div className="p-4 bg-earth-900 dark:bg-earth-950 text-white rounded-t-2xl">
        <div className="flex items-center justify-between">
          <Link
            to={DASHBOARD_PATH}
            aria-current={isActive(DASHBOARD_PATH) ? 'page' : undefined}
            onClick={isMobile && onClose ? () => setTimeout(onClose, 0) : undefined}
            className="flex items-center gap-3 min-w-0"
            title={collapsed ? 'Dashboard' : undefined}
          >
            <div className="w-10 h-10 bg-lsc-white/10 rounded-xl flex items-center justify-center flex-shrink-0">
              <Shield aria-hidden="true" className="w-6 h-6 text-lsc-cream" />
            </div>
            {!collapsed && (
              <div className="min-w-0">
                <p className="font-semibold truncate">Staff Portal</p>
                <p className="text-sm text-lsc-cream truncate">{roleLabel}</p>
              </div>
            )}
          </Link>
          {isMobile && onClose && (
            <button onClick={onClose} className="p-2 hover:bg-lsc-white/20 rounded-lg transition-colors"
              aria-label={t('aria.staff.closeSidebar')}>
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      <nav className="p-2 flex-1" aria-label="Staff">
        {!collapsed && favoriteItems.length > 0 && (
          <div className="px-1 pb-2 mb-1 border-b border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-2 px-3 py-1.5">
              <Star className="w-3.5 h-3.5 text-lsc-rose fill-current" aria-hidden="true" />
              <span className="text-xs font-semibold uppercase tracking-wider text-lsc-dark/70 dark:text-lsc-cream/60">Favorites</span>
            </div>
            <div className="space-y-0.5">
              {favoriteItems.map((item) => renderLink({ ...item, icon: Star }))}
            </div>
          </div>
        )}

        <div className="space-y-1">
          {areas.map((a) => renderLink(a))}
        </div>
      </nav>

      <div className="mt-auto p-2 border-t border-lsc-border dark:border-earth-700 rounded-b-2xl space-y-1">
        {footer.map((f) => renderLink(f))}
        {onOpenAccessibility && (
          <button onClick={onOpenAccessibility}
            className={clsx('w-full flex items-center rounded-xl px-3 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 transition-colors',
              collapsed ? 'justify-center' : 'gap-2')}
            aria-label="Accessibility settings" title="Accessibility settings">
            <PersonStanding className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            {!collapsed && <span>Accessibility</span>}
          </button>
        )}
        {!isMobile && onToggleCollapse && (
          <button onClick={onToggleCollapse}
            className={clsx('w-full flex items-center rounded-xl px-3 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 transition-colors',
              collapsed ? 'justify-center' : 'gap-2')}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
            {collapsed ? <ChevronsRight className="w-4 h-4" /> : (<><ChevronsLeft className="w-4 h-4" /><span>Collapse</span></>)}
          </button>
        )}
      </div>
    </aside>
  )
}

export default UnifiedStaffSidebar
