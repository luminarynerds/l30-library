/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Link, useLocation } from 'react-router-dom'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import {
  User, BookMarked, FileText, Bell, Feather, Printer,
  Briefcase, Settings,
  LogOut, LogIn, CreditCard, ChevronDown, ChevronRight, RefreshCw, Loader2, Monitor,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'
import { useTranslation } from '../i18n/I18nContext'
import { clsx } from '../utils/helpers'
import { getMyCheckouts, renewCheckout, type Checkout } from '../api/domains/circulation/circulation-api'

interface AccountDropdownProps {
  onOpenLogin: () => void
  onOpenRegister: () => void
}

interface AccountItem {
  to: string
  labelKey: string
  fallback?: string
  icon: React.ElementType
  show: boolean
}

const linkItemClasses =
  'flex items-center justify-between gap-3 px-4 py-2.5 text-sm text-lsc-dark dark:text-lsc-cream ' +
  'data-[highlighted]:bg-lsc-rose/10 dark:data-[highlighted]:bg-lsc-rose/20 ' +
  'outline-none transition-colors cursor-pointer'

function LinkItem({ item, label }: { item: AccountItem; label: string }): React.ReactElement {
  const Icon = item.icon
  return (
    <DropdownMenu.Item asChild>
      <Link to={item.to} className={linkItemClasses}>
        <span className="flex items-center gap-3">
          <Icon aria-hidden="true" className="w-4 h-4" />
          {label}
        </span>
        <ChevronRight aria-hidden="true" className="w-4 h-4 opacity-50" />
      </Link>
    </DropdownMenu.Item>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }): React.ReactElement {
  return (
    <DropdownMenu.Label className="px-4 py-2">
      <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
        {children}
      </span>
    </DropdownMenu.Label>
  )
}

export default function AccountDropdown({
  onOpenLogin,
  onOpenRegister,
}: AccountDropdownProps): React.ReactElement {
  const { isAuthenticated, user, token, logout } = useAuth()
  const { t } = useTranslation()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [renewable, setRenewable] = useState<Checkout[]>([])
  const [renewingAll, setRenewingAll] = useState(false)

  const fetchRenewable = useCallback(async () => {
    if (!token) return
    try {
      const data = await getMyCheckouts(token)
      setRenewable(
        data.filter((c) =>
          c.renewals_remaining === undefined || c.renewals_remaining > 0,
        ),
      )
    } catch {
      // Silent — chip simply won't show
    }
  }, [token])

  useEffect(() => {
    if (isAuthenticated && open) {
      void fetchRenewable()
    }
  }, [isAuthenticated, open, fetchRenewable])

  const handleRenewAll = useCallback(async () => {
    if (renewable.length === 0 || !token) return
    setRenewingAll(true)
    let succeeded = 0
    let failed = 0
    for (const c of renewable) {
      try {
        await renewCheckout(token, c.id)
        succeeded++
      } catch {
        failed++
      }
    }
    if (failed === 0) {
      toast.success(`Renewed all ${succeeded} books.`)
    } else if (succeeded === 0) {
      toast.error(`Couldn't renew any books. They may have holds or hit the renewal limit.`)
    } else {
      toast.error(`Renewed ${succeeded} of ${succeeded + failed}. ${failed} couldn't be renewed.`)
    }
    setRenewingAll(false)
    await fetchRenewable()
  }, [renewable, token, fetchRenewable])

  const isStaffUser = Boolean(
    user &&
      (['staff', 'admin', 'super_admin', 'director', 'legal', 'bookmobile', 'homebond'].includes(
        user.role,
      ) ||
        user.is_board_member),
  )
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'
  const hasActiveChild =
    location.pathname.startsWith('/account') || location.pathname.startsWith('/staff')

  const patronItems: AccountItem[] = [
    { to: '/account', labelKey: 'navigation.myAccount', icon: User, show: true },
    { to: '/account?tab=checkouts', labelKey: 'navigation.myCheckouts', fallback: 'My Checkouts', icon: BookMarked, show: true },
    { to: '/my-prints', labelKey: 'navigation.myPrintJobs', icon: Printer, show: isFeatureEnabled('printing_enabled') },
    { to: '/my-reports', labelKey: 'navigation.myReports', icon: FileText, show: true },
    { to: '/account/notifications', labelKey: 'account.notifications', icon: Bell, show: true },
    {
      to: '/indie/dashboard',
      labelKey: 'navigation.authorDashboard',
      icon: Feather,
      show: Boolean(user?.indie_author && isFeatureEnabled('indie_platform_enabled')),
    },
  ]

  const staffItems: AccountItem[] = isStaffUser
    ? [
        { to: '/staff', labelKey: 'navigation.staff', icon: Briefcase, show: true },
      ]
    : []

  const adminItems: AccountItem[] = isAdmin
    ? [
        { to: '/staff/admin/features', labelKey: 'navigation.featureFlags', icon: Settings, show: true },
        { to: '/staff/admin/site-settings', labelKey: 'navigation.siteSettings', icon: Monitor, show: true },
        { to: '/staff/admin', labelKey: 'navigation.allAdminTools', icon: Briefcase, show: true },
      ]
    : []

  const triggerLabel = isAuthenticated
    ? user?.first_name || t('navigation.account')
    : t('navigation.account')

  return (
    <DropdownMenu.Root open={open} onOpenChange={setOpen}>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          className={clsx(
            'flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium motion-safe:transition-all',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose',
            hasActiveChild
              ? 'bg-lsc-rose/10 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light border-b-2 border-lsc-rose'
              : 'text-earth-600 dark:text-earth-300 hover:bg-earth-50 dark:hover:bg-earth-800/15 hover:text-earth-950 dark:hover:text-lsc-cream',
          )}
        >
          <User aria-hidden="true" className="w-5 h-5" />
          {triggerLabel}
          <ChevronDown
            aria-hidden="true"
            className={clsx(
              'w-3.5 h-3.5 motion-safe:transition-transform motion-safe:duration-200',
              open && 'rotate-180',
            )}
          />
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          collisionPadding={16}
          className={clsx(
            'bg-lsc-white dark:bg-earth-800 ring-1 ring-black/5 dark:ring-white/10 rounded-xl',
            'shadow-soft-xl dark:shadow-[0_8px_30px_rgba(0,0,0,0.6)]',
            'border border-lsc-border dark:border-earth-400/50',
            'overflow-y-auto max-h-[calc(100vh-120px)]',
            'min-w-[240px] max-w-[calc(100vw-2rem)] sm:max-w-[360px] py-2 z-[60]',
            'motion-safe:animate-menu-enter',
          )}
        >
          {isAuthenticated ? (
            <>
              <DropdownMenu.Label className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
                <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {user?.first_name} {user?.last_name}
                </p>
                <p
                  className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate"
                  title={user?.email}
                >
                  {user?.email}
                </p>
              </DropdownMenu.Label>

              <div className="px-3 py-2">
                {renewable.length > 0 ? (
                  <DropdownMenu.Item
                    onSelect={(e) => {
                      e.preventDefault()
                      void handleRenewAll()
                    }}
                    disabled={renewingAll}
                    className={clsx(
                      'w-full flex items-center justify-center gap-2 px-4 py-2 rounded-full cursor-pointer',
                      'bg-lsc-rose/10 hover:bg-lsc-rose/20 dark:bg-lsc-rose/15 dark:hover:bg-lsc-rose/25',
                      'data-[highlighted]:bg-lsc-rose/20 dark:data-[highlighted]:bg-lsc-rose/25',
                      'text-lsc-rose dark:text-lsc-rose-light text-sm font-medium',
                      'border border-lsc-rose/30 dark:border-lsc-rose/40',
                      'outline-none transition-colors data-[disabled]:opacity-50',
                      'focus-visible:ring-2 focus-visible:ring-lsc-rose',
                    )}
                  >
                    {renewingAll ? (
                      <Loader2 aria-hidden="true" className="w-4 h-4 motion-safe:animate-spin" />
                    ) : (
                      <RefreshCw aria-hidden="true" className="w-4 h-4" />
                    )}
                    {renewingAll
                      ? `Renewing ${renewable.length}...`
                      : `Renew all ${renewable.length} book${renewable.length === 1 ? '' : 's'}`}
                  </DropdownMenu.Item>
                ) : (
                  <p className="text-xs text-center text-lsc-dark/60 dark:text-lsc-cream/60 py-1">
                    Nothing to renew today
                  </p>
                )}
              </div>

              <DropdownMenu.Group className="py-1">
                {patronItems
                  .filter((i) => i.show)
                  .map((item) => (
                    <LinkItem key={item.to} item={item} label={item.fallback ? t(item.labelKey, item.fallback) : t(item.labelKey)} />
                  ))}
                {staffItems
                  .filter((i) => i.show)
                  .map((item) => (
                    <LinkItem key={item.to} item={item} label={item.fallback ? t(item.labelKey, item.fallback) : t(item.labelKey)} />
                  ))}
              </DropdownMenu.Group>

              {adminItems.length > 0 && (
                <>
                  <DropdownMenu.Separator className="h-px bg-lsc-border dark:bg-earth-700 my-1" />
                  <DropdownMenu.Group className="py-1">
                    <SectionLabel>{t('navigation.administration')}</SectionLabel>
                    {adminItems
                      .filter((i) => i.show)
                      .map((item) => (
                        <LinkItem key={item.to} item={item} label={item.fallback ? t(item.labelKey, item.fallback) : t(item.labelKey)} />
                      ))}
                  </DropdownMenu.Group>
                </>
              )}

              <DropdownMenu.Separator className="h-px bg-lsc-border dark:bg-earth-700 my-1" />
              <DropdownMenu.Group className="py-1">
                <DropdownMenu.Item
                  onSelect={() => logout()}
                  className={clsx(
                    'w-full flex items-center gap-3 px-4 py-2.5 text-sm',
                    'text-status-danger-600 dark:text-status-danger-400',
                    'data-[highlighted]:bg-status-danger-50 dark:data-[highlighted]:bg-status-danger-900/20',
                    'outline-none transition-colors cursor-pointer',
                  )}
                >
                  <LogOut aria-hidden="true" className="w-4 h-4" />
                  {t('navigation.logout')}
                </DropdownMenu.Item>
              </DropdownMenu.Group>
            </>
          ) : (
            <>
              <DropdownMenu.Label className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
                <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                  {t('auth.signInToAccount')}
                </p>
              </DropdownMenu.Label>

              <div className="p-3 space-y-2">
                <DropdownMenu.Item
                  onSelect={() => onOpenLogin()}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 data-[highlighted]:bg-lsc-rose/90 text-white rounded-xl text-sm font-medium transition-colors outline-none cursor-pointer"
                >
                  <LogIn aria-hidden="true" className="w-4 h-4" />
                  {t('navigation.login')}
                </DropdownMenu.Item>
                <DropdownMenu.Item
                  onSelect={() => onOpenRegister()}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-cream/80 dark:hover:bg-earth-700 data-[highlighted]:bg-lsc-cream/80 dark:data-[highlighted]:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl text-sm font-medium transition-colors border border-lsc-border dark:border-earth-700 outline-none cursor-pointer"
                >
                  <CreditCard aria-hidden="true" className="w-4 h-4" />
                  {t('navigation.register')}
                </DropdownMenu.Item>
              </div>
            </>
          )}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
