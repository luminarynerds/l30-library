/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Security Tab
 * 7-section security hub: Checklist, 2FA, Password, Recovery, Alerts, Activity, Sessions
 */
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import {
  Loader2,
  Key,
  Eye,
  EyeOff,
  Smartphone,
  RefreshCw,
  Monitor,
  LogOut,
  ChevronDown,
  ChevronUp,
  Shield,
  LifeBuoy,
  Bell,
  History,
} from 'lucide-react'
import { Session } from '../../api/api'
import ConfirmDialog from '../ConfirmDialog'
import { useTranslation} from '@/i18n'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import { getSecurityOverview, type SecurityOverview } from '@/api/account-security-api'
import { SecurityChecklist } from './SecurityChecklist'
import { FinancialSecurityBanner } from './FinancialSecurityBanner'
import { TwoFactorSetup } from './TwoFactorSetup'
import { RecoveryOptions } from './RecoveryOptions'
import { SecurityAlerts } from './SecurityAlerts'
import { SecurityActivity } from './SecurityActivity'
import { SecuritySkeleton } from './SkeletonLoaders'

interface SecuritySectionProps {
  sessions: Session[]
  sessionsLoading: boolean
  revokingSessionId: number | null
  onSessionRefresh: () => void
  onRevokeSession: (sessionId: number) => void
  onRevokeAllOtherSessions?: () => void
  isRevokingAllSessions?: boolean
  onChangePassword: (currentPassword: string, newPassword: string, confirmPassword: string) => Promise<boolean>
  isChangingPassword: boolean
}

// Password strength calculation
function calculatePasswordStrength(password: string, t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => string): { score: number; label: string; color: string } {
  let score = 0

  // Length checks
  if (password.length >= 8) score += 1
  if (password.length >= 12) score += 1
  if (password.length >= 16) score += 1

  // Character variety
  if (/[a-z]/.test(password)) score += 1
  if (/[A-Z]/.test(password)) score += 1
  if (/[0-9]/.test(password)) score += 1
  if (/[^a-zA-Z0-9]/.test(password)) score += 1

  // Normalize to 0-4 scale
  const normalizedScore = Math.min(4, Math.floor(score / 2))

  const levels = [
    { label: t('auth.strengthVeryWeak', 'Very Weak'), color: 'bg-status-danger-500' },
    { label: t('auth.strengthWeak', 'Weak'), color: 'bg-status-warning-500' },
    { label: t('auth.strengthFair', 'Fair'), color: 'bg-status-warning-500' },
    { label: t('auth.strengthGood', 'Good'), color: 'bg-lime-500' },
    { label: t('auth.strengthStrong', 'Strong'), color: 'bg-status-success-500' },
  ]

  const level = levels[normalizedScore] || levels[0]!
  return { score: normalizedScore, label: level!.label, color: level!.color }
}

// Collapsible section wrapper with status indicators
type SectionStatus = 'active' | 'attention' | 'info'

interface CollapsibleSectionProps {
  id: string
  title: string
  icon?: React.ReactNode
  status: SectionStatus
  collapsed: boolean
  onToggle: () => void
  children: React.ReactNode
}

const statusBorder = {
  active: 'border-l-4 border-l-green-500',
  attention: 'border-l-4 border-l-status-warning-500',
  info: '',
}

function getStatusBadge(t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => string) {
  return {
    active: <span className="text-xs px-2 py-0.5 rounded-full bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-300">{t('components.account.securitySection.badgeActive', 'Active')}</span>,
    attention: <span className="text-xs px-2 py-0.5 rounded-full bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-300">{t('components.account.securitySection.badgeNotSetUp', 'Not set up')}</span>,
    info: null,
  }
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  id, title, icon, status, collapsed, onToggle, children,
}) => {
  const { t } = useTranslation()
  const statusBadge = getStatusBadge(t)
  return (
  <div className={`bg-cream dark:bg-earth-800 rounded-xl overflow-hidden ${statusBorder[status]}`}>
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={!collapsed}
      aria-controls={`section-${id}`}
      className="w-full flex items-center justify-between p-6 text-left"
    >
      <div className="flex items-center gap-3">
        {icon}
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h3>
        {statusBadge[status]}
      </div>
      {collapsed ? <ChevronDown className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" /> : <ChevronUp className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" />}
    </button>
    <div
      id={`section-${id}`}
      className={`grid motion-safe:transition-[grid-template-rows] motion-safe:duration-300 ${collapsed ? 'grid-rows-[0fr]' : 'grid-rows-[1fr]'}`}
    >
      <div className="overflow-hidden">
        <div className="px-6 pb-6">
          {children}
        </div>
      </div>
    </div>
  </div>
  )
}

