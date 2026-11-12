/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import toast from 'react-hot-toast'
import {
  BookOpen, Save, Plus, Trash2, Info, Layers, Shield, X,
} from 'lucide-react'
import { useConfigurationSection } from '@/hooks/useConfigurationSection'
import { SectionShell } from '../ai-settings/SectionShell'

const safeInt = (val: string, fallback: number) => { const n = parseInt(val); return isNaN(n) ? fallback : n }

const PATRON_TYPES = ['Adult', 'Juvenile', 'Teen', 'Senior'] as const

const MATRIX_MATERIAL_TYPES = [
  'Books', 'DVDs', 'Audiobooks', 'Magazines', 'eBooks', 'Equipment', 'Hotspots', 'Museum Passes',
] as const

const ALL_MATERIAL_TYPES = [
  'Books', 'DVDs', 'Audiobooks', 'Magazines', 'Newspapers', 'eBooks', 'Equipment',
  'Hotspots', 'Museum Passes', 'Seeds', '3D Prints',
] as const

interface DefaultRules {
  loanPeriodDays: number
  renewalLimit: number
  holdLimit: number
  overdueFinePerDay: string
  maxFine: string
}

interface CellRule {
  loanDays: number
  renewalLimit: number
}

interface SpecialRule {
  id: number
  description: string
  active: boolean
}

interface MaterialTypeConfig {
  name: string
  defaultLoanPeriod: number
  maxRenewals: number
  holdable: boolean
  renewable: boolean
}

type EditingCell = { material: string; patron: string } | null

interface CirculationRulesConfig extends Record<string, unknown> {
  defaults: DefaultRules
  matrix: Record<string, Record<string, CellRule>>
  special_rules: SpecialRule[]
  material_types: MaterialTypeConfig[]
}

function buildInitialMatrix(): Record<string, Record<string, CellRule>> {
  const matrix: Record<string, Record<string, CellRule>> = {}
  for (const mat of MATRIX_MATERIAL_TYPES) {
    matrix[mat] = {}
    for (const pat of PATRON_TYPES) {
      let loanDays = 21
      let renewalLimit = 2
      if (mat === 'DVDs' || mat === 'Hotspots') { loanDays = 7; renewalLimit = 1 }
      if (mat === 'Museum Passes') { loanDays = 7; renewalLimit = 0 }
      if (mat === 'Equipment') { loanDays = 14; renewalLimit = 1 }
      if (pat === 'Juvenile') { renewalLimit = Math.max(renewalLimit - 1, 0) }
      if (pat === 'Senior') { loanDays += 7 }
      matrix[mat]![pat] = { loanDays, renewalLimit }
    }
  }
  return matrix
}

const DEFAULT_CONFIG: CirculationRulesConfig = {
  defaults: { loanPeriodDays: 21, renewalLimit: 2, holdLimit: 5, overdueFinePerDay: '0.25', maxFine: '10.00' },
  matrix: buildInitialMatrix(),
  special_rules: [
    { id: 1, description: 'Holiday extension: +7 days during Dec 15-Jan 5', active: true },
    { id: 2, description: 'Summer reading: unlimited renewals for juvenile patrons June-August', active: true },
    { id: 3, description: 'New materials: no holds for first 14 days', active: false },
  ],
  material_types: ALL_MATERIAL_TYPES.map((name) => ({
    name, defaultLoanPeriod: 21, maxRenewals: 2, holdable: true, renewable: true,
  })),
}

const TABS = [
  { id: 'defaults', label: 'Default Rules', icon: BookOpen },
  { id: 'matrix', label: 'Patron/Material Matrix', icon: Layers },
  { id: 'special', label: 'Special Rules', icon: Shield },
  { id: 'materials', label: 'Material Types', icon: Info },
] as const

interface CirculationRulesSectionProps {
  onBack: () => void
}

