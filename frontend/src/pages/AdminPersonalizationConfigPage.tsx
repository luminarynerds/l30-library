/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react';
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext';
import api from '@/lib/api-client';
import toast from 'react-hot-toast';
import { API_BASE } from '@/api/types';
import {
  Settings,
  Save,
  RefreshCw,
  Plus,
  Trash2,
  ChevronUp,
  ChevronDown,
  Eye,
  Palette,
  Type,
  Clock,
} from 'lucide-react';
import { AdminShell } from '../components/shells/AdminShell'
import ConfirmDialog from '../components/ConfirmDialog'
import { useTranslation} from '@/i18n'
interface OptionConfig {
  id: string;
  value: string;
  description: string;
  preview?: React.ReactNode;
}

interface ConfigSection {
  key: 'enabled_themes' | 'enabled_fonts' | 'enabled_focus_modes';
  label: string;
  description: string;
  icon: React.ElementType;
  options: OptionConfig[];
  availableOptions: OptionConfig[];
}

// Define all available options for each category
const AVAILABLE_THEMES: OptionConfig[] = [
  {
    id: 'light',
    value: 'light',
    description: 'Bright background with dark text, ideal for daytime use',
    preview: (
      <div className="flex items-center justify-center h-16 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded">
        <span className="text-lsc-dark dark:text-lsc-cream text-sm">Light Theme</span>
      </div>
    ),
  },
  {
    id: 'dark',
    value: 'dark',
    description: 'Dark background with light text, easy on eyes in low light',
    preview: (
      <div className="flex items-center justify-center h-16 bg-earth-800 border border-earth-700 rounded">
        <span className="text-white text-sm">Dark Theme</span>
      </div>
    ),
  },
  {
    id: 'high-contrast',
    value: 'high-contrast',
    description: 'Maximum contrast for better visibility and accessibility',
    preview: (
      <div className="flex items-center justify-center h-16 bg-black border-2 border-status-warning-400 rounded">
        <span className="text-status-warning-400 text-sm font-bold">High Contrast</span>
      </div>
    ),
  },
  {
    id: 'sepia',
    value: 'sepia',
    description: 'Warm, vintage appearance with reduced blue light',
    preview: (
      <div className="flex items-center justify-center h-16 bg-status-warning-100 dark:bg-status-warning-900/30 border border-status-warning-200 dark:border-status-warning-800 rounded">
        <span className="text-status-warning-900 dark:text-status-warning-200 text-sm">Sepia Theme</span>
      </div>
    ),
  },
];

const AVAILABLE_FONTS: OptionConfig[] = [
  {
    id: 'default',
    value: 'default',
    description: 'Standard sans-serif font for general readability',
    preview: (
      <div className="flex items-center justify-center h-16 bg-earth-50 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded font-sans">
        <span className="text-lsc-dark dark:text-lsc-cream">Aa Default</span>
      </div>
    ),
  },
  {
    id: 'dyslexia-friendly',
    value: 'dyslexia-friendly',
    description: 'Atkinson Hyperlegible font for clearer letterforms',
    preview: (
      <div className="flex items-center justify-center h-16 bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded">
        <span className="text-earth-900 dark:text-lsc-rose-light/80">Aa Dyslexia-Friendly</span>
      </div>
    ),
  },
  {
    id: 'large',
    value: 'large',
    description: 'Larger default font size for better visibility',
    preview: (
      <div className="flex items-center justify-center h-16 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded">
        <span className="text-status-success-900 dark:text-status-success-200 text-lg">Aa Large</span>
      </div>
    ),
  },
  {
    id: 'monospace',
    value: 'monospace',
    description: 'Fixed-width monospace font for code and technical content',
    preview: (
      <div className="flex items-center justify-center h-16 bg-category-50 dark:bg-category-900/20 border border-category-200 dark:border-category-800 rounded font-mono">
        <span className="text-category-900 dark:text-category-200">Aa Mono</span>
      </div>
    ),
  },
];

