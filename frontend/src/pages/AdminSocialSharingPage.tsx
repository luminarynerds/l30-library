/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  Share2,
  Settings,
  RefreshCw,
  Loader2,
  Save,
  Globe,
  Mail,
  Link2,
  BarChart3,
  Copy,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useRequireRole } from '@/hooks/useRequireRole'
import { AdminShell } from '../components/shells/AdminShell'
import { API_BASE } from '@/api/types'
import api from '@/lib/api-client'
import { useTranslation } from '@/i18n'
import {
  AdminTabs,
  StatCard,
  StatGrid,
  ToggleRow,
  TextField,
} from '@/components/admin'

interface SocialSharingConfig {
  sharing_enabled: boolean
  share_buttons_enabled: boolean
  default_message_template?: string
  bluesky_handle?: string
  mastodon_handle?: string
  pinterest_enabled: boolean
  bluesky_enabled: boolean
  mastodon_enabled: boolean
  email_enabled: boolean
  copy_link_enabled: boolean
  share_counts_enabled: boolean
  og_default_image?: string
  utm_tracking_enabled: boolean
  utm_source?: string
  utm_medium?: string
}

interface SharingStats {
  total_shares_today: number
  total_shares_week: number
  total_shares_month: number
  shares_by_platform: Record<string, number>
  most_shared_items: Array<{
    item_id: number
    item_title: string
    share_count: number
  }>
}

type ViewMode = 'config' | 'stats'

