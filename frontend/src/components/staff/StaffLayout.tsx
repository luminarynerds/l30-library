/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { Menu, X, Loader2 } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { useScrollLock } from '../../hooks/useScrollLock'
import { useAuth } from '../../contexts/AuthContext'
import { usePreferences } from '../../contexts/PreferencesContext'
import { UnifiedStaffSidebar } from './UnifiedStaffSidebar'
import { QuickAccessibilityWidget } from '../../features/accessibility/components/QuickAccessibilityWidget'
import { useLocation } from 'react-router-dom'
import { KnowledgeBaseHelpButton } from '../knowledge-base/KnowledgeBaseHelpButton'

interface StaffLayoutProps {
  children: React.ReactNode
  title?: string
  subtitle?: string
  actions?: React.ReactNode
  loading?: boolean
  /** When the caller renders its own desktop title header (e.g. AdminShell with an
   *  icon), skip StaffLayout's default one so the page has a single h1. The mobile
   *  sticky bar and everything else are unaffected. */
  hideDefaultHeader?: boolean
}

export const StaffLayout: React.FC<StaffLayoutProps> = ({
  children,
  title,
  subtitle,
  actions,
  loading = false,
  hideDefaultHeader = false,
}) => {
  const { user, isLoading: authLoading } = useAuth()
  const { preferences, updatePreferences } = usePreferences()
  const sidebarCollapsed = preferences.sidebar_collapsed ?? false
  const location = useLocation()

  const toggleSidebarCollapse = async () => {
    await updatePreferences({ sidebar_collapsed: !sidebarCollapsed })
  }

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [a11yOpen, setA11yOpen] = useState(false)
  const openAccessibility = () => {
    setSidebarOpen(false)
    setA11yOpen(true)
  }

  useScrollLock(sidebarOpen)

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  if (!user || (user.role === 'patron' && !user.is_board_member)) {
    return null
  }

  return (
    <div className="flex h-full min-h-screen overflow-hidden">
      {/* Full sidebar at lg+ */}
      <div
        className={`hidden lg:flex lg:flex-col lg:sticky lg:top-0 lg:self-start lg:max-h-screen lg:overflow-y-auto lg:overflow-x-hidden transition-all duration-200 ${
          sidebarCollapsed ? 'lg:w-24' : 'lg:w-[18rem]'
        }`}
      >
        <UnifiedStaffSidebar
          collapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebarCollapse}
          onOpenAccessibility={openAccessibility}
        />
      </div>

      {/* Collapsed rail at md (768-1023px): icons only, no toggle (tap a row to navigate, hamburger still opens overlay below md) */}
      <div className="hidden md:flex lg:hidden md:flex-col md:sticky md:top-0 md:z-10 md:self-start md:max-h-screen md:overflow-y-auto md:overflow-x-hidden md:w-24 transition-all duration-200">
        <UnifiedStaffSidebar collapsed={true} onOpenAccessibility={openAccessibility} />
      </div>

      {/* Mobile sidebar - modal overlay (<md) */}
      {sidebarOpen && (
        <FocusTrap
          active={sidebarOpen}
          focusTrapOptions={{
            initialFocus: false,
            allowOutsideClick: true,
            escapeDeactivates: true,
            returnFocusOnDeactivate: true,
            onDeactivate: () => setSidebarOpen(false),
          }}
        >
          <div>
            {/* Backdrop — click to close */}
            <div
              className="fixed inset-0 bg-black/50 z-40 lg:hidden"
              onClick={() => setSidebarOpen(false)}
              aria-hidden="true"
            />
            <UnifiedStaffSidebar
              isOpen={sidebarOpen}
              onClose={() => setSidebarOpen(false)}
              isMobile={true}
              onOpenAccessibility={openAccessibility}
            />
          </div>
        </FocusTrap>
      )}

      {/* Main content area — note: <main id="main-content"> is already in the outer Layout wrapper */}
      <div className="flex-1 min-w-0 overflow-auto">
        {/* Mobile header with hamburger toggle */}
        <header className="lg:hidden sticky top-0 z-20 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 px-4 py-3 flex items-center justify-between" aria-label="Staff portal mobile header">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={title || 'Staff Portal'}>
            {title || 'Staff Portal'}
          </h2>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="inline-flex items-center gap-2 min-h-[44px] px-3 py-2 rounded-lg border border-lsc-rose/40 bg-lsc-rose/5 text-lsc-rose font-medium hover:bg-lsc-rose/10 focus-visible:ring-2 focus-visible:ring-lsc-rose transition-colors dark:text-lsc-rose-light dark:border-lsc-rose-light/40 dark:bg-lsc-rose/10"
            aria-label={sidebarOpen ? 'Close staff menu' : 'Open staff menu'}
            aria-expanded={sidebarOpen}
            aria-controls="mobile-staff-sidebar"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            <span className="text-sm">{sidebarOpen ? 'Close' : 'Menu'}</span>
          </button>
        </header>

        {/* Page content */}
        <div className="p-4 lg:p-6 space-y-6">
          {/* Page header (desktop - mobile uses sticky bar above) */}
          {!hideDefaultHeader && (title || actions) && (
            <div className="hidden lg:flex items-center justify-between">
              <div>
                {title && (
                  <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                    {title}
                  </h1>
                )}
                {subtitle && (
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{subtitle}</p>
                )}
              </div>
              {actions && <div className="flex items-center gap-2">{actions}</div>}
            </div>
          )}

          {/* Mobile subtitle + actions (below sticky bar) */}
          {(subtitle || actions) && (
            <div className="lg:hidden space-y-2">
              {subtitle && (
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{subtitle}</p>
              )}
              {actions && <div className="flex items-center gap-2">{actions}</div>}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
            </div>
          ) : (
            children
          )}
        </div>
      </div>

      {location.pathname !== '/staff/knowledge-base' && <KnowledgeBaseHelpButton />}

      {/* Accessibility quick-settings panel for the staff shell. Controlled by
          the sidebar trigger; floats fixed regardless of DOM position. */}
      <QuickAccessibilityWidget
        open={a11yOpen}
        onOpenChange={setA11yOpen}
        showCalmSession
        onOpenSettings={() => { window.location.href = '/accessibility' }}
      />
    </div>
  )
}

export default StaffLayout
