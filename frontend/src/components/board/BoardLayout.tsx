/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link, useLocation, Outlet } from 'react-router-dom'
import Footer from '../Footer'
import { Menu, X, Building2, Users, Calendar, ScrollText, Gavel, FileText, MessageSquare } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import { usePreferences } from '../../contexts/PreferencesContext'
import { UnifiedStaffSidebar } from '../staff/UnifiedStaffSidebar'

const BOARD_NAV_ITEMS = [
  { label: 'Dashboard', path: '/board', icon: Building2 },
  { label: 'Members', path: '/board/members', icon: Users },
  { label: 'Meetings', path: '/board/meetings', icon: Calendar },
  { label: 'Minutes', path: '/board/minutes', icon: ScrollText },
  { label: 'Motions', path: '/board/motions', icon: Gavel },
  { label: 'Committees', path: '/board/committees', icon: Building2 },
  { label: 'Documents', path: '/board/documents', icon: FileText },
  { label: 'Public Comments', path: '/board/public-comments', icon: MessageSquare },
]

export default function BoardLayout() {
  const { user } = useAuth()
  const userRole = (user?.role || '').toLowerCase()
  const isStaff = user && userRole !== 'patron'

  if (isStaff) {
    return <StaffBoardLayout />
  }

  return <PublicBoardLayout />
}

function StaffBoardLayout() {
  const { preferences, updatePreferences } = usePreferences()
  const sidebarCollapsed = preferences?.sidebar_collapsed ?? false
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const toggleSidebarCollapse = async () => {
    await updatePreferences({ sidebar_collapsed: !sidebarCollapsed })
  }

  return (
    <div className="flex h-full min-h-screen overflow-hidden">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}
      <div className={`hidden lg:flex lg:flex-col lg:sticky lg:top-0 lg:self-start lg:max-h-screen lg:overflow-y-auto lg:overflow-x-hidden transition-all duration-200 ${sidebarCollapsed ? 'lg:w-24' : 'lg:w-[18rem]'}`}>
        <UnifiedStaffSidebar collapsed={sidebarCollapsed} onToggleCollapse={toggleSidebarCollapse} />
      </div>
      <UnifiedStaffSidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} isMobile={true} />
      <div className="flex-1 min-w-0 overflow-auto">
        <div className="lg:hidden sticky top-0 z-20 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 px-4 py-3 flex items-center justify-between">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream truncate">Board</h2>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg transition-colors"
            aria-label={sidebarOpen ? 'Close navigation' : 'Open navigation'}>
            {sidebarOpen ? <X className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" /> : <Menu className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />}
          </button>
        </div>
        <div className="p-4 lg:p-6">
          <Outlet />
        </div>
      </div>
    </div>
  )
}

function PublicBoardLayout() {
  const location = useLocation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  const isActive = (path: string) => {
    if (path === '/board') return location.pathname === '/board' || location.pathname === '/board/'
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }

  return (
    <div className="min-h-screen">
      <nav className="bg-earth-900 dark:bg-earth-950 text-white" aria-label="Board navigation">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-12">
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              <span className="font-semibold text-sm">Board of Trustees</span>
            </div>
            <button
              onClick={() => setMobileNavOpen(!mobileNavOpen)}
              className="sm:hidden p-1.5 hover:bg-lsc-white/10 rounded-lg transition-colors"
              aria-label={mobileNavOpen ? 'Close board menu' : 'Open board menu'} 
              aria-expanded={mobileNavOpen}>
              {mobileNavOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
          <div className="hidden sm:flex gap-1 -mb-px overflow-x-auto">
            {BOARD_NAV_ITEMS.map((item) => {
              const Icon = item.icon
              const active = isActive(item.path)
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${active ? 'border-lsc-rose text-white' : 'border-transparent text-white/60 hover:text-white/80 hover:border-white/30'}`}>
                  <Icon className="w-4 h-4" aria-hidden="true" />
                  {item.label}
                </Link>
              )
            })}
          </div>
        </div>
        {mobileNavOpen && (
          <div className="sm:hidden border-t border-white/10 px-4 py-2 space-y-1">
            {BOARD_NAV_ITEMS.map((item) => {
              const Icon = item.icon
              const active = isActive(item.path)
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileNavOpen(false)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${active ? 'bg-lsc-rose/20 text-white font-medium' : 'text-white/70 hover:bg-lsc-white/10 hover:text-white'}`}>
                  <Icon className="w-4 h-4" aria-hidden="true" />
                  {item.label}
                </Link>
              )
            })}
          </div>
        )}
      </nav>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </div>
      <Footer />
    </div>
  )
}