export default function AdminSocialSharingPage(): React.ReactElement {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth()
  const { authLoading, isAuthorized } = useRequireRole('systemAdmin')
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [config, setConfig] = useState<SocialSharingConfig | null>(null)
  const [stats, setStats] = useState<SharingStats | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('config')

  useEffect(() => {
    if (!authLoading && !isAuthorized) {
      toast.error(t('toast.adminAPIStatus.adminAccessRequired'))
      navigate('/account')
    }
  }, [authLoading, isAuthorized, navigate, t])

  const fetchConfig = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await api.get<SocialSharingConfig>(`${API_BASE}/sharing/config`)
      setConfig(data)
    } catch (_error: unknown) {
      toast.error(t('admin.adminSocialSharing.failedToLoadSocialSharing'))
    } finally {
      setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchStats = useCallback(async () => {
    try {
      const data = await api.get<SharingStats>(`${API_BASE}/sharing/stats`)
      setStats(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      fetchConfig()
      fetchStats()
    }
  }, [isAuthenticated, fetchConfig, fetchStats])

  const handleSaveConfig = async () => {
    if (!config) return
    setIsSaving(true)
    try {
      await api.put(`${API_BASE}/sharing/config`, config)
      toast.success(t('toast.adminSMSSettings.configurationSaved'))
    } catch (_error: unknown) {
      toast.error(t('admin.adminSocialSharing.failedToSaveConfiguration'))
    } finally {
      setIsSaving(false)
    }
  }

  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'bluesky':
      case 'mastodon':
        return <Globe className="w-4 h-4" aria-hidden="true" />
      case 'email':
        return <Mail className="w-4 h-4" aria-hidden="true" />
      case 'copy_link':
        return <Copy className="w-4 h-4" aria-hidden="true" />
      default:
        return <Share2 className="w-4 h-4" aria-hidden="true" />
    }
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
      </div>
    )
  }

  if (!isAuthorized) {
    return <></>
  }

  const tabs = [
    { id: 'config' as const, label: 'Config', icon: Settings },
    { id: 'stats' as const, label: 'Stats', icon: BarChart3 },
  ]

  const platformToggles: Array<{ key: keyof SocialSharingConfig; label: string; icon?: React.ElementType }> = [
    { key: 'bluesky_enabled', label: 'Bluesky', icon: Globe },
    { key: 'mastodon_enabled', label: 'Mastodon', icon: Globe },
    { key: 'pinterest_enabled', label: 'Pinterest' },
    { key: 'email_enabled', label: 'Email', icon: Mail },
    { key: 'copy_link_enabled', label: 'Copy Link', icon: Link2 },
  ]

  return (
    <AdminShell title="Social Sharing Settings">
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Social Sharing Settings
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Configure social media sharing options and tracking
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              fetchConfig()
              fetchStats()
            }}
            className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
          >
            <RefreshCw className="w-4 h-4" aria-hidden="true" />
            Refresh
          </button>
        </div>

        <AdminTabs tabs={tabs} active={viewMode} onChange={setViewMode} ariaLabel="Social sharing views" />

        {viewMode === 'config' && (
          <>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
              </div>
            ) : config ? (
              <div className="space-y-6">
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 space-y-4">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">General Settings</h3>
                  <ToggleRow
                    label="Social Sharing Enabled"
                    description="Enable or disable all social sharing features"
                    checked={config.sharing_enabled}
                    onChange={(v) => setConfig({ ...config, sharing_enabled: v })}
                  />
                  <ToggleRow
                    label="Show Share Buttons"
                    description="Display share buttons on catalog items and events"
                    checked={config.share_buttons_enabled}
                    onChange={(v) => setConfig({ ...config, share_buttons_enabled: v })}
                  />
                  <ToggleRow
                    label="Show Share Counts"
                    description="Display the number of times content has been shared"
                    checked={config.share_counts_enabled}
                    onChange={(v) => setConfig({ ...config, share_counts_enabled: v })}
                  />
                </div>

                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 space-y-4">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Platform Settings</h3>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                      Bluesky Handle
                    </label>
                    <div className="flex">
                      <span className="px-3 py-2 bg-lsc-cream dark:bg-earth-700 border border-r-0 border-lsc-border dark:border-earth-700 rounded-l-lg text-lsc-dark/70 dark:text-lsc-cream/70">
                        @
                      </span>
                      <input
                        type="text"
                        value={config.bluesky_handle || ''}
                        onChange={(e) => setConfig({ ...config, bluesky_handle: e.target.value })}
                        placeholder={t('placeholder.adminSocialSharing.yourlibrarybskysocial')}
                        className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-r-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                      Mastodon Handle
                    </label>
                    <div className="flex">
                      <span className="px-3 py-2 bg-lsc-cream dark:bg-earth-700 border border-r-0 border-lsc-border dark:border-earth-700 rounded-l-lg text-lsc-dark/70 dark:text-lsc-cream/70">
                        @
                      </span>
                      <input
                        type="text"
                        value={config.mastodon_handle || ''}
                        onChange={(e) => setConfig({ ...config, mastodon_handle: e.target.value })}
                        placeholder={t('placeholder.adminSocialSharing.yourlibrarymastodonsocial')}
                        className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-r-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {platformToggles.map(({ key, label, icon: Icon }) => (
                      <label key={key as string} className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                        <input
                          type="checkbox"
                          checked={config[key] as boolean}
                          onChange={(e) => setConfig({ ...config, [key]: e.target.checked })}
                          className="w-4 h-4 text-lsc-rose bg-earth-100 dark:bg-earth-700 border-lsc-border dark:border-earth-700 rounded focus:ring-lsc-rose"
                        />
                        {Icon && <Icon className="w-4 h-4" aria-hidden="true" />}
                        {label}
                      </label>
                    ))}
                  </div>
                </div>

                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 space-y-4">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">UTM Tracking</h3>
                  <ToggleRow
                    label="Enable UTM Tracking"
                    description="Add UTM parameters to shared links"
                    checked={config.utm_tracking_enabled}
                    onChange={(v) => setConfig({ ...config, utm_tracking_enabled: v })}
                  />
                  {config.utm_tracking_enabled && (
                    <div className="grid grid-cols-2 gap-4">
                      <TextField
                        label="UTM Source"
                        value={config.utm_source || ''}
                        onChange={(v) => setConfig({ ...config, utm_source: v })}
                        placeholder={t('placeholder.adminSocialSharing.librarycatalog')}
                      />
                      <TextField
                        label="UTM Medium"
                        value={config.utm_medium || ''}
                        onChange={(v) => setConfig({ ...config, utm_medium: v })}
                        placeholder={t('placeholder.adminSocialSharing.social')}
                      />
                    </div>
                  )}
                  <div className="pt-4 border-t border-lsc-border dark:border-earth-700 flex justify-end">
                    <button
                      type="button"
                      onClick={handleSaveConfig}
                      disabled={isSaving}
                      className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
                    >
                      {isSaving ? (
                        <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                      ) : (
                        <Save className="w-4 h-4" aria-hidden="true" />
                      )}
                      Save Configuration
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6 text-center">
                <p className="text-status-danger-700 dark:text-status-danger-300 mb-4">Failed to load configuration</p>
                <button
                  type="button"
                  onClick={fetchConfig}
                  className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
                >
                  Retry
                </button>
              </div>
            )}
          </>
        )}

        {viewMode === 'stats' &&
          (stats ? (
            <div className="space-y-6">
              <StatGrid columns={3}>
                <StatCard title="Today" value={stats.total_shares_today} icon={Share2} color="accent" />
                <StatCard title="This Week" value={stats.total_shares_week} icon={Share2} color="accent" />
                <StatCard title="This Month" value={stats.total_shares_month} icon={Share2} color="accent" />
              </StatGrid>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Shares by Platform
                </h3>
                <div className="space-y-3">
                  {Object.entries(stats.shares_by_platform).map(([platform, count]) => (
                    <div key={platform} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getPlatformIcon(platform)}
                        <span className="text-lsc-dark dark:text-lsc-cream capitalize">
                          {platform.replace('_', ' ')}
                        </span>
                      </div>
                      <span className="font-medium text-lsc-dark dark:text-lsc-cream">{count}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Most Shared Items
                </h3>
                {stats.most_shared_items.length === 0 ? (
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('admin.adminSocialSharing.noSharedItemsYet')}
                  </p>
                ) : (
                  <div className="space-y-3">
                    {stats.most_shared_items.map((item, index) => (
                      <div key={item.item_id} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 flex items-center justify-center rounded-full bg-lsc-cream dark:bg-earth-700 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                            {index + 1}
                          </span>
                          <span className="text-lsc-dark dark:text-lsc-cream">{item.item_title}</span>
                        </div>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {item.share_count} shares
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
            </div>
          ))}
      </div>
    </AdminShell>
  )
}
