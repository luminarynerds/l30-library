/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react';
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext';
import api from '@/lib/api-client';
import toast from 'react-hot-toast';
import { API_BASE } from '@/api/types';
import {
  Truck,
  Save,
  RefreshCw,
  Map,
  Clock,
  Package,
  Info,
} from 'lucide-react';
import { AdminShell } from '../components/shells/AdminShell'
import { useTranslation} from '@/i18n'
interface HomeDeliveryConfig {
  home_delivery_default_checkout_days: number;
  home_delivery_reminder_days: number;
  home_delivery_feedback_delay_hours: number;
  home_delivery_max_items_per_delivery: number;
  home_delivery_service_time_minutes: number;
  home_delivery_average_speed_mph: number;
  mapping_provider: string;
  google_maps_api_key: string;
  mapbox_api_key: string;
  osrm_server_url: string;
}

const DEFAULT_HOME_DELIVERY_CONFIG: HomeDeliveryConfig = {
  home_delivery_default_checkout_days: 28,
  home_delivery_reminder_days: 1,
  home_delivery_feedback_delay_hours: 24,
  home_delivery_max_items_per_delivery: 10,
  home_delivery_service_time_minutes: 10,
  home_delivery_average_speed_mph: 25.0,
  mapping_provider: 'none',
  google_maps_api_key: '',
  mapbox_api_key: '',
  osrm_server_url: 'https://router.project-osrm.org',
};

