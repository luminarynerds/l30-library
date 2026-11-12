/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import * as Sentry from '@/lib/sentry-lazy'
import toast from 'react-hot-toast'
import { Loader2, Plus, Pencil, Trash2, Eye, BookOpen } from 'lucide-react'
import api from '@/api/api'
import { API_BASE } from '@/api/types'
import { SectionShell } from '../ai-settings/SectionShell'
import { EditCirculationPolicyModal } from './EditCirculationPolicyModal'
import {
  BOOK_BINDINGS,
  CIRCULATION_POLICY_ITEM_TYPES,
  CIRCULATION_POLICY_ROLES,
  bindingLabel,
  createCirculationPolicy,
  deleteCirculationPolicy,
  describeScope,
  itemTypeLabel,
  listCirculationPolicies,
  previewCirculationPolicy,
  roleLabel,
  updateCirculationPolicy,
  type BookBinding,
  type CirculationPolicyCreate,
  type CirculationPolicyResponse,
  type CirculationPolicyRole,
  type CirculationPolicyUpdate,
  type ResolvedPolicyResponse,
} from '@/api/domains/admin/circulation-policy-api'
import type { ItemType } from '@/api/domains/catalog/catalog-api'

interface LibrarySystem {
  id: number
  code: string
  name: string
}

const TABS = [{ id: 'matrix', label: 'Policy matrix', icon: BookOpen }] as const

interface CirculationPolicySectionProps {
  onBack: () => void
}

function fmtMoney(v: string | null): string {
  if (v === null) return '(inherits)'
  const n = parseFloat(v)
  if (Number.isNaN(n)) return v
  return `$${n.toFixed(2)}`
}

function fmtNum(v: number | null, suffix = ''): string {
  if (v === null) return '(inherits)'
  return `${v}${suffix}`
}

function fmtFineFree(v: boolean | null): string {
  if (v === null) return '(inherits)'
  return v ? 'Yes' : 'No'
}

const inheritsCls = 'text-lsc-dark/40 dark:text-lsc-cream/40 italic'

interface InheritCellProps {
  set: boolean
  display: string
  tooltip?: string
}

function Cell({ set, display, tooltip }: InheritCellProps) {
  return (
    <span
      className={set ? '' : inheritsCls}
      title={tooltip || (set ? undefined : 'No override here. Falls back to next-broader policy.')}
    >
      {display}
    </span>
  )
}

