/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { StrategicKPI, KPICreateData, KPIUpdateData } from '@/api/domains/admin/strategic-api'

interface Props {
  editing: Partial<StrategicKPI> & { name: string }
  setEditing: (v: Partial<StrategicKPI> & { name: string }) => void
  onSave: () => void
  onClose: () => void
}

const categoryOptions = ['Financial', 'Operational', 'Customer', 'Learning']

const frequencyOptions = [
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'annually', label: 'Annually' },
]

export type KPIFormData = KPICreateData & Pick<KPIUpdateData, 'is_active'>

export default function KPIModal({ editing, setEditing, onSave, onClose }: Props) {
  const isEdit = !!editing.id

  const field = <K extends keyof typeof editing>(key: K) => ({
    value: (editing[key] ?? '') as string,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setEditing({ ...editing, [key]: e.target.value }),
  })

  return (
    <ModalBackdrop onClose={onClose} title={isEdit ? 'Edit KPI' : 'Add KPI'}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {isEdit ? 'Edit KPI' : 'Add KPI'}
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Name *</label>
              <input
                type="text"
                value={editing.name}
                onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Description</label>
              <textarea
                {...field('description')}
                rows={2}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Category</label>
                <select
                  value={editing.category || ''}
                  onChange={(e) => setEditing({ ...editing, category: e.target.value || undefined })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="">— select —</option>
                  {categoryOptions.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Unit of Measure</label>
                <input
                  type="text"
                  {...field('unit_of_measure')}
                  placeholder="e.g. %, count, $"
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Frequency</label>
                <select
                  value={editing.frequency || 'monthly'}
                  onChange={(e) => setEditing({ ...editing, frequency: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                >
                  {frequencyOptions.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Data Source</label>
                <input
                  type="text"
                  {...field('data_source')}
                  placeholder="e.g. ILS, survey"
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Target Value</label>
                <input
                  type="number"
                  step="any"
                  {...field('target_value')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Baseline Value</label>
                <input
                  type="number"
                  step="any"
                  {...field('baseline_value')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Alert Thresholds</label>
              <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mb-2">
                Alerts fire when a recorded value falls below this. Leave thresholds empty for lower-is-better KPIs.
              </p>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs text-status-danger-600 dark:text-status-danger-400 mb-1">Red (critical)</label>
                  <input
                    type="number"
                    step="any"
                    {...field('threshold_red')}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-yellow-600 dark:text-yellow-400 mb-1">Yellow (warning)</label>
                  <input
                    type="number"
                    step="any"
                    {...field('threshold_yellow')}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-status-success-600 dark:text-status-success-400 mb-1">Green (info)</label>
                  <input
                    type="number"
                    step="any"
                    {...field('threshold_green')}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm"
                  />
                </div>
              </div>
            </div>

            {isEdit && (
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="kpi-is-active"
                  checked={editing.is_active !== false}
                  onChange={(e) => setEditing({ ...editing, is_active: e.target.checked })}
                  className="h-4 w-4 rounded border-lsc-border"
                />
                <label htmlFor="kpi-is-active" className="text-sm text-lsc-dark dark:text-lsc-cream">
                  Active
                </label>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2 mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl"
            >
              Cancel
            </button>
            <button
              onClick={onSave}
              disabled={!editing.name}
              className="px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose disabled:opacity-50"
            >
              Save KPI
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}