const AVAILABLE_FOCUS_MODES: OptionConfig[] = [
  {
    id: 'pomodoro',
    value: 'pomodoro',
    description: '25-minute focused work sessions with 5-minute breaks',
    preview: (
      <div className="flex items-center justify-center h-16 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded">
        <span className="text-status-danger-900 dark:text-status-danger-200 text-sm">25/5 Pomodoro</span>
      </div>
    ),
  },
  {
    id: 'zen',
    value: 'zen',
    description: 'Distraction-free mode with minimal UI elements',
    preview: (
      <div className="flex items-center justify-center h-16 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded">
        <span className="text-status-warning-900 dark:text-status-warning-200 text-sm">Zen Mode</span>
      </div>
    ),
  },
  {
    id: 'timed',
    value: 'timed',
    description: 'Customizable timer for flexible work intervals',
    preview: (
      <div className="flex items-center justify-center h-16 bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800 rounded">
        <span className="text-cyan-900 dark:text-cyan-200 text-sm">Custom Timer</span>
      </div>
    ),
  },
  {
    id: 'forest',
    value: 'forest',
    description: 'Grow a virtual forest while maintaining focus',
    preview: (
      <div className="flex items-center justify-center h-16 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded">
        <span className="text-status-success-900 dark:text-status-success-200 text-sm">Forest</span>
      </div>
    ),
  },
];