export function CirculationPolicySection({ onBack }: CirculationPolicySectionProps) {
  const [systems, setSystems] = useState<LibrarySystem[]>([])
  const [selectedSystemId, setSelectedSystemId] = useState<number | null>(null)
  const [policies, setPolicies] = useState<CirculationPolicyResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [modalOpen, setModalOpen] = useState(false)
  const [editingPolicy, setEditingPolicy] = useState<CirculationPolicyResponse | null>(null)

  // Preview state
  const [previewRole, setPreviewRole] = useState<CirculationPolicyRole | ''>('')
  const [previewItemType, setPreviewItemType] = useState<ItemType | ''>('')
  const [previewBinding, setPreviewBinding] = useState<BookBinding | ''>('')
  const [previewCollectionId, setPreviewCollectionId] = useState('')
  const [previewResult, setPreviewResult] = useState<ResolvedPolicyResponse | null>(null)
  const [previewing, setPreviewing] = useState(false)

  // Load library systems on mount
  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const data = await api.get<LibrarySystem[]>(`${API_BASE}/branches/systems`)
        if (cancelled) return
        setSystems(data)
        if (data.length > 0) setSelectedSystemId(data[0]!.id)
      } catch (error: unknown) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
        toast.error('Failed to load library systems.')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const loadPolicies = useCallback(async (systemId: number) => {
    setLoading(true)
    try {
      const data = await listCirculationPolicies({ library_system_id: systemId })
      setPolicies(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error('Failed to load circulation policies.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (selectedSystemId !== null) void loadPolicies(selectedSystemId)
  }, [selectedSystemId, loadPolicies])

  const handleAdd = () => {
    setEditingPolicy(null)
    setModalOpen(true)
  }

  const handleEdit = (p: CirculationPolicyResponse) => {
    setEditingPolicy(p)
    setModalOpen(true)
  }

  const handleDelete = async (p: CirculationPolicyResponse) => {
    // No app-wide ConfirmDialog primitive; window.confirm is the existing pattern.
    if (!window.confirm(`Delete this circulation policy? This cannot be undone.`)) return
    try {
      await deleteCirculationPolicy(p.id)
      toast.success('Policy deleted.')
      if (selectedSystemId !== null) await loadPolicies(selectedSystemId)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error('Failed to delete policy.')
    }
  }

  const handleToggleActive = async (p: CirculationPolicyResponse) => {
    try {
      await updateCirculationPolicy(p.id, { active: !p.active })
      if (selectedSystemId !== null) await loadPolicies(selectedSystemId)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error('Failed to update policy.')
    }
  }

  const handleSave = async (
    mode: 'create' | 'update',
    payload: CirculationPolicyCreate | CirculationPolicyUpdate,
  ) => {
    setSaving(true)
    try {
      if (mode === 'create') {
        await createCirculationPolicy(payload as CirculationPolicyCreate)
        toast.success('Policy created.')
      } else if (editingPolicy) {
        await updateCirculationPolicy(editingPolicy.id, payload as CirculationPolicyUpdate)
        toast.success('Policy updated.')
      }
      setModalOpen(false)
      setEditingPolicy(null)
      if (selectedSystemId !== null) await loadPolicies(selectedSystemId)
    } catch (error: unknown) {
      const err = error as { detail?: string; message?: string }
      const msg = err.detail || err.message || 'Save failed.'
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      throw new Error(msg)
    } finally {
      setSaving(false)
    }
  }

  const runPreview = async () => {
    if (selectedSystemId === null) return
    setPreviewing(true)
    try {
      const params: Parameters<typeof previewCirculationPolicy>[0] = {
        library_system_id: selectedSystemId,
      }
      if (previewRole !== '') params.role = previewRole
      if (previewItemType !== '') params.item_type = previewItemType
      if (previewBinding !== '') params.binding = previewBinding
      if (previewCollectionId.trim() !== '') {
        const n = parseInt(previewCollectionId, 10)
        if (!Number.isNaN(n)) params.collection_id = n
      }
      const result = await previewCirculationPolicy(params)
      setPreviewResult(result)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error('Failed to resolve preview.')
    } finally {
      setPreviewing(false)
    }
  }

  const sortedPolicies = useMemo(() => {
    // Most-specific first: count non-null scope axes desc.
    return [...policies].sort((a, b) => {
      const sa = (a.role ? 1 : 0) + (a.item_type ? 1 : 0) + (a.binding ? 1 : 0) + (a.collection_id !== null ? 1 : 0)
      const sb = (b.role ? 1 : 0) + (b.item_type ? 1 : 0) + (b.binding ? 1 : 0) + (b.collection_id !== null ? 1 : 0)
      if (sb !== sa) return sb - sa
      return a.id - b.id
    })
  }, [policies])

  const inputCls =
    'px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50'

  return (
    <SectionShell
      title="Circulation Policy Matrix"
      description="Per-format, per-audience, per-binding, and per-collection circulation overrides. Empty fields inherit from broader policies, then from Site Settings defaults."
      tabs={[...TABS]}
      defaultTab="matrix"
      backLabel="Back to Library Configuration"
      onBack={onBack}
    >
      {() => (
        <div className="space-y-6">
          {systems.length > 1 && (
            <div className="flex items-center gap-3">
              <label htmlFor="cp-system" className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Library System:</label>
              <select
                id="cp-system"
                value={selectedSystemId ?? ''}
                onChange={(e) => setSelectedSystemId(parseInt(e.target.value, 10))}
                className={inputCls}
              >
                {systems.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          )}

          {/* Preview panel */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 space-y-4">
            <div className="flex items-center gap-2">
              <Eye className="w-5 h-5 text-status-warning-600" aria-hidden="true" />
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Resolve a sample policy</h3>
            </div>
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 -mt-2">
              Pick a patron role + item type to see which knobs apply and where each value came from.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
              <div>
                <label htmlFor="prev-role" className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Role</label>
                <select id="prev-role" className={`w-full ${inputCls}`} value={previewRole} onChange={(e) => setPreviewRole(e.target.value as CirculationPolicyRole | '')}>
                  <option value="">— Any —</option>
                  {CIRCULATION_POLICY_ROLES.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="prev-item-type" className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Item type</label>
                <select id="prev-item-type" className={`w-full ${inputCls}`} value={previewItemType} onChange={(e) => setPreviewItemType(e.target.value as ItemType | '')}>
                  <option value="">— Any —</option>
                  {CIRCULATION_POLICY_ITEM_TYPES.map((t) => <option key={t} value={t}>{itemTypeLabel(t)}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="prev-binding" className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Binding</label>
                <select id="prev-binding" className={`w-full ${inputCls}`} value={previewBinding} onChange={(e) => setPreviewBinding(e.target.value as BookBinding | '')} disabled={previewItemType !== '' && previewItemType !== 'book'}>
                  <option value="">— Any —</option>
                  {BOOK_BINDINGS.map((b) => <option key={b} value={b}>{bindingLabel(b)}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="prev-collection" className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Collection ID</label>
                <input id="prev-collection" type="number" min="1" className={`w-full ${inputCls}`} value={previewCollectionId} onChange={(e) => setPreviewCollectionId(e.target.value)} placeholder="optional" />
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  onClick={runPreview}
                  disabled={previewing || selectedSystemId === null}
                  className="w-full px-4 py-2 text-sm font-semibold text-white bg-lsc-rose rounded-lg hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 disabled:opacity-50"
                >
                  {previewing ? 'Resolving...' : 'Resolve'}
                </button>
              </div>
            </div>
            {previewResult && (
              <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
                <h4 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Resolved values</h4>
                <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                  <ProvenanceRow label="Loan period" value={`${previewResult.loan_period_days} days`} prov={previewResult.provenance.loan_period_days} />
                  <ProvenanceRow label="Max renewals" value={String(previewResult.max_renewals)} prov={previewResult.provenance.max_renewals} />
                  <ProvenanceRow label="Overdue fine / day" value={`$${parseFloat(previewResult.overdue_fine_per_day).toFixed(2)}`} prov={previewResult.provenance.overdue_fine_per_day} />
                  <ProvenanceRow label="Max fine" value={`$${parseFloat(previewResult.max_fine).toFixed(2)}`} prov={previewResult.provenance.max_fine} />
                  <ProvenanceRow label="Grace days" value={`${previewResult.grace_period_days}`} prov={previewResult.provenance.grace_period_days} />
                  <ProvenanceRow label="Hold pickup days" value={`${previewResult.hold_pickup_days}`} prov={previewResult.provenance.hold_pickup_days} />
                  <ProvenanceRow label="Fine-free" value={previewResult.fine_free ? 'Yes' : 'No'} prov={previewResult.provenance.fine_free} />
                </dl>
              </div>
            )}
          </div>

          {/* Add button */}
          <div className="flex justify-between items-center">
            <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {loading ? 'Loading...' : `${policies.length} polic${policies.length === 1 ? 'y' : 'ies'}`}
            </div>
            <button
              type="button"
              onClick={handleAdd}
              disabled={selectedSystemId === null}
              className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-lsc-rose rounded-lg hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 disabled:opacity-50"
            >
              <Plus className="w-4 h-4" aria-hidden="true" />
              Add policy
            </button>
          </div>

          {/* Table */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-x-auto">
            {loading ? (
              <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 motion-safe:animate-spin text-lsc-rose" aria-label="Loading" /></div>
            ) : sortedPolicies.length === 0 ? (
              <div className="py-12 text-center text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
                No circulation policies yet. Use "Add policy" to create one. Until then, Site Settings defaults apply to everything.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                <thead className="border-b border-lsc-border dark:border-earth-700">
                  <tr className="text-left text-xs uppercase text-lsc-dark/60 dark:text-lsc-cream/60">
                    <th scope="col" className="px-4 py-3">Scope</th>
                    <th scope="col" className="px-4 py-3">Loan</th>
                    <th scope="col" className="px-4 py-3">Renewals</th>
                    <th scope="col" className="px-4 py-3">Fine/day</th>
                    <th scope="col" className="px-4 py-3">Max fine</th>
                    <th scope="col" className="px-4 py-3">Grace</th>
                    <th scope="col" className="px-4 py-3">Hold pickup</th>
                    <th scope="col" className="px-4 py-3">Fine-free</th>
                    <th scope="col" className="px-4 py-3">Active</th>
                    <th scope="col" className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedPolicies.map((p) => {
                    const scope = describeScope(p)
                    return (
                      <tr key={p.id} className="border-b border-lsc-border/50 dark:border-earth-700/50 last:border-b-0 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-x-2 gap-y-1 text-xs">
                            <span><span className="text-lsc-dark/50 dark:text-lsc-cream/50">role</span> {scope.role}</span>
                            <span><span className="text-lsc-dark/50 dark:text-lsc-cream/50">type</span> {scope.itemType}</span>
                            <span><span className="text-lsc-dark/50 dark:text-lsc-cream/50">binding</span> {scope.binding}</span>
                            <span><span className="text-lsc-dark/50 dark:text-lsc-cream/50">coll</span> {scope.collection}</span>
                          </div>
                          {p.notes && <div className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mt-1 italic">{p.notes}</div>}
                        </td>
                        <td className="px-4 py-3"><Cell set={p.loan_period_days !== null} display={fmtNum(p.loan_period_days, 'd')} /></td>
                        <td className="px-4 py-3"><Cell set={p.max_renewals !== null} display={fmtNum(p.max_renewals)} /></td>
                        <td className="px-4 py-3"><Cell set={p.overdue_fine_per_day !== null} display={fmtMoney(p.overdue_fine_per_day)} /></td>
                        <td className="px-4 py-3"><Cell set={p.max_fine !== null} display={fmtMoney(p.max_fine)} /></td>
                        <td className="px-4 py-3"><Cell set={p.grace_period_days !== null} display={fmtNum(p.grace_period_days, 'd')} /></td>
                        <td className="px-4 py-3"><Cell set={p.hold_pickup_days !== null} display={fmtNum(p.hold_pickup_days, 'd')} /></td>
                        <td className="px-4 py-3"><Cell set={p.fine_free !== null} display={fmtFineFree(p.fine_free)} /></td>
                        <td className="px-4 py-3">
                          <button
                            type="button"
                            role="switch"
                            aria-checked={p.active}
                            aria-label={`Toggle policy ${p.id} active`}
                            onClick={() => void handleToggleActive(p)}
                            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 ${p.active ? 'bg-lsc-rose' : 'bg-earth-200 dark:bg-earth-700'}`}
                          >
                            <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-lsc-white dark:bg-earth-800 transition-transform ${p.active ? 'translate-x-5' : 'translate-x-0.5'}`} />
                          </button>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="inline-flex gap-1">
                            <button
                              type="button"
                              onClick={() => handleEdit(p)}
                              aria-label={`Edit policy ${p.id}`}
                              className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-1.5 rounded-lg text-lsc-dark/60 dark:text-lsc-cream/60 hover:text-lsc-rose hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
                            >
                              <Pencil className="w-4 h-4" aria-hidden="true" />
                            </button>
                            <button
                              type="button"
                              onClick={() => void handleDelete(p)}
                              aria-label={`Delete policy ${p.id}`}
                              className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-1.5 rounded-lg text-lsc-dark/60 dark:text-lsc-cream/60 hover:text-status-warning-600 hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
                            >
                              <Trash2 className="w-4 h-4" aria-hidden="true" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
                </table>
              </div>
            )}
          </div>

          {selectedSystemId !== null && (
            <EditCirculationPolicyModal
              isOpen={modalOpen}
              librarySystemId={selectedSystemId}
              initial={editingPolicy}
              saving={saving}
              onClose={() => { setModalOpen(false); setEditingPolicy(null) }}
              onSave={handleSave}
            />
          )}
        </div>
      )}
    </SectionShell>
  )
}

interface ProvenanceRowProps {
  label: string
  value: string
  prov: { scope: string; policy_id: number | null }
}

function ProvenanceRow({ label, value, prov }: ProvenanceRowProps) {
  return (
    <div className="flex flex-col">
      <dt className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">{label}</dt>
      <dd className="text-lsc-dark dark:text-lsc-cream">
        <span className="font-medium">{value}</span>{' '}
        <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">(from {prov.scope})</span>
      </dd>
    </div>
  )
}

export default CirculationPolicySection