export function CirculationRulesSection({ onBack }: CirculationRulesSectionProps) {
  const { value: config, setField, loading, saving, save } =
    useConfigurationSection<CirculationRulesConfig>('circulation_rules', DEFAULT_CONFIG, {
      successMessage: 'Circulation rules saved',
      errorMessage: 'Failed to save circulation rules',
      defaultReason: 'Admin update via circulation rules UI',
    })

  const [editingCell, setEditingCell] = useState<EditingCell>(null)
  const [editValues, setEditValues] = useState({ loanDays: 0, renewalLimit: 0 })
  const [newRuleDesc, setNewRuleDesc] = useState('')

  const handleCellClick = (material: string, patron: string) => {
    const cell = config.matrix[material]?.[patron]
    if (cell) {
      setEditingCell({ material, patron })
      setEditValues({ loanDays: cell.loanDays, renewalLimit: cell.renewalLimit })
    }
  }

  const handleCellSave = () => {
    if (!editingCell) return
    const newMatrix = { ...config.matrix }
    newMatrix[editingCell.material] = {
      ...newMatrix[editingCell.material],
      [editingCell.patron]: { ...editValues },
    }
    setField('matrix', newMatrix)
    setEditingCell(null)
    toast.success('Cell updated')
  }

  const handleAddRule = () => {
    if (!newRuleDesc.trim()) return
    const newRules = [
      ...config.special_rules,
      { id: Date.now(), description: newRuleDesc.trim(), active: true },
    ]
    setField('special_rules', newRules)
    setNewRuleDesc('')
    toast.success('Rule added')
  }

  const toggleRule = (id: number) => {
    setField('special_rules', config.special_rules.map((r) =>
      r.id === id ? { ...r, active: !r.active } : r
    ))
  }

  const deleteRule = (id: number) => {
    setField('special_rules', config.special_rules.filter((r) => r.id !== id))
    toast.success('Rule removed')
  }

  if (loading) return null

  return (
    <SectionShell
      title="Circulation Rules"
      description="How long patrons can borrow each type of material, and how many times they can renew. The matrix that controls it all."
      tabs={[...TABS]}
      defaultTab="defaults"
      backLabel="Back to Circulation & Policy"
      onBack={onBack}
    >
      {(activeTab) => (
        <>
          {activeTab === 'defaults' && (
            <div className="space-y-6">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Default Circulation Rules</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Loan Period (days)</label>
                    <input type="number" min="1" max="365" value={config.defaults.loanPeriodDays}
                      onChange={(e) => setField('defaults', { ...config.defaults, loanPeriodDays: safeInt(e.target.value, 21) })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Renewal Limit</label>
                    <input type="number" min="0" max="10" value={config.defaults.renewalLimit}
                      onChange={(e) => setField('defaults', { ...config.defaults, renewalLimit: safeInt(e.target.value, 2) })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Hold Limit</label>
                    <input type="number" min="0" max="50" value={config.defaults.holdLimit}
                      onChange={(e) => setField('defaults', { ...config.defaults, holdLimit: safeInt(e.target.value, 5) })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Overdue Fine Per Day ($)</label>
                    <input type="number" min="0" max="10" step="0.01" value={config.defaults.overdueFinePerDay}
                      onChange={(e) => setField('defaults', { ...config.defaults, overdueFinePerDay: e.target.value })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Maximum Fine ($)</label>
                    <input type="number" min="0" max="1000" step="0.01" value={config.defaults.maxFine}
                      onChange={(e) => setField('defaults', { ...config.defaults, maxFine: e.target.value })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                  </div>
                </div>
              </div>
              <button onClick={() => save()} disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 font-semibold">
                <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}

          {activeTab === 'matrix' && (
            <div className="space-y-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr>
                      <th className="text-left py-2 px-3 bg-lsc-cream dark:bg-earth-700 rounded-tl-lg font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Material</th>
                      {PATRON_TYPES.map((p) => (
                        <th key={p} className="text-center py-2 px-3 bg-lsc-cream dark:bg-earth-700 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{p}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {MATRIX_MATERIAL_TYPES.map((mat) => (
                      <tr key={mat} className="border-b border-lsc-border dark:border-earth-700">
                        <td className="py-2 px-3 font-medium text-lsc-dark dark:text-lsc-cream">{mat}</td>
                        {PATRON_TYPES.map((pat) => {
                          const cell = config.matrix[mat]?.[pat]
                          const isEditing = editingCell?.material === mat && editingCell?.patron === pat
                          return (
                            <td key={pat} className="py-2 px-3 text-center">
                              {isEditing ? (
                                <div className="flex items-center gap-1 justify-center">
                                  <input type="number" min="1" max="365" value={editValues.loanDays}
                                    onChange={(e) => setEditValues({ ...editValues, loanDays: safeInt(e.target.value, 1) })}
                                    className="w-12 px-1 py-0.5 border rounded text-xs bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                                  <input type="number" min="0" max="10" value={editValues.renewalLimit}
                                    onChange={(e) => setEditValues({ ...editValues, renewalLimit: safeInt(e.target.value, 0) })}
                                    className="w-12 px-1 py-0.5 border rounded text-xs bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream" />
                                  <button onClick={handleCellSave} className="text-status-success-600 hover:text-status-success-700" aria-label="Save cell"><Save className="w-3 h-3" /></button>
                                  <button onClick={() => setEditingCell(null)} className="text-earth-600 hover:text-earth-700" aria-label="Cancel"><X className="w-3 h-3" /></button>
                                </div>
                              ) : (
                                <button onClick={() => handleCellClick(mat, pat)}
                                  className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose cursor-pointer"
                                  aria-label={`Edit ${mat} for ${pat}: ${cell?.loanDays ?? 0}d / ${cell?.renewalLimit ?? 0}r`}>
                                  {cell?.loanDays ?? 0}d / {cell?.renewalLimit ?? 0}r
                                </button>
                              )}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button onClick={() => save()} disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 font-semibold">
                <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}

          {activeTab === 'special' && (
            <div className="space-y-4">
              <div className="space-y-3">
                {config.special_rules.map((rule) => (
                  <div key={rule.id} className="flex items-center gap-3 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-3">
                    <button type="button" role="switch" aria-checked={rule.active} onClick={() => toggleRule(rule.id)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${rule.active ? 'bg-lsc-rose' : 'bg-earth-200 dark:bg-earth-700'}`}>
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-lsc-white transition-transform ${rule.active ? 'translate-x-6' : 'translate-x-1'}`} />
                    </button>
                    <span className="flex-1 text-sm text-lsc-dark dark:text-lsc-cream">{rule.description}</span>
                    <button onClick={() => deleteRule(rule.id)} className="text-status-danger-500 hover:text-status-danger-700 p-1" aria-label={`Delete rule: ${rule.description}`}>
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <input type="text" value={newRuleDesc} onChange={(e) => setNewRuleDesc(e.target.value)}
                  placeholder="Describe a new special rule..."
                  className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm" />
                <button onClick={handleAddRule} disabled={!newRuleDesc.trim()}
                  className="flex items-center gap-1 px-3 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 text-sm font-medium">
                  <Plus className="w-4 h-4" /> Add
                </button>
              </div>
              <button onClick={() => save()} disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 font-semibold">
                <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}

          {activeTab === 'materials' && (
            <div className="space-y-4">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-lsc-border dark:border-earth-700">
                      <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Type</th>
                      <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Loan Period</th>
                      <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Max Renewals</th>
                      <th className="text-center py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Holdable</th>
                      <th className="text-center py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Renewable</th>
                    </tr>
                  </thead>
                  <tbody>
                    {config.material_types.map((mt, idx) => (
                      <tr key={mt.name} className="border-b border-earth-100 dark:border-earth-700">
                        <td className="py-2 px-3 text-lsc-dark dark:text-lsc-cream font-medium">{mt.name}</td>
                        <td className="py-2 px-3">
                          <input type="number" min="1" max="365" value={mt.defaultLoanPeriod}
                            onChange={(e) => {
                              const updated = [...config.material_types]
                              updated[idx] = { ...mt, defaultLoanPeriod: safeInt(e.target.value, 21) }
                              setField('material_types', updated)
                            }}
                            className="w-20 px-2 py-1 border border-lsc-border dark:border-earth-700 rounded bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm" />
                        </td>
                        <td className="py-2 px-3">
                          <input type="number" min="0" max="10" value={mt.maxRenewals}
                            onChange={(e) => {
                              const updated = [...config.material_types]
                              updated[idx] = { ...mt, maxRenewals: safeInt(e.target.value, 0) }
                              setField('material_types', updated)
                            }}
                            className="w-20 px-2 py-1 border border-lsc-border dark:border-earth-700 rounded bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm" />
                        </td>
                        <td className="py-2 px-3 text-center">
                          <input type="checkbox" checked={mt.holdable}
                            onChange={() => {
                              const updated = [...config.material_types]
                              updated[idx] = { ...mt, holdable: !mt.holdable }
                              setField('material_types', updated)
                            }}
                            className="rounded border-lsc-border" />
                        </td>
                        <td className="py-2 px-3 text-center">
                          <input type="checkbox" checked={mt.renewable}
                            onChange={() => {
                              const updated = [...config.material_types]
                              updated[idx] = { ...mt, renewable: !mt.renewable }
                              setField('material_types', updated)
                            }}
                            className="rounded border-lsc-border" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button onClick={() => save()} disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 font-semibold">
                <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}
        </>
      )}
    </SectionShell>
  )
}
