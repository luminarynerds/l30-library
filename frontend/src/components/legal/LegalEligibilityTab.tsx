/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Check,
  Download,
  Edit,
  Loader2,
  Plus,
  Trash2,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { getCurrentLocale, useTranslation } from '@/i18n'

import {
  createEligibilityThreshold,
  deleteEligibilityThreshold,
  importFPG2026,
  listEligibilityThresholds,
  updateEligibilityThreshold,
  type EligibilityThreshold,
  type LegalProviderSummary,
} from '@/api/legal-api'

interface LegalEligibilityTabProps {
  providers: LegalProviderSummary[]
}

const HOUSEHOLD_SIZES = [1, 2, 3, 4, 5, 6, 7, 8]

function formatDollars(n: number | null | undefined): string {
  if (n == null) return '--'
  return `$${n.toLocaleString(getCurrentLocale())}`
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

interface ThresholdRowDraft {
  household_size: number
  income_limit: string
  percentage_of_fpl: string
  effective_date: string
  expires_date: string
}

function defaultDraft(): ThresholdRowDraft {
  return {
    household_size: 1,
    income_limit: '',
    percentage_of_fpl: '125',
    effective_date: new Date().toISOString().slice(0, 10),
    expires_date: '',
  }
}

export function LegalEligibilityTab({ providers }: LegalEligibilityTabProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [filterProviderId, setFilterProviderId] = useState<number | 'all'>('all')
  const [includeExpired, setIncludeExpired] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createDraft, setCreateDraft] = useState<ThresholdRowDraft>(defaultDraft())
  const [createProviderId, setCreateProviderId] = useState<number | ''>('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editDraft, setEditDraft] = useState<ThresholdRowDraft>(defaultDraft())
  const [importing, setImporting] = useState(false)
  const [importProviderId, setImportProviderId] = useState<number | ''>('')
  const [importPercent, setImportPercent] = useState<string>('125')
  const [importEffectiveDate, setImportEffectiveDate] = useState<string>(
    new Date().toISOString().slice(0, 10)
  )

  const { data, isLoading } = useQuery({
    queryKey: ['legal-eligibility-thresholds-admin', filterProviderId, includeExpired],
    queryFn: () => {
      const params: { provider_id?: number; include_expired?: boolean } = {
        include_expired: includeExpired,
      }
      if (filterProviderId !== 'all') {
        params.provider_id = filterProviderId
      }
      return listEligibilityThresholds(params)
    },
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['legal-eligibility-thresholds-admin'] })
  }

  const createMutation = useMutation({
    mutationFn: createEligibilityThreshold,
    onSuccess: () => {
      toast.success(t('legalEligibilityTab.thresholdAdded', 'Threshold added'))
      setCreating(false)
      setCreateDraft(defaultDraft())
      setCreateProviderId('')
      invalidate()
    },
    onError: () => toast.error(t('legalEligibilityTab.failedToAddThreshold', 'Failed to add threshold')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Parameters<typeof updateEligibilityThreshold>[1] }) =>
      updateEligibilityThreshold(id, body),
    onSuccess: () => {
      toast.success(t('legalEligibilityTab.thresholdUpdated', 'Threshold updated'))
      setEditingId(null)
      invalidate()
    },
    onError: () => toast.error(t('legalEligibilityTab.failedToUpdateThreshold', 'Failed to update threshold')),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteEligibilityThreshold,
    onSuccess: () => {
      toast.success(t('legalEligibilityTab.thresholdRemoved', 'Threshold removed'))
      invalidate()
    },
    onError: () => toast.error(t('legalEligibilityTab.failedToRemoveThreshold', 'Failed to remove threshold')),
  })

  const importMutation = useMutation({
    mutationFn: importFPG2026,
    onSuccess: (res) => {
      toast.success(t('legalEligibilityTab.importedXThresholds', { count: res.count }))
      setImporting(false)
      invalidate()
    },
    onError: () => toast.error(t('legalEligibilityTab.failedToImportFpgTable', 'Failed to import FPG table')),
  })

  const thresholds = data?.thresholds ?? []

  const grouped = useMemo(() => {
    const map = new Map<string, { provider_id: number; provider_name: string; percentage_of_fpl: number; rows: EligibilityThreshold[] }>()
    for (const t of thresholds) {
      const key = `${t.provider_id}::${t.percentage_of_fpl}`
      const existing = map.get(key)
      if (existing) {
        existing.rows.push(t)
      } else {
        map.set(key, {
          provider_id: t.provider_id,
          provider_name: t.provider_name ?? `Provider #${t.provider_id}`,
          percentage_of_fpl: t.percentage_of_fpl,
          rows: [t],
        })
      }
    }
    for (const group of map.values()) {
      group.rows.sort((a, b) => a.household_size - b.household_size)
    }
    return Array.from(map.values()).sort((a, b) => {
      if (a.provider_name === b.provider_name) {
        return a.percentage_of_fpl - b.percentage_of_fpl
      }
      return a.provider_name.localeCompare(b.provider_name)
    })
  }, [thresholds])

  const parseIntField = (raw: string): number | null => {
    const cleaned = raw.replace(/[^\d]/g, '')
    if (!cleaned) return null
    const parsed = parseInt(cleaned, 10)
    return Number.isFinite(parsed) ? parsed : null
  }

  const handleCreate = () => {
    if (!createProviderId) {
      toast.error(t('legalEligibilityTab.selectAProvider', 'Select a provider'))
      return
    }
    const income = parseIntField(createDraft.income_limit)
    const percent = parseIntField(createDraft.percentage_of_fpl)
    if (income == null || percent == null) {
      toast.error(t('legalEligibilityTab.enterIncomeLimitAnd', 'Enter income limit and percentage'))
      return
    }
    if (!createDraft.effective_date) {
      toast.error(t('legalEligibilityTab.enterEffectiveDate', 'Enter effective date'))
      return
    }
    createMutation.mutate({
      provider_id: Number(createProviderId),
      household_size: createDraft.household_size,
      income_limit: income,
      percentage_of_fpl: percent,
      effective_date: createDraft.effective_date,
      expires_date: createDraft.expires_date || null,
    })
  }

  const handleStartEdit = (t: EligibilityThreshold) => {
    setEditingId(t.id)
    setEditDraft({
      household_size: t.household_size,
      income_limit: String(t.income_limit),
      percentage_of_fpl: String(t.percentage_of_fpl),
      effective_date: t.effective_date,
      expires_date: t.expires_date ?? '',
    })
  }

  const handleSaveEdit = () => {
    if (editingId == null) return
    const income = parseIntField(editDraft.income_limit)
    const percent = parseIntField(editDraft.percentage_of_fpl)
    if (income == null || percent == null) {
      toast.error(t('legalEligibilityTab.enterIncomeLimitAnd', 'Enter income limit and percentage'))
      return
    }
    updateMutation.mutate({
      id: editingId,
      body: {
        household_size: editDraft.household_size,
        income_limit: income,
        percentage_of_fpl: percent,
        effective_date: editDraft.effective_date,
        expires_date: editDraft.expires_date || null,
      },
    })
  }

  const handleDelete = (id: number) => {
    if (!confirm(t('legalEligibilityTab.removeThisThresholdThis', 'Remove this threshold? This cannot be undone.'))) return
    deleteMutation.mutate(id)
  }

  const handleImport = () => {
    if (!importProviderId) {
      toast.error(t('legalEligibilityTab.selectAProvider', 'Select a provider'))
      return
    }
    const percent = parseIntField(importPercent)
    if (percent == null) {
      toast.error(t('legalEligibilityTab.enterPercentageOfFpl', 'Enter percentage of FPL'))
      return
    }
    if (!importEffectiveDate) {
      toast.error(t('legalEligibilityTab.enterEffectiveDate', 'Enter effective date'))
      return
    }
    importMutation.mutate({
      provider_id: Number(importProviderId),
      percentage_of_fpl: percent,
      effective_date: importEffectiveDate,
      expire_existing: true,
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">
          {t('legalEligibilityTab.incomeEligibilityThresholdsX', { count: data?.total ?? 0 })}
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setImporting((v) => !v)}
            className="flex items-center gap-2 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm"
          >
            <Download className="w-4 h-4" />
            {t('legalEligibilityTab.import2026Fpg', 'Import 2026 FPG')}
          </button>
          <button
            onClick={() => setCreating((v) => !v)}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            {t('legalEligibilityTab.addThreshold', 'Add Threshold')}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2 text-lsc-dark dark:text-earth-50">
          <span>{t('legalEligibilityTab.provider', 'Provider')}</span>
          <select
            value={filterProviderId}
            onChange={(e) =>
              setFilterProviderId(e.target.value === 'all' ? 'all' : Number(e.target.value))
            }
            className="px-2 py-1 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
          >
            <option value="all">{t('legalEligibilityTab.allProviders', 'All providers')}</option>
            {providers.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-lsc-dark dark:text-earth-50">
          <input
            type="checkbox"
            checked={includeExpired}
            onChange={(e) => setIncludeExpired(e.target.checked)}
          />
          <span>{t('legalEligibilityTab.includeExpired', 'Include expired')}</span>
        </label>
      </div>

      {importing && (
        <div className="bg-lsc-cream/50 dark:bg-earth-900/50 border border-lsc-border dark:border-earth-700 rounded-xl p-4 space-y-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" />
            <p className="text-sm text-lsc-dark dark:text-earth-50">
              {t('legalEligibilityTab.bulkinsertThe2026Federal', 'Bulk-insert the 2026 Federal Poverty Guidelines for one provider, household sizes 1 to 8. Existing active rows at the same percentage will be expired the day before the effective date.')}
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <label className="flex flex-col gap-1 text-xs text-lsc-dark dark:text-earth-50">
              <span className="font-medium">{t('legalEligibilityTab.provider', 'Provider')}</span>
              <select
                value={importProviderId}
                onChange={(e) =>
                  setImportProviderId(e.target.value ? Number(e.target.value) : '')
                }
                className="px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              >
                <option value="">{t('legalEligibilityTab.selectProvider', 'Select provider')}</option>
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-lsc-dark dark:text-earth-50">
              <span className="font-medium">{t('legalEligibilityTab.percentOfFpl', '% of FPL')}</span>
              <input
                type="number"
                min="0"
                max="1000"
                value={importPercent}
                onChange={(e) => setImportPercent(e.target.value)}
                className="px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-lsc-dark dark:text-earth-50">
              <span className="font-medium">{t('legalEligibilityTab.effectiveDate', 'Effective date')}</span>
              <input
                type="date"
                value={importEffectiveDate}
                onChange={(e) => setImportEffectiveDate(e.target.value)}
                className="px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </label>
            <div className="flex items-end gap-2">
              <button
                onClick={handleImport}
                disabled={importMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium disabled:opacity-50"
              >
                {importMutation.isPending ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                {t('legalEligibilityTab.importAction', 'Import')}
              </button>
              <button
                onClick={() => setImporting(false)}
                className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm"
              >
                {t('common.cancel')}
              </button>
            </div>
          </div>
        </div>
      )}

      {creating && (
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4 space-y-3">
          <h3 className="font-medium text-sm text-lsc-dark dark:text-earth-50">{t('legalEligibilityTab.newThreshold', 'New threshold')}</h3>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            <label className="flex flex-col gap-1 text-xs text-lsc-dark dark:text-earth-50 col-span-2">
              <span className="font-medium">{t('legalEligibilityTab.provider', 'Provider')}</span>
              <select
                value={createProviderId}
                onChange={(e) =>
                  setCreateProviderId(e.target.value ? Number(e.target.value) : '')
                }
                className="px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              >
                <option value="">{t('legalEligibilityTab.selectProvider', 'Select provider')}</option>
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-lsc-dark dark:text-earth-50">
              <span className="font-medium">{t('legalEligibilityTab.household', 'Household')}</span>
              <select
                value={createDraft.household_size}
                onChange={(e) =>
                  setCreateDraft({ ...createDraft, household_size: Number(e.target.value) })
                }
                className="px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              >
                {HOUSEHOLD_SIZES.map((n) => (
                  <option key={n} value={n}>{n === 8 ? '8+' : n}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-lsc-dark dark:text-earth-50">
              <span className="font-medium">{t('legalEligibilityTab.incomeLimit', 'Income limit ($)')}</span>
              <input
                type="text"
                inputMode="numeric"
                value={createDraft.income_limit}
                onChange={(e) =>
                  setCreateDraft({ ...createDraft, income_limit: e.target.value })
                }
                className="px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-lsc-dark dark:text-earth-50">
              <span className="font-medium">{t('legalEligibilityTab.percentOfFpl', '% of FPL')}</span>
              <input
                type="number"
                min="0"
                max="1000"
                value={createDraft.percentage_of_fpl}
                onChange={(e) =>
                  setCreateDraft({ ...createDraft, percentage_of_fpl: e.target.value })
                }
                className="px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-lsc-dark dark:text-earth-50">
              <span className="font-medium">{t('legalEligibilityTab.effective', 'Effective')}</span>
              <input
                type="date"
                value={createDraft.effective_date}
                onChange={(e) =>
                  setCreateDraft({ ...createDraft, effective_date: e.target.value })
                }
                className="px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-lsc-dark dark:text-earth-50">
              <span className="font-medium">{t('legalEligibilityTab.expiresOptional', 'Expires (optional)')}</span>
              <input
                type="date"
                value={createDraft.expires_date}
                onChange={(e) =>
                  setCreateDraft({ ...createDraft, expires_date: e.target.value })
                }
                className="px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </label>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCreate}
              disabled={createMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium disabled:opacity-50"
            >
              {createMutation.isPending ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              {t('common.save')}
            </button>
            <button
              onClick={() => {
                setCreating(false)
                setCreateDraft(defaultDraft())
                setCreateProviderId('')
              }}
              className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm"
            >
              {t('common.cancel')}
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : grouped.length === 0 ? (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl">
          <p className="text-lsc-dark dark:text-earth-50 font-medium">{t('legalEligibilityTab.noThresholdsConfigured', 'No thresholds configured')}</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {t('legalEligibilityTab.addThresholdsManuallyOrUse', 'Add thresholds manually, or use Import 2026 FPG to seed standard LSC limits.')}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {grouped.map((group) => (
            <div
              key={`${group.provider_id}-${group.percentage_of_fpl}`}
              className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden"
            >
              <div className="px-4 py-2 bg-lsc-cream/50 dark:bg-earth-900/50 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <div>
                  <h3 className="font-medium text-sm text-lsc-dark dark:text-earth-50">
                    {group.provider_name}
                  </h3>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('legalEligibilityTab.percentOfFederalPovertyLevel', { percent: group.percentage_of_fpl })}
                  </p>
                </div>
              </div>
              <table className="w-full text-sm">
                <thead className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 border-b border-lsc-border dark:border-earth-700">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">{t('legalEligibilityTab.household', 'Household')}</th>
                    <th className="px-4 py-2 text-left font-medium">{t('legalEligibilityTab.incomeLimitColumn', 'Income limit')}</th>
                    <th className="px-4 py-2 text-left font-medium">{t('legalEligibilityTab.percentFpl', '% FPL')}</th>
                    <th className="px-4 py-2 text-left font-medium">{t('legalEligibilityTab.effective', 'Effective')}</th>
                    <th className="px-4 py-2 text-left font-medium">{t('legalEligibilityTab.expires', 'Expires')}</th>
                    <th className="px-4 py-2 text-right font-medium">{t('legalEligibilityTab.actions', 'Actions')}</th>
                  </tr>
                </thead>
                <tbody className="text-lsc-dark dark:text-earth-50">
                  {group.rows.map((row) => {
                    const isEditing = editingId === row.id
                    return (
                      <tr
                        key={row.id}
                        className="border-b border-lsc-border/60 dark:border-earth-700/60 last:border-0"
                      >
                        {isEditing ? (
                          <>
                            <td className="px-4 py-2">
                              <select
                                value={editDraft.household_size}
                                onChange={(e) =>
                                  setEditDraft({
                                    ...editDraft,
                                    household_size: Number(e.target.value),
                                  })
                                }
                                className="px-2 py-1 border border-lsc-border dark:border-earth-700 rounded bg-lsc-white dark:bg-earth-900"
                              >
                                {HOUSEHOLD_SIZES.map((n) => (
                                  <option key={n} value={n}>{n === 8 ? '8+' : n}</option>
                                ))}
                              </select>
                            </td>
                            <td className="px-4 py-2">
                              <input
                                type="text"
                                inputMode="numeric"
                                value={editDraft.income_limit}
                                onChange={(e) =>
                                  setEditDraft({
                                    ...editDraft,
                                    income_limit: e.target.value,
                                  })
                                }
                                className="w-24 px-2 py-1 border border-lsc-border dark:border-earth-700 rounded bg-lsc-white dark:bg-earth-900"
                              />
                            </td>
                            <td className="px-4 py-2">
                              <input
                                type="number"
                                value={editDraft.percentage_of_fpl}
                                onChange={(e) =>
                                  setEditDraft({
                                    ...editDraft,
                                    percentage_of_fpl: e.target.value,
                                  })
                                }
                                className="w-16 px-2 py-1 border border-lsc-border dark:border-earth-700 rounded bg-lsc-white dark:bg-earth-900"
                              />
                            </td>
                            <td className="px-4 py-2">
                              <input
                                type="date"
                                value={editDraft.effective_date}
                                onChange={(e) =>
                                  setEditDraft({
                                    ...editDraft,
                                    effective_date: e.target.value,
                                  })
                                }
                                className="px-2 py-1 border border-lsc-border dark:border-earth-700 rounded bg-lsc-white dark:bg-earth-900"
                              />
                            </td>
                            <td className="px-4 py-2">
                              <input
                                type="date"
                                value={editDraft.expires_date}
                                onChange={(e) =>
                                  setEditDraft({
                                    ...editDraft,
                                    expires_date: e.target.value,
                                  })
                                }
                                className="px-2 py-1 border border-lsc-border dark:border-earth-700 rounded bg-lsc-white dark:bg-earth-900"
                              />
                            </td>
                            <td className="px-4 py-2 text-right">
                              <div className="inline-flex items-center gap-1">
                                <button
                                  onClick={handleSaveEdit}
                                  disabled={updateMutation.isPending}
                                  className="p-1.5 text-status-success-700 dark:text-status-success-300 hover:bg-status-success-100 dark:hover:bg-status-success-900/30 rounded disabled:opacity-50"
                                  aria-label={t('legalEligibilityTab.saveChanges', 'Save changes')}
                                >
                                  {updateMutation.isPending ? (
                                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                                  ) : (
                                    <Check className="w-4 h-4" />
                                  )}
                                </button>
                                <button
                                  onClick={() => setEditingId(null)}
                                  className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded"
                                  aria-label={t('legalEligibilityTab.cancelEdit', 'Cancel edit')}
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </>
                        ) : (
                          <>
                            <td className="px-4 py-2">
                              {row.household_size === 8 ? '8+' : row.household_size}
                            </td>
                            <td className="px-4 py-2">{formatDollars(row.income_limit)}</td>
                            <td className="px-4 py-2">{row.percentage_of_fpl}%</td>
                            <td className="px-4 py-2">{formatDate(row.effective_date)}</td>
                            <td className="px-4 py-2">
                              {row.expires_date ? formatDate(row.expires_date) : t('legalEligibilityTab.current', 'Current')}
                            </td>
                            <td className="px-4 py-2 text-right">
                              <div className="inline-flex items-center gap-1">
                                <button
                                  onClick={() => handleStartEdit(row)}
                                  className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded"
                                  aria-label={t('legalEligibilityTab.editThreshold', 'Edit threshold')}
                                >
                                  <Edit className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleDelete(row.id)}
                                  disabled={deleteMutation.isPending}
                                  className="p-1.5 text-status-danger-700 dark:text-status-danger-300 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 rounded disabled:opacity-50"
                                  aria-label={t('legalEligibilityTab.deleteThreshold', 'Delete threshold')}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </>
                        )}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