export default function AdminPersonalizationConfigPage() {
  const { t } = useTranslation()
  const { features, loading: contextLoading, refetch } = useOrganizationFeatures();
  const [saving, setSaving] = useState(false);
  const [reason, setReason] = useState('');
  const [newOptionValues, setNewOptionValues] = useState({
    enabled_themes: '',
    enabled_fonts: '',
    enabled_focus_modes: '',
  });
  const [configs, setConfigs] = useState<ConfigSection[]>([]);
  const [removeConfirm, setRemoveConfirm] = useState<{ sectionKey: ConfigSection['key']; value: string } | null>(null);

  useEffect(() => {
    if (features) {
      setConfigs([
        {
          key: 'enabled_themes',
          label: 'Themes',
          description: t('admin.adminPersonalizationConfig.visualAppearanceOptionsForUsers'),
          icon: Palette,
          options: (features.enabled_themes || []).map(
            (value) =>
              AVAILABLE_THEMES.find((t) => t.value === value) || {
                id: value,
                value,
                description: 'Custom theme',
              }
          ),
          availableOptions: AVAILABLE_THEMES,
        },
        {
          key: 'enabled_fonts',
          label: 'Fonts',
          description: t('admin.adminPersonalizationConfig.fontOptionsForImprovedReadability'),
          icon: Type,
          options: (features.enabled_fonts || []).map(
            (value) =>
              AVAILABLE_FONTS.find((f) => f.value === value) || {
                id: value,
                value,
                description: 'Custom font',
              }
          ),
          availableOptions: AVAILABLE_FONTS,
        },
        {
          key: 'enabled_focus_modes',
          label: 'Focus Modes',
          description: t('admin.adminPersonalizationConfig.productivityAndDistractionManagementFeatures'),
          icon: Clock,
          options: (features.enabled_focus_modes || []).map(
            (value) =>
              AVAILABLE_FOCUS_MODES.find((f) => f.value === value) || {
                id: value,
                value,
                description: 'Custom focus mode',
              }
          ),
          availableOptions: AVAILABLE_FOCUS_MODES,
        },
      ]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [features]);

  const getAvailableOptionsForSection = (config: ConfigSection) => {
    return config.availableOptions.filter(
      (option) => !config.options.some((selected) => selected.value === option.value)
    );
  };

  const handleAddOption = (sectionKey: ConfigSection['key'], value: string) => {
    if (!value) {
      toast.error(t('admin.adminPersonalizationConfig.pleaseSelectAnOption'));
      return;
    }

    setConfigs((prevConfigs) =>
      prevConfigs.map((config) => {
        if (config.key === sectionKey) {
          const selectedOption =
            config.availableOptions.find((o) => o.value === value) ||
            {
              id: value,
              value,
              description: 'Custom option',
            };

          return {
            ...config,
            options: [...config.options, selectedOption],
          };
        }
        return config;
      })
    );

    setNewOptionValues((prev) => ({
      ...prev,
      [sectionKey]: '',
    }));
  };

  const handleRemoveOption = (sectionKey: ConfigSection['key'], value: string) => {
    setConfigs((prevConfigs) =>
      prevConfigs.map((config) => {
        if (config.key === sectionKey) {
          return {
            ...config,
            options: config.options.filter((o) => o.value !== value),
          };
        }
        return config;
      })
    );
  };

  const handleMoveOption = (
    sectionKey: ConfigSection['key'],
    value: string,
    direction: 'up' | 'down'
  ) => {
    setConfigs((prevConfigs) =>
      prevConfigs.map((config) => {
        if (config.key === sectionKey) {
          const index = config.options.findIndex((o) => o.value === value);
          if (
            (direction === 'up' && index === 0) ||
            (direction === 'down' && index === config.options.length - 1)
          ) {
            return config;
          }

          const newOptions = [...config.options];
          const newIndex = direction === 'up' ? index - 1 : index + 1;
          [newOptions[index], newOptions[newIndex]] = [newOptions[newIndex]!, newOptions[index]!];

          return {
            ...config,
            options: newOptions,
          };
        }
        return config;
      })
    );
  };

  const handleSave = async () => {
    try {
      setSaving(true);

      const payload = {
        enabled_themes: configs
          .find((c) => c.key === 'enabled_themes')
          ?.options.map((o) => o.value) || [],
        enabled_fonts: configs
          .find((c) => c.key === 'enabled_fonts')
          ?.options.map((o) => o.value) || [],
        enabled_focus_modes: configs
          .find((c) => c.key === 'enabled_focus_modes')
          ?.options.map((o) => o.value) || [],
        reason: reason || 'Admin update via personalization settings UI',
      };

      await api.patch(`${API_BASE}/organization-features`, payload);
      await refetch();
      toast.success(t('admin.adminPersonalizationConfig.personalizationSettingsUpdatedSuccessfully'));
      setReason('');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast.error(err.response?.data?.detail || t('toast.adminPersonalizationConfig.failedToUpdatePersonalizationSettings'));
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    } finally {
      setSaving(false);
    }
  };

  if (contextLoading || !features) {
    return (
      <AdminShell title="Personalization Configuration">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      </AdminShell>
    );
  }

  return (
    <AdminShell title="Personalization Configuration">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Settings className="w-8 h-8 text-lsc-rose" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Personalization Configuration
          </h1>
        </div>

        {/* Info Banner */}
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-4">
          <p className="text-sm text-status-warning-800 dark:text-status-warning-200">
            Manage the personalization options available to all users. These settings control
            which themes, fonts, and focus modes appear in user preferences library-wide.
          </p>
        </div>

        {/* Configuration Sections */}
        <div className="space-y-6">
          {configs.map((config) => (
            <div
              key={config.key}
              className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6"
            >
              {/* Section Header */}
              <div className="flex items-center gap-2 mb-6">
                <config.icon className="w-6 h-6 text-lsc-rose" />
                <div>
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    {config.label}
                  </h2>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{config.description}</p>
                </div>
              </div>

              {/* Add New Option */}
              <div className="mb-6 p-4 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                <label htmlFor={`add-option-${config.key}`} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Add New Option
                </label>
                <div className="flex gap-2">
                  <select
                    id={`add-option-${config.key}`}
                    value={newOptionValues[config.key]}
                    onChange={(e) =>
                      setNewOptionValues((prev) => ({
                        ...prev,
                        [config.key]: e.target.value,
                      }))
                    }
                    className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  >
                    <option value="">Select an option...</option>
                    {getAvailableOptionsForSection(config).map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.value} - {option.description}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleAddOption(config.key, newOptionValues[config.key])}
                    className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Add
                  </button>
                </div>
                {getAvailableOptionsForSection(config).length === 0 && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                    All available options are already enabled.
                  </p>
                )}
              </div>

              {/* Current Options */}
              <div>
                <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                  Enabled Options ({config.options.length})
                </h3>

                {config.options.length === 0 ? (
                  <div className="text-center py-6 text-lsc-dark/70 dark:text-lsc-cream/70">
                    No options enabled yet. Add one to get started.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {config.options.map((option, index) => (
                      <div
                        key={option.value}
                        className="border border-lsc-border dark:border-earth-700 rounded-lg p-4"
                      >
                        <div className="flex items-start justify-between gap-4">
                          {/* Option Details */}
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                                {option.value}
                              </span>
                              <span className="px-2 py-1 text-xs bg-earth-100 dark:bg-earth-800 text-earth-800 dark:text-lsc-rose-light/80 rounded">
                                Position {index + 1}
                              </span>
                            </div>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                              {option.description}
                            </p>

                            {/* Preview */}
                            {option.preview && (
                              <div className="mt-3">
                                <label className="flex items-center gap-2 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                                  <Eye className="w-3 h-3" />
                                  Preview
                                </label>
                                {option.preview}
                              </div>
                            )}
                          </div>

                          {/* Actions */}
                          <div className="flex flex-col gap-2">
                            <button
                              onClick={() => handleMoveOption(config.key, option.value, 'up')}
                              disabled={index === 0}
                              aria-label={`Move ${option.value} up`}
                              className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                              title="Move up"
                            >
                              <ChevronUp className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleMoveOption(config.key, option.value, 'down')}
                              disabled={index === config.options.length - 1}
                              aria-label={`Move ${option.value} down`}
                              className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                              title="Move down"
                            >
                              <ChevronDown className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setRemoveConfirm({ sectionKey: config.key, value: option.value })}
                              aria-label={`Remove ${option.value}`}
                              className="p-2 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded transition-colors"
                              title="Remove option"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Reason & Save Section */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 space-y-4">
          <div>
            <label htmlFor="personalization-reason" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Reason for Changes (optional)
            </label>
            <textarea
              id="personalization-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t('admin.adminPersonalizationConfig.describeWhyYouReMaking')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              rows={3}
            />
          </div>

          {/* Summary */}
          <div className="grid grid-cols-3 gap-4 p-3 bg-earth-50 dark:bg-earth-700/50 rounded">
            <div>
              <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                Themes Enabled
              </p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {configs.find((c) => c.key === 'enabled_themes')?.options.length || 0}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                Fonts Enabled
              </p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {configs.find((c) => c.key === 'enabled_fonts')?.options.length || 0}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                Focus Modes Enabled
              </p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {configs.find((c) => c.key === 'enabled_focus_modes')?.options.length || 0}
              </p>
            </div>
          </div>

          {/* Save Button */}
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors disabled:opacity-50 font-medium"
          >
            {saving ? (
              <RefreshCw className="w-5 h-5 motion-safe:animate-spin" />
            ) : (
              <Save className="w-5 h-5" />
            )}
            {saving ? 'Saving...' : 'Save Personalization Settings'}
          </button>
        </div>
      </div>

      <ConfirmDialog
        isOpen={removeConfirm !== null}
        title="Remove this option?"
        message={`This will remove "${removeConfirm?.value}" from the available options. You can re-add it later. Remember to save your changes.`}
        confirmText="Yes, remove it"
        cancelText="Keep it"
        confirmVariant="danger"
        onConfirm={() => {
          if (removeConfirm) {
            handleRemoveOption(removeConfirm.sectionKey, removeConfirm.value);
            toast.success(t('toast.adminPersonalizationConfig.valueRemoved', { value: removeConfirm.value }));
            setRemoveConfirm(null);
          }
        }}
        onCancel={() => setRemoveConfirm(null)}
      />
    </AdminShell>
  );
}