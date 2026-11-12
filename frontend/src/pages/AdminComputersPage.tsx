/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { AdminShell } from '../components/shells/AdminShell'
import { Monitor, Plus, Loader2, X, Edit, Wifi, Printer as PrinterIcon, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../api/api'
import {
  getAdminComputers,
  createAdminComputer,
  updateAdminComputer,
  updateComputerStatus,
  deleteAdminComputer,
  type AdminComputer,
  type AdminComputerCreate,
  type AdminComputerUpdate,
} from '@/api/domains/admin/admin-computers-api'
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { StatusVariant } from '@/components/ui/StatusBadge'
import { useTranslation } from '@/i18n/I18nContext'
import AdminComputerMapArranger from '@/features/admin/AdminComputerMapArranger'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

type ComputerData = AdminComputer
interface Branch { id: number; name: string }

const TYPES = ['adult', 'teen', 'kids', 'accessible']
const STATUSES = ['available', 'in_use', 'maintenance', 'offline', 'reserved']

export default function AdminComputersPage(): React.ReactElement {
  const { t } = useTranslation()
  const [view, setView] = useState<'list' | 'map'>('list')
  const [computers, setComputers] = useState<ComputerData[]>([])
  const [branches, setBranches] = useState<Branch[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<ComputerData | null>(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    name: '', computer_number: '', computer_type: 'adult', location: '',
    os_type: 'Windows 11', branch_id: '', has_internet: true, has_print_release: true,
    max_session_minutes: 60, status: 'available',
  })

  const fetchData = useCallback(async () => {
    try {
      const [compRes, branchRes] = await Promise.all([
        getAdminComputers(),
        api.get<Branch[] | { items: Branch[] }>('/branches'),
      ])
      setComputers(compRes.items || [])
      setBranches(Array.isArray(branchRes) ? branchRes : (branchRes?.items || []))
    } catch (err) { console.error('Failed to load computer data:', err) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const resetForm = () => setForm({ name: '', computer_number: '', computer_type: 'adult', location: '', os_type: 'Windows 11', branch_id: '', has_internet: true, has_print_release: true, max_session_minutes: 60, status: 'available' })

  const openEdit = (comp: ComputerData) => {
    setEditing(comp)
    setForm({
      name: comp.name,
      computer_number: comp.computer_number,
      computer_type: comp.computer_type,
      location: comp.location ?? '',
      os_type: comp.os_type ?? 'Windows 11',
      branch_id: comp.branch_id != null ? String(comp.branch_id) : '',
      has_internet: comp.has_internet,
      has_print_release: comp.has_print_release,
      max_session_minutes: comp.max_session_minutes,
      status: comp.status,
    })
    setShowModal(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const branch_id = form.branch_id ? Number(form.branch_id) : null
      if (editing) {
        const payload: AdminComputerUpdate = {
          name: form.name,
          computer_number: form.computer_number,
          computer_type: form.computer_type,
          location: form.location,
          os_type: form.os_type,
          branch_id,
          has_internet: form.has_internet,
          has_print_release: form.has_print_release,
          max_session_minutes: Number(form.max_session_minutes),
          status: form.status,
        }
        await updateAdminComputer(editing.id, payload)
        toast.success('Computer updated')
      } else {
        const payload: AdminComputerCreate = {
          name: form.name,
          computer_number: form.computer_number,
          computer_type: form.computer_type,
          location: form.location,
          os_type: form.os_type,
          branch_id,
          has_internet: form.has_internet,
          has_print_release: form.has_print_release,
          max_session_minutes: Number(form.max_session_minutes),
        }
        await createAdminComputer(payload)
        toast.success('Computer added')
      }
      setShowModal(false); setEditing(null); resetForm(); fetchData()
    } catch { toast.error(editing ? 'Failed to update' : 'Failed to add computer') }
    finally { setSaving(false) }
  }

  const toggleStatus = async (comp: ComputerData, newStatus: string) => {
    try { await updateComputerStatus(comp.id, newStatus); toast.success(`Status: ${newStatus}`); fetchData() }
    catch { toast.error('Failed to update status') }
  }

  const handleDelete = async (comp: ComputerData) => {
    if (!confirm(`Remove "${comp.name}" from inventory? It will be marked inactive.`)) return
    try { await deleteAdminComputer(comp.id); toast.success('Computer removed'); fetchData() }
    catch { toast.error('Failed to remove computer') }
  }

  const statusVariant = (s: string): StatusVariant => ({ available: 'success', in_use: 'info', reserved: 'info', maintenance: 'warning', offline: 'danger' }[s] as StatusVariant || 'neutral')
  const typeLabel = (t: string) => ({ adult: 'Adult', teen: 'Teen', kids: "Children's", accessible: 'Accessible' }[t] || t)
  const inputCls = "w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
  const labelCls = "block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"

  return (
    <AdminShell title="Computer Management">
      <div>
        <div className="mb-4 inline-flex rounded border border-earth-200">
          <button
            type="button"
            onClick={() => setView('list')}
            className={`px-3 py-1 text-sm ${view === 'list' ? 'bg-sage-200' : ''}`}
          >
            {t('admin.computerMap.tabs.list')}
          </button>
          <button
            type="button"
            onClick={() => setView('map')}
            className={`px-3 py-1 text-sm ${view === 'map' ? 'bg-sage-200' : ''}`}
          >
            {t('admin.computerMap.tabs.arrange')}
          </button>
        </div>
        {view === 'list' && (<>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl"><Monitor className="w-6 h-6 text-lsc-rose" /></div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Computer Management</h1>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{computers.length} computers across {branches.length} branches</p>
            </div>
          </div>
          <button onClick={() => { resetForm(); setEditing(null); setShowModal(true) }} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm">
            <Plus className="w-4 h-4" /> Add Computer
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total', value: computers.length, color: 'text-lsc-dark dark:text-lsc-cream' },
            { label: 'Available', value: computers.filter(c => c.status === 'available').length, color: 'text-status-success-700 dark:text-status-success-400' },
            { label: 'In Use', value: computers.filter(c => c.status === 'in_use').length, color: 'text-status-info-700 dark:text-status-info-400' },
            { label: 'Out of service', value: computers.filter(c => ['maintenance', 'offline'].includes(c.status)).length, color: 'text-status-warning-700 dark:text-status-warning-400' },
          ].map(stat => (
            <div key={stat.label} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{stat.label}</p>
              <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
            </div>
          ))}
        </div>

        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" /></div>
        ) : computers.length === 0 ? (
          <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60"><Monitor className="w-12 h-12 mx-auto mb-3 opacity-50" /><p>No computers configured</p></div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {computers.map(comp => (
              <div key={comp.id} className={`bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 ${comp.is_active ? '' : 'opacity-60'}`}>
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                      {comp.name}
                      {!comp.is_active && <span className="ml-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">(inactive)</span>}
                    </h3>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">{comp.location || '—'}</p>
                    {comp.branch_name && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{comp.branch_name}</p>}
                  </div>
                  <div className="flex items-center gap-1">
                    <StatusBadge variant={statusVariant(comp.status)}>{comp.status.replace('_', ' ')}</StatusBadge>
                    <button onClick={() => openEdit(comp)} title="Edit" className="p-1 text-lsc-dark/70 hover:text-lsc-rose dark:text-lsc-cream/40"><Edit className="w-3.5 h-3.5" /></button>
                    {comp.is_active && <button onClick={() => handleDelete(comp)} title="Remove" className="p-1 text-lsc-dark/70 hover:text-status-danger-600 dark:text-lsc-cream/40"><Trash2 className="w-3.5 h-3.5" /></button>}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 mb-3">
                  <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs text-lsc-dark dark:text-lsc-cream">{typeLabel(comp.computer_type)}</span>
                  {comp.os_type && <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs text-lsc-dark dark:text-lsc-cream">{comp.os_type}</span>}
                  <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs text-lsc-dark dark:text-lsc-cream">#{comp.computer_number}</span>
                  {comp.has_internet && <span className="flex items-center gap-1 px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs"><Wifi className="w-3 h-3" />Net</span>}
                  {comp.has_print_release && <span className="flex items-center gap-1 px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs"><PrinterIcon className="w-3 h-3" />Print</span>}
                  <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs text-lsc-dark dark:text-lsc-cream">{comp.max_session_minutes}m</span>
                </div>
                <div className="flex gap-1 flex-wrap">
                  {comp.status !== 'available' && <button onClick={() => toggleStatus(comp, 'available')} className="text-xs px-2 py-1 rounded bg-status-success-100 text-status-success-800 hover:bg-status-success-200 dark:bg-status-success-900/30 dark:text-status-success-400">Available</button>}
                  {comp.status !== 'maintenance' && <button onClick={() => toggleStatus(comp, 'maintenance')} className="text-xs px-2 py-1 rounded bg-status-warning-100 text-status-warning-800 hover:bg-status-warning-200 dark:bg-status-warning-900/30 dark:text-status-warning-400">Maintenance</button>}
                  {comp.status !== 'offline' && <button onClick={() => toggleStatus(comp, 'offline')} className="text-xs px-2 py-1 rounded bg-earth-100 text-earth-800 hover:bg-earth-200 dark:bg-earth-900/30 dark:text-earth-400">Offline</button>}
                </div>
              </div>
            ))}
          </div>
        )}

        {showModal && (
          <ModalBackdrop onClose={() => { setShowModal(false); setEditing(null) }} labelledBy="admin-computers-modal-title">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-lg w-full max-h-[90vh] overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 id="admin-computers-modal-title" className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{editing ? 'Edit Computer' : 'Add Computer'}</h3>
                <button onClick={() => { setShowModal(false); setEditing(null) }}><X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" /></button>
              </div>
              <form onSubmit={handleSubmit} className="p-4 space-y-4 overflow-y-auto max-h-[70vh]">
                <div className="grid grid-cols-2 gap-4">
                  <div><label className={labelCls}>Name *</label><input type="text" required value={form.name} onChange={e => setForm({...form, name: e.target.value})} className={inputCls} placeholder="PC-A01" /></div>
                  <div><label className={labelCls}>Number</label><input type="text" value={form.computer_number} onChange={e => setForm({...form, computer_number: e.target.value})} className={inputCls} placeholder="A01" /></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className={labelCls}>Type *</label><select required value={form.computer_type} onChange={e => setForm({...form, computer_type: e.target.value})} className={inputCls}>{TYPES.map(ty => <option key={ty} value={ty}>{typeLabel(ty)}</option>)}</select></div>
                  <div><label className={labelCls}>Status</label><select value={form.status} onChange={e => setForm({...form, status: e.target.value})} className={inputCls}>{STATUSES.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}</select></div>
                </div>
                <div><label className={labelCls}>Location *</label><input type="text" required value={form.location} onChange={e => setForm({...form, location: e.target.value})} className={inputCls} placeholder="Adult Services - Main Floor" /></div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className={labelCls}>OS</label><input type="text" value={form.os_type} onChange={e => setForm({...form, os_type: e.target.value})} className={inputCls} /></div>
                  <div><label className={labelCls}>Branch *</label><select required value={form.branch_id} onChange={e => setForm({...form, branch_id: e.target.value})} className={inputCls}><option value="">Select...</option>{branches.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div>
                </div>
                <div><label className={labelCls}>Max Session (min)</label><input type="number" min="15" max="480" value={form.max_session_minutes} onChange={e => setForm({...form, max_session_minutes: Number(e.target.value)})} className={inputCls} /></div>
                <div className="flex gap-6">
                  <label className="flex items-center gap-2"><input type="checkbox" checked={form.has_internet} onChange={e => setForm({...form, has_internet: e.target.checked})} className="rounded" /><span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Internet</span></label>
                  <label className="flex items-center gap-2"><input type="checkbox" checked={form.has_print_release} onChange={e => setForm({...form, has_print_release: e.target.checked})} className="rounded" /><span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Print release</span></label>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button type="button" onClick={() => { setShowModal(false); setEditing(null) }} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70">Cancel</button>
                  <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50">{saving ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : editing ? 'Update' : 'Add'}</button>
                </div>
              </form>
            </div>
          </ModalBackdrop>
        )}
        </>)}
        {view === 'map' && <AdminComputerMapArranger />}
      </div>
    </AdminShell>
  )
}