export default function AdminHomeDeliverySettingsPage() {
  const { t } = useTranslation()
  const { features, loading: contextLoading, refetch } = useOrganizationFeatures();
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState<HomeDeliveryConfig>(DEFAULT_HOME_DELIVERY_CONFIG);

  useEffect(() => {
    if (features?.configuration) {
      const deliveryConfig = (features.configuration as Record<string, unknown>)?.home_delivery as HomeDeliveryConfig | undefined;
      if (deliveryConfig) {
        setConfig({ ...DEFAULT_HOME_DELIVERY_CONFIG, ...deliveryConfig });
      }
    }
  }, [features]);

  const handleNumberChange = (field: keyof HomeDeliveryConfig, value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      setConfig(prev => ({ ...prev, [field]: numValue }));
    }
  };

  const handleStringChange = (field: keyof HomeDeliveryConfig, value: string) => {
    setConfig(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const payload = {
        configuration: {
          ...(features?.configuration || {}),
          home_delivery: config,
        },
        reason: 'Admin update via home delivery settings UI',
      };
      await api.patch(`${API_BASE}/organization-features`, payload);
      await refetch();
      toast.success(t('admin.adminHomeDeliverySettings.homeDeliverySettingsUpdatedSuccessfully'));
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast.error(err.response?.data?.detail || t('toast.adminHomeDeliverySettings.failedToUpdateHomeDelivery'));
    } finally {
      setSaving(false);
    }
  };

  if (contextLoading || !features) {
    return (
      <AdminShell title="Home Delivery Settings">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      </AdminShell>
    );
  }

  return (
    <AdminShell title="Home Delivery Settings">
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <div className="flex items-center gap-3 mb-6">
          <Truck className="w-8 h-8 text-lsc-rose" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Home Delivery Settings
          </h1>
        </div>

        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-4 flex gap-3">
          <Info className="w-5 h-5 text-status-warning-700 dark:text-status-warning-300 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-status-warning-800 dark:text-status-warning-200">
            Configure home delivery service parameters including checkout periods, delivery limits,
            and route optimization. These settings affect the volunteer delivery program.
          </p>
        </div>

        {/* Delivery Policies */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 space-y-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 mb-4">
            <Package className="w-5 h-5 text-lsc-rose" />
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              Delivery Policies
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label htmlFor="home_delivery_default_checkout_days" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Default Checkout Period (days)
              </label>
              <input
                type="number"
                id="home_delivery_default_checkout_days"
                min={7}
                max={90}
                value={config.home_delivery_default_checkout_days}
                onChange={(e) => handleNumberChange('home_delivery_default_checkout_days', e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('admin.adminHomeDeliverySettings.loanPeriodForDeliveredItems')}</p>
            </div>

            <div>
              <label htmlFor="home_delivery_max_items_per_delivery" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Max Items Per Delivery
              </label>
              <input
                type="number"
                id="home_delivery_max_items_per_delivery"
                min={1}
                max={50}
                value={config.home_delivery_max_items_per_delivery}
                onChange={(e) => handleNumberChange('home_delivery_max_items_per_delivery', e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('admin.adminHomeDeliverySettings.maximumItemsPerSingleDelivery')}</p>
            </div>

            <div>
              <label htmlFor="home_delivery_reminder_days" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Reminder Before Due (days)
              </label>
              <input
                type="number"
                id="home_delivery_reminder_days"
                min={1}
                max={14}
                value={config.home_delivery_reminder_days}
                onChange={(e) => handleNumberChange('home_delivery_reminder_days', e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
            </div>

            <div>
              <label htmlFor="home_delivery_feedback_delay_hours" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Feedback Delay (hours)
              </label>
              <input
                type="number"
                id="home_delivery_feedback_delay_hours"
                min={1}
                max={168}
                value={config.home_delivery_feedback_delay_hours}
                onChange={(e) => handleNumberChange('home_delivery_feedback_delay_hours', e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('admin.adminHomeDeliverySettings.waitTimeBeforeRequestingDelivery')}</p>
            </div>
          </div>
        </div>

        {/* Route Optimization */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 space-y-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-lsc-rose" />
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              Route Estimates
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="home_delivery_service_time_minutes" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Service Time Per Stop (minutes)
              </label>
              <input
                type="number"
                id="home_delivery_service_time_minutes"
                min={1}
                max={60}
                value={config.home_delivery_service_time_minutes}
                onChange={(e) => handleNumberChange('home_delivery_service_time_minutes', e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('admin.adminHomeDeliverySettings.averageTimeSpentAtEach')}</p>
            </div>

            <div>
              <label htmlFor="home_delivery_average_speed_mph" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Average Speed (mph)
              </label>
              <input
                type="number"
                id="home_delivery_average_speed_mph"
                min={5}
                max={65}
                step={0.5}
                value={config.home_delivery_average_speed_mph}
                onChange={(e) => handleNumberChange('home_delivery_average_speed_mph', e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('admin.adminHomeDeliverySettings.usedForDeliveryTimeEstimates')}</p>
            </div>
          </div>
        </div>

        {/* Mapping Provider */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 space-y-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 mb-4">
            <Map className="w-5 h-5 text-lsc-rose" />
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              Mapping Provider
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label htmlFor="mapping-provider" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Provider
              </label>
              <select
                id="mapping-provider"
                value={config.mapping_provider}
                onChange={(e) => handleStringChange('mapping_provider', e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              >
                <option value="none">{t('admin.adminHomeDeliverySettings.noneNoRouteOptimization')}</option>
                <option value="google_maps">Google Maps</option>
                <option value="mapbox">Mapbox</option>
                <option value="osrm">OSRM (Open Source)</option>
              </select>
            </div>

            {config.mapping_provider === 'google_maps' && (
              <div className="md:col-span-2">
                <label htmlFor="google-maps-api-key" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Google Maps API Key
                </label>
                <input
                  id="google-maps-api-key"
                  type="password"
                  value={config.google_maps_api_key}
                  onChange={(e) => handleStringChange('google_maps_api_key', e.target.value)}
                  placeholder={t('placeholder.adminHomeDeliverySettings.aiza')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            )}

            {config.mapping_provider === 'mapbox' && (
              <div className="md:col-span-2">
                <label htmlFor="mapbox-api-key" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Mapbox API Key
                </label>
                <input
                  id="mapbox-api-key"
                  type="password"
                  value={config.mapbox_api_key}
                  onChange={(e) => handleStringChange('mapbox_api_key', e.target.value)}
                  placeholder={t('placeholder.adminHomeDeliverySettings.pk')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            )}

            {config.mapping_provider === 'osrm' && (
              <div className="md:col-span-2">
                <label htmlFor="osrm-server-url" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  OSRM Server URL
                </label>
                <input
                  id="osrm-server-url"
                  type="text"
                  value={config.osrm_server_url}
                  onChange={(e) => handleStringChange('osrm_server_url', e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            )}
          </div>
        </div>

        {/* Save */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 border border-lsc-border dark:border-earth-700">
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors disabled:opacity-50 font-medium"
          >
            {saving ? <RefreshCw className="w-5 h-5 motion-safe:animate-spin" /> : <Save className="w-5 h-5" />}
            {saving ? 'Saving...' : 'Save Home Delivery Settings'}
          </button>
        </div>
      </div>
    </AdminShell>
  );
}