export const SecuritySection: React.FC<SecuritySectionProps> = ({
  sessions,
  sessionsLoading,
  revokingSessionId,
  onSessionRefresh,
  onRevokeSession,
  onRevokeAllOtherSessions,
  isRevokingAllSessions,
  onChangePassword,
  isChangingPassword,
// eslint-disable-next-line complexity
}) => {
  const { settings: a11y } = useAccessibility()
  const { t } = useTranslation()
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  })
  const [confirmRevokeSessionId, setConfirmRevokeSessionId] = useState<number | null>(null)
  const [confirmRevokeAll, setConfirmRevokeAll] = useState(false)
  const sessionToRevoke = sessions.find((s) => s.id === confirmRevokeSessionId)

  // Security overview state
  const [overview, setOverview] = useState<SecurityOverview | null>(null)
  const [overviewError, setOverviewError] = useState(false)
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({})

  // Collapsible section state
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({})
  const [initializedCollapse, setInitializedCollapse] = useState(false)

  const sectionStatuses = useMemo((): Record<string, SectionStatus> => {
    if (!overview) return {}
    return {
      '2fa': overview.totp_enabled ? 'active' : 'attention',
      password: 'active',
      recovery: overview.recovery_email_set && overview.recovery_email_verified ? 'active' : 'attention',
      alerts: overview.security_alert_new_login && overview.security_alert_changes ? 'active' : 'attention',
      activity: 'info',
      sessions: 'info',
    }
  }, [overview])

  // Initialize collapse state when overview loads — expand sections needing attention
  useEffect(() => {
    if (overview && !initializedCollapse) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- seed collapse state once from async-loaded overview, then user-mutable
      setCollapsedSections({
        '2fa': overview.totp_enabled,
        password: true,
        recovery: overview.recovery_email_set && overview.recovery_email_verified,
        alerts: overview.security_alert_new_login && overview.security_alert_changes,
        activity: true,
        sessions: true,
      })
      setInitializedCollapse(true)
    }
  }, [overview, initializedCollapse])

  const toggleSection = (section: string) => {
    setCollapsedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const fetchOverview = useCallback(async () => {
    try {
      setOverviewError(false)
      const data = await getSecurityOverview()
      setOverview(data)
    } catch {
      setOverviewError(true)
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async fetch on mount; fetchOverview resets error state before awaiting
    fetchOverview()
  }, [fetchOverview])

  const handleScrollTo = (section: string) => {
    setCollapsedSections(prev => ({ ...prev, [section]: false }))
    setTimeout(() => {
      sectionRefs.current[section]?.scrollIntoView({ behavior: a11y.reduceMotion ? 'auto' : 'smooth', block: 'start' })
    }, 50)
  }

  const strength = useMemo(() => calculatePasswordStrength(passwordData.newPassword, t), [passwordData.newPassword, t])

  const requirements = useMemo(() => [
    { met: passwordData.newPassword.length >= 8, label: t('components.account.securitySection.reqAtLeast8', 'At least 8 characters') },
    { met: /[a-z]/.test(passwordData.newPassword), label: t('components.account.securitySection.reqLowercase', 'One lowercase letter') },
    { met: /[A-Z]/.test(passwordData.newPassword), label: t('components.account.securitySection.reqUppercase', 'One uppercase letter') },
    { met: /[0-9]/.test(passwordData.newPassword), label: t('components.account.securitySection.reqNumber', 'One number') },
    { met: /[^a-zA-Z0-9]/.test(passwordData.newPassword), label: t('components.account.securitySection.reqSpecialChar', 'One special character') },
  ], [passwordData.newPassword, t])

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const success = await onChangePassword(
      passwordData.currentPassword,
      passwordData.newPassword,
      passwordData.confirmPassword
    )
    if (success) {
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' })
      setShowCurrentPassword(false)
      setShowNewPassword(false)
      setShowConfirmPassword(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
        {t('account.securitySettings', 'Security Settings')}
      </h2>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        {t('account.securitySettingsDesc', 'Manage your password and account security.')}
      </p>

      <div className="space-y-6">
        {/* Loading skeleton */}
        {!overview && !overviewError && <SecuritySkeleton />}

        {/* Error state */}
        {overviewError && !overview && (
          <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-xl text-sm text-status-danger-700 dark:text-status-danger-300 flex items-center justify-between">
            <span>{t('components.account.securitySection.unableToLoadStatus', 'Unable to load security status.')}</span>
            <button onClick={() => { setOverviewError(false); fetchOverview() }} className="underline">{t('common.retry', 'Retry')}</button>
          </div>
        )}

        {/* 1. Security Checklist */}
        {overview && (
          <SecurityChecklist overview={overview} onScrollTo={handleScrollTo} />
        )}

        {/* 1b. Financial Security Banner (Stripe Connect 2FA nudge) */}
        {overview && (
          <FinancialSecurityBanner
            hasStripeConnected={overview.has_stripe_connected}
            totpEnabled={overview.totp_enabled}
            onScrollTo2FA={() => handleScrollTo('2fa')}
          />
        )}

        {/* 2. Two-Factor Authentication */}
        <div ref={el => { sectionRefs.current['2fa'] = el }}>
          <CollapsibleSection
            id="2fa"
            title={t('accountSecurity.twoFactor.title', 'Two-Factor Authentication')}
            icon={<Shield className="w-5 h-5" aria-hidden="true" />}
            status={sectionStatuses['2fa'] || 'attention'}
            collapsed={collapsedSections['2fa'] ?? false}
            onToggle={() => toggleSection('2fa')}
          >
            <TwoFactorSetup
              enabled={overview?.totp_enabled ?? false}
              confirmedAt={overview?.totp_confirmed_at ?? null}
              recoveryCodesRemaining={overview?.recovery_codes_remaining ?? 0}
              onStatusChange={fetchOverview}
            />
          </CollapsibleSection>
        </div>

        {/* 3. Change Password */}
        <div ref={el => { sectionRefs.current['password'] = el }}>
        <CollapsibleSection
          id="password"
          title={t('account.changePassword', 'Change Password')}
          icon={<Key className="w-5 h-5" aria-hidden="true" />}
          status={sectionStatuses['password'] || 'active'}
          collapsed={collapsedSections['password'] ?? true}
          onToggle={() => toggleSection('password')}
        >
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div>
              <label htmlFor="security-current-password" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                {t('account.currentPassword', 'Current Password')}
              </label>
              <div className="relative">
                <input
                  id="security-current-password"
                  type={showCurrentPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={passwordData.currentPassword}
                  onChange={(e) =>
                    setPasswordData({ ...passwordData, currentPassword: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-sage/30 dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400 focus:border-transparent"
                  required
                />
                <button
                  type="button"
                  aria-label={showCurrentPassword ? t('auth.hideCurrentPassword', 'Hide current password') : t('auth.showCurrentPassword', 'Show current password')}
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                >
                  {showCurrentPassword ? <EyeOff className="w-5 h-5" aria-hidden="true" /> : <Eye className="w-5 h-5" aria-hidden="true" />}
                </button>
              </div>
            </div>

            <div>
              <label htmlFor="security-new-password" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                {t('account.newPassword', 'New Password')}
              </label>
              <div className="relative">
                <input
                  id="security-new-password"
                  type={showNewPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={passwordData.newPassword}
                  onChange={(e) =>
                    setPasswordData({ ...passwordData, newPassword: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-sage/30 dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400 focus:border-transparent"
                  required
                />
                <button
                  type="button"
                  aria-label={showNewPassword ? t('auth.hideNewPassword', 'Hide new password') : t('auth.showNewPassword', 'Show new password')}
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                >
                  {showNewPassword ? <EyeOff className="w-5 h-5" aria-hidden="true" /> : <Eye className="w-5 h-5" aria-hidden="true" />}
                </button>
              </div>
              {passwordData.newPassword && (
                <div className="mt-2">
                  <div role="status" aria-live="polite">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="flex-1 h-2 bg-earth-200 dark:bg-earth-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-300 ${strength.color}`}
                          style={{ width: `${(strength.score + 1) * 20}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 min-w-[70px]">
                        {strength.label}
                      </span>
                    </div>
                  </div>
                  <ul className="text-xs space-y-0.5 mt-1" aria-label={t('aria.account.passwordRequirements')}>
                    {requirements.map(r => (
                      <li key={r.label} className={r.met ? 'text-status-success-600 dark:text-status-success-400' : 'text-earth-600'}>
                        {r.met ? '✓' : '○'} {r.label}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {!passwordData.newPassword && (
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  {t('account.passwordRequirements', 'Password must be at least 8 characters long')}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="security-confirm-password" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                {t('account.confirmNewPassword', 'Confirm New Password')}
              </label>
              <div className="relative">
                <input
                  id="security-confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={passwordData.confirmPassword}
                  onChange={(e) =>
                    setPasswordData({ ...passwordData, confirmPassword: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-sage/30 dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400 focus:border-transparent"
                  required
                />
                <button
                  type="button"
                  aria-label={showConfirmPassword ? t('auth.hideConfirmPassword', 'Hide confirm password') : t('auth.showConfirmPassword', 'Show confirm password')}
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                >
                  {showConfirmPassword ? <EyeOff className="w-5 h-5" aria-hidden="true" /> : <Eye className="w-5 h-5" aria-hidden="true" />}
                </button>
              </div>
              {passwordData.confirmPassword && passwordData.newPassword !== passwordData.confirmPassword && (
                <p className="text-xs text-status-danger-600 dark:text-status-danger-400 mt-1" role="alert">{t('components.account.securitySection.passwordsDoNotMatch', 'Passwords do not match')}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isChangingPassword}
              className="w-full bg-lsc-rose text-white py-2 rounded-xl hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isChangingPassword ? (
                <>
                  <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                  {t('account.changingPassword', 'Changing Password...')}
                </>
              ) : (
                <>
                  <Key className="w-5 h-5" />
                  {t('account.changePassword', 'Change Password')}
                </>
              )}
            </button>
          </form>
        </CollapsibleSection>
        </div>

        {/* 4. Recovery Options */}
        <div ref={el => { sectionRefs.current['recovery'] = el }}>
          <CollapsibleSection
            id="recovery"
            title={t('accountSecurity.recovery.title', 'Recovery Options')}
            icon={<LifeBuoy className="w-5 h-5" aria-hidden="true" />}
            status={sectionStatuses['recovery'] || 'attention'}
            collapsed={collapsedSections['recovery'] ?? false}
            onToggle={() => toggleSection('recovery')}
          >
            <RecoveryOptions
              totpEnabled={overview?.totp_enabled ?? false}
              recoveryEmailSet={overview?.recovery_email_set ?? false}
              recoveryEmailVerified={overview?.recovery_email_verified ?? false}
              recoveryCodesRemaining={overview?.recovery_codes_remaining ?? 0}
              onStatusChange={fetchOverview}
            />
          </CollapsibleSection>
        </div>

        {/* 5. Security Alerts */}
        <div ref={el => { sectionRefs.current['alerts'] = el }}>
          <CollapsibleSection
            id="alerts"
            title={t('accountSecurity.alerts.title', 'Security Alerts')}
            icon={<Bell className="w-5 h-5" aria-hidden="true" />}
            status={sectionStatuses['alerts'] || 'attention'}
            collapsed={collapsedSections['alerts'] ?? false}
            onToggle={() => toggleSection('alerts')}
          >
            <SecurityAlerts
              alertNewLogin={overview?.security_alert_new_login ?? true}
              alertChanges={overview?.security_alert_changes ?? true}
              onStatusChange={fetchOverview}
            />
          </CollapsibleSection>
        </div>

        {/* 6. Recent Activity */}
        <CollapsibleSection
          id="activity"
          title={t('accountSecurity.activity.title', 'Recent Activity')}
          icon={<History className="w-5 h-5" aria-hidden="true" />}
          status="info"
          collapsed={collapsedSections['activity'] ?? true}
          onToggle={() => toggleSection('activity')}
        >
          <SecurityActivity />
        </CollapsibleSection>

        {/* 7. Active Sessions */}
        <div ref={el => { sectionRefs.current['sessions'] = el }}>
        <CollapsibleSection
          id="sessions"
          title={t('account.activeSessions', 'Active Sessions')}
          icon={<Smartphone className="w-5 h-5" aria-hidden="true" />}
          status="info"
          collapsed={collapsedSections['sessions'] ?? true}
          onToggle={() => toggleSection('sessions')}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <button
                onClick={onSessionRefresh}
                disabled={sessionsLoading}
                className="flex items-center gap-2 px-3 py-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${sessionsLoading ? 'motion-safe:animate-spin' : ''}`} />
                {t('account.refresh', 'Refresh')}
              </button>
            </div>
          </div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            {t('components.account.securitySection.sessionsDesc', "These are the devices currently logged into your account. If you see a session you don't recognize, revoke it immediately and change your password.")}
          </p>

          {/* Revoke All Other Sessions Button */}
          {sessions.filter(s => !s.is_current).length > 0 && onRevokeAllOtherSessions && (
            <div className="mb-4 p-3 bg-lsc-white dark:bg-lsc-brown rounded-xl border border-sage/20 dark:border-earth-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <LogOut className="w-5 h-5 text-status-danger-600" />
                  <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                    {t('components.account.securitySection.otherActiveSessionsCount', { count: sessions.filter(s => !s.is_current).length })}
                  </span>
                </div>
                <button
                  onClick={() => setConfirmRevokeAll(true)}
                  disabled={isRevokingAllSessions}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 transition-colors disabled:opacity-50"
                >
                  {isRevokingAllSessions ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <LogOut className="w-4 h-4" />
                  )}
                  {t('components.account.securitySection.signOutEverywhereButton', 'Sign Out Everywhere Else')}
                </button>
              </div>
            </div>
          )}

          {sessionsLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-8">
              <Monitor className="w-12 h-12 text-sage/30 mx-auto mb-3" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('account.noActiveSessions', 'No active sessions')}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`p-4 rounded-xl border-2 ${
                    session.is_current
                      ? 'border-lsc-rose/30 bg-lsc-rose/5'
                      : 'border-sage/20 dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Monitor className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {session.device_info || t('account.unknownDevice', 'Unknown Device')}
                        </p>
                        {session.is_current && (
                          <span className="px-2 py-0.5 text-xs bg-lsc-rose text-white rounded-full">
                            {t('account.current', 'Current')}
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
                        {session.ip_address && <p>{t('components.account.securitySection.ipLabel', { ip: session.ip_address })}</p>}
                        <p>{t('components.account.securitySection.signedInLabel', { date: new Date(session.created_at).toLocaleString() })}</p>
                        {session.last_active_at && (
                          <p>{t('components.account.securitySection.lastActiveLabel', { date: new Date(session.last_active_at).toLocaleString() })}</p>
                        )}
                      </div>
                    </div>
                    {!session.is_current && (
                      <button
                        onClick={() => setConfirmRevokeSessionId(session.id)}
                        disabled={revokingSessionId === session.id}
                        aria-label={revokingSessionId === session.id ? t('aria.account.revokingSession', 'Revoking session...') : t('aria.account.revokeSession', 'Revoke session')}
                        className="ml-4 px-4 py-2 bg-status-danger-600 text-white rounded-xl hover:bg-status-danger-700 transition-colors disabled:opacity-50 text-sm"
                      >
                        {revokingSessionId === session.id ? (
                          <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                        ) : (
                          t('account.revoke', 'Revoke')
                        )}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CollapsibleSection>
        </div>
      </div>

      <ConfirmDialog
        isOpen={confirmRevokeSessionId !== null}
        title={t('account.revokeSessionTitle', 'Revoke this session?')}
        message={
          sessionToRevoke
            ? (sessionToRevoke.ip_address
                ? t('components.account.securitySection.revokeMessageWithDeviceAndIp', { device: sessionToRevoke.device_info || t('account.unknownDevice', 'Unknown Device'), ip: sessionToRevoke.ip_address })
                : t('components.account.securitySection.revokeMessageWithDevice', { device: sessionToRevoke.device_info || t('account.unknownDevice', 'Unknown Device') }))
            : t('components.account.securitySection.revokeMessageGeneric', 'Sign out this session? That device will need to sign in again.')
        }
        confirmText={t('account.yesRevoke', 'Yes, revoke')}
        cancelText={t('common.goBack', 'Go back')}
        confirmVariant="danger"
        onConfirm={() => {
          if (confirmRevokeSessionId !== null) {
            onRevokeSession(confirmRevokeSessionId)
          }
          setConfirmRevokeSessionId(null)
        }}
        onCancel={() => setConfirmRevokeSessionId(null)}
      />

      <ConfirmDialog
        isOpen={confirmRevokeAll}
        title={t('components.account.securitySection.signOutAllOtherSessions', 'Sign out all other sessions?')}
        message={t('components.account.securitySection.signOutAllOtherMessage', { count: sessions.filter(s => !s.is_current).length })}
        confirmText={t('account.yesSignOutAll', 'Yes, sign out all')}
        cancelText={t('common.goBack', 'Go back')}
        confirmVariant="danger"
        onConfirm={() => {
          if (onRevokeAllOtherSessions) {
            onRevokeAllOtherSessions()
          }
          setConfirmRevokeAll(false)
        }}
        onCancel={() => setConfirmRevokeAll(false)}
      />
    </div>
  )
}
