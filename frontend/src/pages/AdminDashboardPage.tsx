/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext';
import api from '@/lib/api-client';
import { AdminShell } from '../components/shells/AdminShell';
import {
  ToggleRight,
  Palette,
  Mail,
  Wallet,
  Target,
  Settings,
  Activity,
  Users,
  AlertCircle,
  CheckCircle,
  Clock,
  RefreshCw,
  Lightbulb,
  AlertTriangle,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { StatCard } from '@/components/ui/StatCard';
import { StatGrid } from '@/components/ui/StatGrid';
import AdminGettingStartedChecklist from '@/components/onboarding/AdminGettingStartedChecklist';
import { useTranslation, getCurrentLocale } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

interface ConfigCard {
  id: string;
  title: string;
  icon: React.ReactNode;
  stats: string;
  color: string;
  description: string;
  link?: string;
}

interface AuditLogEntry {
  id: number;
  admin_id?: number;
  admin_email?: string;
  action: string;
  target_user_email?: string;
  old_value?: string;
  new_value?: string;
  reason?: string;
  created_at: string;
  target_user_id?: number;
}

interface SystemHealthStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'error';
  lastChecked: string;
  message?: string;
}

export default function AdminDashboardPage() {
  const { t } = useTranslation()
  const { user } = useAuth();
  const { features, loading: featuresLoading } = useOrganizationFeatures();
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [recentLogs, setRecentLogs] = useState<AuditLogEntry[]>([]);
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealthStatus[]>([]);

  // Fetch recent audit logs
  const fetchRecentLogs = useCallback(async () => {
    try {
      const response = await api.get<{ logs: AuditLogEntry[] }>(
        '/api/v1/audit/admin?page=1&page_size=10&days_back=1'
      );
      if (response && response.logs) {
        setRecentLogs(response.logs);
      }
    } catch (error: unknown) {
      if (import.meta.env.DEV) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      }
      // Show empty state if API fails
      setRecentLogs([]);
    }
  }, []);

  // Check system health using real health endpoints
                                                  // eslint-disable-next-line complexity
  const checkSystemHealth = useCallback(async () => {
    const now = new Date().toISOString();
    const healthChecks: SystemHealthStatus[] = [];

    try {
      const readiness = await api.get('/api/v1/health/ready');
      const checks = readiness.checks || {};

      healthChecks.push({
        name: 'PostgreSQL',
        status: checks.database?.status === 'healthy' ? 'healthy' : 'error',
        lastChecked: now,
        message: checks.database?.status === 'healthy'
          ? `Connected (${checks.database?.response_time_ms ?? '?'} ms)`
          : (checks.database?.error || 'Unavailable'),
      });

      healthChecks.push({
        name: 'Redis',
        status: checks.redis?.status === 'healthy' ? 'healthy' : 'degraded',
        lastChecked: now,
        message: checks.redis?.status === 'healthy'
          ? `Connected (${checks.redis?.response_time_ms ?? '?'} ms)`
          : (checks.redis?.error || 'Unavailable'),
      });

      healthChecks.push({
        name: 'APScheduler',
        status: checks.scheduler?.status === 'healthy' ? 'healthy'
          : checks.scheduler?.status === 'disabled' ? 'degraded' : 'error',
        lastChecked: now,
        message: checks.scheduler?.status === 'healthy'
          ? `Running (${checks.scheduler?.job_count ?? 0} jobs)`
          : (checks.scheduler?.message || checks.scheduler?.error || 'Not running'),
      });

      healthChecks.push({
        name: 'WebSockets',
        status: checks.websockets?.status === 'healthy' ? 'healthy' : 'degraded',
        lastChecked: now,
        message: checks.websockets?.status === 'healthy'
          ? `Patron: ${checks.websockets?.patron?.active_connections ?? 0} conn, RFID: ${checks.websockets?.rfid?.active_connections ?? 0} conn`
          : 'Degraded',
      });

      healthChecks.push({
        name: 'Feature Flag Sync',
        status: features ? 'healthy' : 'degraded',
        lastChecked: now,
        message: features ? 'Synchronized' : 'Unable to load features',
      });
    } catch {
      // Health endpoint itself failed
      healthChecks.push(
        { name: 'API Responsiveness', status: 'error', lastChecked: now, message: 'Health check failed' },
        { name: 'PostgreSQL', status: 'error', lastChecked: now, message: 'Unable to verify' },
        { name: 'Redis', status: 'error', lastChecked: now, message: 'Unable to verify' },
        { name: 'APScheduler', status: 'error', lastChecked: now, message: 'Unable to verify' },
        { name: 'WebSockets', status: 'error', lastChecked: now, message: 'Unable to verify' },
        { name: 'Feature Flag Sync', status: features ? 'healthy' : 'degraded', lastChecked: now, message: features ? 'Synchronized' : 'Unable to load features' },
      );
    }

    setSystemHealth(healthChecks);
  }, [features]);

  useEffect(() => {
    const loadDashboard = async () => {
      setLoading(true);
      await Promise.all([fetchRecentLogs(), checkSystemHealth()]);
      setLoading(false);
    };

    loadDashboard();

    if (autoRefresh) {
      const interval = setInterval(loadDashboard, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, fetchRecentLogs, checkSystemHealth]);

  if (loading || featuresLoading) {
    return (
      <AdminShell title="Admin Dashboard">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      </AdminShell>
    );
  }

  // Calculate stats
  const featureFlagKeys = features
    ? Object.keys(features).filter((key) => key.endsWith('_enabled'))
    : [];
  const featureFlagsTotal = featureFlagKeys.length;
  const featureFlagsEnabled = featureFlagKeys.filter(
    (key) => (features as unknown as Record<string, unknown>)[key] === true
  ).length;

  const personalizedCount =
    (features?.enabled_themes?.length || 0) +
    (features?.enabled_fonts?.length || 0) +
    (features?.enabled_focus_modes?.length || 0);

  const quickStats = [
    {
      label: 'Total Configurations',
      value: Object.keys(features || {}).length,
      icon: Settings,
      color: 'blue' as const,
    },
    {
      label: 'Recently Modified (24h)',
      value: recentLogs.filter((log) => isWithinLast24Hours(log.created_at)).length,
      icon: Clock,
      color: 'green' as const,
    },
    {
      label: 'Admin Users',
      value: recentLogs.length > 0 ? new Set(recentLogs.map(l => l.admin_id)).size : 0,
      icon: Users,
      color: 'purple' as const,
    },
    {
      label: 'System Status',
      value: systemHealth.length > 0 && systemHealth.every(h => h.status === 'healthy') ? 'Healthy' : systemHealth.some(h => h.status === 'error') ? 'Error' : 'Unknown',
      icon: Activity,
      color: 'green' as const,
    },
  ];

  const configCards: ConfigCard[] = [
    {
      id: 'features',
      title: 'Feature Flags',
      icon: <ToggleRight className="w-6 h-6" />,
      stats: `${featureFlagsEnabled} of ${featureFlagsTotal} enabled`,
      color: 'from-earth-600 to-earth-700',
      description: t('admin.adminDashboard.enableDisableSystemFeatures'),
      link: '/staff/admin/features',
    },
    {
      id: 'personalization',
      title: 'Personalization',
      icon: <Palette className="w-6 h-6" />,
      stats: `${personalizedCount} items configured`,
      color: 'from-earth-600 to-earth-700',
      description: t('admin.adminDashboard.themesFontsAndFocusModes'),
      link: '/staff/admin/personalization',
    },
    {
      id: 'financial',
      title: 'Financial Config',
      icon: <Wallet className="w-6 h-6" />,
      stats: 'Active',
      color: 'from-earth-600 to-earth-700',
      description: t('admin.adminDashboard.finePoliciesAndPaymentSettings'),
      link: '/staff/admin/financial-config',
    },
    {
      id: 'email',
      title: 'Email & Notifications',
      icon: <Mail className="w-6 h-6" />,
      stats: features?.email_notifications_enabled ? 'Enabled' : 'Disabled',
      color: 'from-earth-600 to-earth-700',
      description: t('admin.adminDashboard.emailAndNotificationSettings'),
      link: '/staff/admin/email-notifications',
    },
    {
      id: 'limits',
      title: 'System Limits',
      icon: <Target className="w-6 h-6" />,
      stats: `${features?.max_holds_per_patron || 0} holds, ${features?.max_checkouts_per_patron || 0} checkouts`,
      color: 'from-earth-600 to-earth-700',
      description: t('admin.adminDashboard.coppaAgeAndResourceLimits'),
      link: '/staff/admin/system-limits',
    },
    {
      id: 'settings',
      title: 'Site Settings',
      icon: <Settings className="w-6 h-6" />,
      stats: 'Configured',
      color: 'from-earth-600 to-earth-700',
      description: 'General site configuration',
      link: '/staff/admin/site-settings',
    },
  ];

  const quickNavItems = [
    { label: 'Feature Flags', icon: <ToggleRight className="w-5 h-5" />, link: '/staff/admin/features', description: 'Manage feature toggles' },
    { label: 'Personalization', icon: <Palette className="w-5 h-5" />, link: '/staff/admin/personalization', description: t('admin.adminDashboard.configureThemesAndFonts') },
    { label: 'Financial Config', icon: <Wallet className="w-5 h-5" />, link: '/staff/admin/financial-config', description: 'Fine policies' },
    { label: 'Email Settings', icon: <Mail className="w-5 h-5" />, link: '/staff/admin/email-notifications', description: 'Notification settings' },
    { label: 'System Limits', icon: <Target className="w-5 h-5" />, link: '/staff/admin/system-limits', description: 'Resource thresholds' },
    { label: 'Site Settings', icon: <Settings className="w-5 h-5" />, link: '/staff/admin/site-settings', description: 'General configuration' },
  ];

  return (
    <AdminShell title="Admin Dashboard">
      <div className="min-h-screen bg-lsc-white dark:bg-earth-900">
        {/* Header Section */}
        <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 sticky top-0 z-10">
          <PageContainer width="wide" className="py-6">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                  Welcome, {user?.first_name || 'Admin'}
                </h1>
                <p className="text-earth-600 dark:text-lsc-cream/70 flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  Last login: {user?.last_login_at ? formatDate(new Date(user.last_login_at)) : 'Just now'}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setAutoRefresh(!autoRefresh);
                    toast.success(autoRefresh ? t('toast.adminDashboard.autorefreshDisabled') : t('toast.adminDashboard.autorefreshEnabled'));
                  }}
                  className={`p-2 rounded-lg transition-colors ${
                    autoRefresh
                      ? 'bg-earth-700 dark:bg-earth-600 text-white'
                      : 'bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-lsc-cream'
                  }`}
                  title={autoRefresh ? 'Disable auto-refresh' : 'Enable auto-refresh'}
                >
                  <RefreshCw className={`w-5 h-5 ${autoRefresh ? 'motion-safe:animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            {/* System Status Indicator */}
            <div className="mt-4 flex items-center gap-2">
              {(() => {
                const allHealthy = systemHealth.length > 0 && systemHealth.every(h => h.status === 'healthy');
                const hasError = systemHealth.some(h => h.status === 'error');
                const hasDegraded = systemHealth.some(h => h.status === 'degraded');

                if (allHealthy) {
                  return (
                    <div className="flex items-center gap-2 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-lg px-3 py-2">
                      <CheckCircle className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
                      <span className="text-sm font-medium text-status-success-700 dark:text-status-success-300">System Status: Operational</span>
                    </div>
                  );
                }
                if (hasError) {
                  return (
                    <div className="flex items-center gap-2 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg px-3 py-2">
                      <AlertCircle className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" />
                      <span className="text-sm font-medium text-status-danger-700 dark:text-status-danger-300">System Status: System Error</span>
                    </div>
                  );
                }
                if (hasDegraded) {
                  return (
                    <div className="flex items-center gap-2 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg px-3 py-2">
                      <AlertTriangle className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400" />
                      <span className="text-sm font-medium text-status-warning-700 dark:text-status-warning-300">System Status: Degraded</span>
                    </div>
                  );
                }
                return (
                  <div className="flex items-center gap-2 bg-lsc-cream dark:bg-earth-800/20 border border-lsc-border dark:border-earth-800 rounded-lg px-3 py-2">
                    <Clock className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">System Status: Checking...</span>
                  </div>
                );
              })()}
            </div>
          </PageContainer>
        </div>

        <PageContainer width="wide" className="py-8 space-y-8">
          <AdminGettingStartedChecklist />
          {/* Quick Stats Row */}
          <StatGrid columns={4}>
            {quickStats.map((stat) => (
              <StatCard
                key={stat.label}
                title={stat.label}
                value={stat.value}
                icon={stat.icon}
                color={stat.color}
              />
            ))}
          </StatGrid>

          {/* Configuration Overview Cards (3 columns, responsive) */}
          <div>
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">Configuration Overview</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {configCards.map((card) => {
                const content = (
                  <div className="p-5">
                    <div className="flex items-start justify-between mb-3">
                      <div className={`bg-gradient-to-br ${card.color} p-2 rounded-lg text-white`}>{card.icon}</div>
                    </div>
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-1">{card.title}</h3>
                    <p className="text-sm text-earth-600 dark:text-earth-400 mb-3">{card.description}</p>
                    <p className="text-sm font-semibold uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/70">{card.stats}</p>
                  </div>
                );
                return card.link ? (
                  <Link
                    key={card.id}
                    to={card.link}
                    className="group rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:shadow-lg dark:hover:shadow-earth-700/50 transition-all"
                  >
                    {content}
                  </Link>
                ) : (
                  <div
                    key={card.id}
                    className="group rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800"
                  >
                    {content}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Recent Changes Log */}
          <div>
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">Recent Changes Log</h2>
            <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm" aria-label={t('aria.adminDashboard.recentChangesLog')}>
                  <thead>
                    <tr className="border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-700/30">
                      <th scope="col" className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Timestamp</th>
                      <th scope="col" className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Admin</th>
                      <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Configuration Changed</th>
                      <th className="px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream">Change</th>
                      <th className="px-4 py-3 text-center font-semibold text-lsc-dark dark:text-lsc-cream">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentLogs.length > 0 ? (
                      recentLogs.map((log) => (
                        <React.Fragment key={log.id}>
                          <tr className="border-b border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/20 dark:hover:bg-earth-700/20 transition-colors">
                            <td className="px-4 py-3 text-lsc-dark dark:text-lsc-cream">
                              {new Date(log.created_at).toLocaleString()}
                            </td>
                            <td className="px-4 py-3 text-lsc-dark dark:text-lsc-cream">{log.admin_email || 'System'}</td>
                            <td className="px-4 py-3 text-lsc-dark dark:text-lsc-cream">{log.action}</td>
                            <td className="px-4 py-3">
                              <span className="inline-block bg-earth-50 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light px-2 py-1 rounded text-xs">
                                {log.old_value && log.new_value ? `${log.old_value} → ${log.new_value}` : 'Modified'}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <button
                                onClick={() => setExpandedLogId(expandedLogId === log.id ? null : log.id)}
                                className="text-lsc-rose hover:text-lsc-rose/70 font-medium"
                              >
                                {expandedLogId === log.id ? 'Hide' : 'Details'}
                              </button>
                            </td>
                          </tr>
                          {expandedLogId === log.id && (
                            <tr className="border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/10 dark:bg-earth-700/10">
                              <td colSpan={5} className="px-4 py-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                  <div>
                                    <p className="font-semibold text-lsc-dark dark:text-lsc-cream mb-1">Details</p>
                                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                                      Action: <span className="font-mono">{log.action}</span>
                                    </p>
                                    {log.target_user_email && (
                                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                                        Target User: <span className="font-mono">{log.target_user_email}</span>
                                      </p>
                                    )}
                                  </div>
                                  {log.reason && (
                                    <div>
                                      <p className="font-semibold text-lsc-dark dark:text-lsc-cream mb-1">Reason</p>
                                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{log.reason}</p>
                                    </div>
                                  )}
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                          No recent changes
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Quick Navigation Grid */}
          <div>
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">Quick Navigation</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {quickNavItems.map((item) => (
                <Link
                  key={item.label}
                  to={item.link}
                  className="group p-4 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg hover:border-lsc-rose dark:hover:border-lsc-rose hover:shadow-md dark:hover:shadow-orange-500/10 transition-all"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="text-lsc-rose group-hover:scale-110 transition-transform">{item.icon}</div>
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{item.label}</h3>
                  </div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.description}</p>
                </Link>
              ))}
            </div>
          </div>

          {/* System Health Section */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">System Health</h2>
              <Link
                to="/staff/admin/system-health"
                className="text-sm font-medium text-lsc-rose hover:text-lsc-rose/70 transition-colors"
              >
                View full dashboard &rarr;
              </Link>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {systemHealth.map((health) => (
                <div
                  key={health.name}
                  className="p-4 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{health.name}</p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{health.message}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                        Last checked: {new Date(health.lastChecked).toLocaleString()}
                      </p>
                    </div>
                    <div>
                      {health.status === 'healthy' && (
                        <CheckCircle className="w-6 h-6 text-status-success-600 dark:text-status-success-400" />
                      )}
                      {health.status === 'degraded' && (
                        <AlertTriangle className="w-6 h-6 text-status-warning-600 dark:text-status-warning-400" />
                      )}
                      {health.status === 'error' && <AlertCircle className="w-6 h-6 text-status-danger-600 dark:text-status-danger-400" />}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Helpful Tips Banner */}
          <div className="bg-gradient-to-r from-blue-50 to-blue-50/50 dark:from-blue-900/20 dark:to-blue-900/10 border border-lsc-border dark:border-earth-700 rounded-lg p-6">
            <div className="flex gap-4">
              <Lightbulb className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-serif font-semibold text-earth-900 dark:text-earth-200 mb-2">Quick Tips</h3>
                <ul className="space-y-1 text-sm text-earth-800 dark:text-lsc-rose-light/80">
                  <li>- Regularly review audit logs to track configuration changes</li>
                  <li>- Enable feature flags gradually to test new functionality</li>
                  <li>- Configure personalization options to match your library's branding</li>
                  <li>- Monitor system health to ensure optimal performance</li>
                  <li>
                    - Visit{' '}
                    <Link to="/help" className="underline hover:no-underline">
                      Admin Documentation
                    </Link>{' '}
                    for detailed guides
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Critical Configurations Check */}
          {!features?.email_notifications_enabled && (
            <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-4 flex gap-3">
              <AlertTriangle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-status-warning-900 dark:text-status-warning-100">Unconfigured: Email Notifications</p>
                <p className="text-sm text-status-warning-800 dark:text-status-warning-200 mt-1">
                  Email notifications are currently disabled. Consider enabling them for better user communication.
                </p>
              </div>
            </div>
          )}
        </PageContainer>
      </div>
    </AdminShell>
  );
}

// Helper functions
function formatDate(date: Date): string {
  return date.toLocaleDateString(getCurrentLocale(), {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function isWithinLast24Hours(dateString: string): boolean {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const hours = diffMs / (1000 * 60 * 60);
  return hours < 24;
}

