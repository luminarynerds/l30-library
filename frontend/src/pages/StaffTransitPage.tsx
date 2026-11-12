/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { AdminShell } from '../components/shells/AdminShell'
import { Truck, Plus, Loader2, X, Package, ArrowRight, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../api/api'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { t } from '@/i18n'

interface Branch { id: number; name: string }
interface TransitRequest {
  id: number; item_copy_id: number; from_branch_id: number; to_branch_id: number
  reason: string; priority: string; status: string; requested_at: string
  from_branch_name?: string; to_branch_name?: string
}
interface TransitShipment {
  id: number; shipment_number: string; from_branch_id: number; to_branch_id: number
  item_count: number; container_count: number; shipped_at: string | null; received_at: string | null; notes: string | null
}

type TabId = 'requests' | 'shipments'
const REASONS = ['hold_fulfillment', 'rebalancing', 'return_to_home', 'collection_transfer', 'repair', 'special_request']
const PRIORITIES = ['low', 'normal', 'high', 'urgent']

export default function StaffTransitPage(): React.ReactElement {
  const [tab, setTab] = useState<TabId>('requests')
  const [requests, setRequests] = useState<TransitRequest[]>([])
  const [shipments, setShipments] = useState<TransitShipment[]>([])
  const [branches, setBranches] = useState<Branch[]>([])
  const [loading, setLoading] = useState(true)
  const [showNewRequest, setShowNewRequest] = useState(false)
  const [showNewShipment, setShowNewShipment] = useState(false)
  const [saving, setSaving] = useState(false)
  const [reqForm, setReqForm] = useState({ item_copy_id: '', from_branch_id: '', to_branch_id: '', reason: 'hold_fulfillment', priority: 'normal' })
  const [shipForm, setShipForm] = useState({ from_branch_id: '', to_branch_id: '', notes: '' })

  const fetchData = useCallback(async () => {
    try {
      const [reqRes, shipRes, branchRes] = await Promise.all([
        api.get('/branches/transit/requests'),
        api.get('/branches/transit/shipments'),
        api.get('/branches'),
      ])
      setRequests(reqRes.data?.items || reqRes.data || [])
      setShipments(shipRes.data?.items || shipRes.data || [])
      setBranches(branchRes.data?.items || branchRes.data || [])
    } catch { /* data may not be available */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleAction = async (id: number, action: string) => {
    try {
      await api.post(`/branches/transit/requests/${id}/${action}`)
      toast.success(`Request ${action}d`)
      fetchData()
    } catch { toast.error(`Failed to ${action}`) }
  }

  const handleShipAction = async (id: number, action: string) => {
    try {
      await api.post(`/branches/transit/shipments/${id}/${action}`)
      toast.success(`Shipment ${action === 'ship' ? 'shipped' : 'received'}`)
      fetchData()
    } catch { toast.error('Action failed') }
  }

  const submitRequest = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/branches/transit/requests', { item_copy_id: Number(reqForm.item_copy_id), from_branch_id: Number(reqForm.from_branch_id), to_branch_id: Number(reqForm.to_branch_id), reason: reqForm.reason, priority: reqForm.priority })
      toast.success('Transit request created')
      setShowNewRequest(false)
      fetchData()
    } catch { toast.error('Failed to create request') }
    finally { setSaving(false) }
  }

  const submitShipment = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/branches/transit/shipments', { from_branch_id: Number(shipForm.from_branch_id), to_branch_id: Number(shipForm.to_branch_id), notes: shipForm.notes || undefined })
      toast.success('Shipment created')
      setShowNewShipment(false)
      fetchData()
    } catch { toast.error('Failed to create shipment') }
    finally { setSaving(false) }
  }

  const getBranchName = (id: number) => branches.find(b => b.id === id)?.name || `Branch #${id}`

  const statusColor = (s: string) => {
    const colors: Record<string, string> = { requested: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-300', approved: 'bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light', picked_up: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300', in_transit: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300', received: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300', completed: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300', cancelled: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300' }
    return colors[s] || 'bg-earth-100 text-earth-800 dark:bg-earth-700 dark:text-earth-300'
  }

  const actionButtons = (req: TransitRequest) => {
    const actions: Record<string, string[]> = { requested: ['approve'], approved: ['pickup'], picked_up: ['receive'], in_transit: ['receive'] }
    return (actions[req.status] || []).map(action => (
      <button key={action} onClick={() => handleAction(req.id, action)} className="px-2 py-1 text-xs rounded bg-lsc-rose text-white hover:bg-lsc-rose/90 capitalize">{action}</button>
    ))
  }

  const inputCls = "w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
  const labelCls = "block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"

  return (
    <AdminShell title="Transit Management">
      <div>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl"><Truck className="w-6 h-6 text-lsc-rose" /></div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Transit Management</h1>
          </div>
          <button onClick={() => tab === 'requests' ? setShowNewRequest(true) : setShowNewShipment(true)} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm">
            <Plus className="w-4 h-4" /> {tab === 'requests' ? 'New Request' : 'New Shipment'}
          </button>
        </div>

        <div className="border-b border-lsc-border dark:border-earth-700 mb-6">
          <nav className="flex gap-4">
            {(['requests', 'shipments'] as TabId[]).map(t => (
              <button key={t} onClick={() => setTab(t)} className={`pb-3 px-1 border-b-2 font-medium capitalize ${tab === t ? 'border-lsc-rose text-lsc-rose' : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70'}`}>{t}</button>
            ))}
          </nav>
        </div>

        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" /></div>
        ) : tab === 'requests' ? (
          <div className="space-y-3">
            {requests.length === 0 ? (
              <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60"><Package className="w-12 h-12 mx-auto mb-3 opacity-50" /><p>No transit requests</p></div>
            ) : requests.map(req => (
              <div key={req.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-mono text-lsc-dark/70 dark:text-lsc-cream/60">Item #{req.item_copy_id}</span>
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/40"><ArrowRight className="w-4 h-4" /></span>
                    <span className="text-sm text-lsc-dark dark:text-lsc-cream">{getBranchName(req.from_branch_id)} → {getBranchName(req.to_branch_id)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(req.status)}`}>{req.status.replace('_', ' ')}</span>
                    {actionButtons(req)}
                    {!['received', 'completed', 'cancelled'].includes(req.status) && (
                      <button onClick={() => handleAction(req.id, 'cancel')} className="px-2 py-1 text-xs rounded border border-status-danger-300 text-status-danger-600 hover:bg-status-danger-50 dark:border-status-danger-800 dark:text-status-danger-400">Cancel</button>
                    )}
                  </div>
                </div>
                <div className="mt-2 flex gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  <span>Reason: {req.reason.replace('_', ' ')}</span>
                  <span>Priority: {req.priority}</span>
                  <span>Requested: {new Date(req.requested_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {shipments.length === 0 ? (
              <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60"><Truck className="w-12 h-12 mx-auto mb-3 opacity-50" /><p>No shipments</p></div>
            ) : shipments.map(ship => (
              <div key={ship.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-mono text-sm font-medium text-lsc-dark dark:text-lsc-cream">{ship.shipment_number}</span>
                    <span className="ml-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{getBranchName(ship.from_branch_id)} → {getBranchName(ship.to_branch_id)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{ship.item_count} items</span>
                    {!ship.shipped_at && <button onClick={() => handleShipAction(ship.id, 'ship')} className="px-2 py-1 text-xs rounded bg-lsc-rose text-white hover:bg-lsc-rose/90">Ship</button>}
                    {ship.shipped_at && !ship.received_at && <button onClick={() => handleShipAction(ship.id, 'receive')} className="px-2 py-1 text-xs rounded bg-status-success-600 text-white hover:bg-status-success-700">Receive</button>}
                    {ship.received_at && <CheckCircle className="w-4 h-4 text-status-success-500" />}
                  </div>
                </div>
                {ship.notes && <p className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{ship.notes}</p>}
              </div>
            ))}
          </div>
        )}

        {/* New Request Modal */}
        {showNewRequest && (
          <ModalBackdrop onClose={() => setShowNewRequest(false)} title="New Transit Request">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">New Transit Request</h3>
                <button onClick={() => setShowNewRequest(false)} aria-label={t('aria.staffTransit.closeModal')}><X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" /></button>
              </div>
              <form onSubmit={submitRequest} className="p-4 space-y-4">
                <div><label htmlFor="transit-item-copy-id" className={labelCls}>Item Copy ID *</label><input id="transit-item-copy-id" type="number" required value={reqForm.item_copy_id} onChange={e => setReqForm({...reqForm, item_copy_id: e.target.value})} className={inputCls} /></div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label htmlFor="transit-from-branch" className={labelCls}>From Branch *</label><select id="transit-from-branch" required value={reqForm.from_branch_id} onChange={e => setReqForm({...reqForm, from_branch_id: e.target.value})} className={inputCls}><option value="">Select...</option>{branches.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div>
                  <div><label htmlFor="transit-to-branch" className={labelCls}>To Branch *</label><select id="transit-to-branch" required value={reqForm.to_branch_id} onChange={e => setReqForm({...reqForm, to_branch_id: e.target.value})} className={inputCls}><option value="">Select...</option>{branches.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label htmlFor="transit-reason" className={labelCls}>Reason</label><select id="transit-reason" value={reqForm.reason} onChange={e => setReqForm({...reqForm, reason: e.target.value})} className={inputCls}>{REASONS.map(r => <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>)}</select></div>
                  <div><label htmlFor="transit-priority" className={labelCls}>Priority</label><select id="transit-priority" value={reqForm.priority} onChange={e => setReqForm({...reqForm, priority: e.target.value})} className={inputCls}>{PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}</select></div>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button type="button" onClick={() => setShowNewRequest(false)} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70">Cancel</button>
                  <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50">{saving ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Create'}</button>
                </div>
              </form>
            </div>
          </ModalBackdrop>
        )}

        {/* New Shipment Modal */}
        {showNewShipment && (
          <ModalBackdrop onClose={() => setShowNewShipment(false)} title="New Shipment">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">New Shipment</h3>
                <button onClick={() => setShowNewShipment(false)} aria-label={t('aria.staffTransit.closeModal')}><X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" /></button>
              </div>
              <form onSubmit={submitShipment} className="p-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div><label htmlFor="ship-from-branch" className={labelCls}>From Branch *</label><select id="ship-from-branch" required value={shipForm.from_branch_id} onChange={e => setShipForm({...shipForm, from_branch_id: e.target.value})} className={inputCls}><option value="">Select...</option>{branches.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div>
                  <div><label htmlFor="ship-to-branch" className={labelCls}>To Branch *</label><select id="ship-to-branch" required value={shipForm.to_branch_id} onChange={e => setShipForm({...shipForm, to_branch_id: e.target.value})} className={inputCls}><option value="">Select...</option>{branches.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div>
                </div>
                <div><label htmlFor="ship-notes" className={labelCls}>Notes</label><textarea id="ship-notes" value={shipForm.notes} onChange={e => setShipForm({...shipForm, notes: e.target.value})} rows={2} className={inputCls} /></div>
                <div className="flex justify-end gap-2 pt-2">
                  <button type="button" onClick={() => setShowNewShipment(false)} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70">Cancel</button>
                  <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50">{saving ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Create'}</button>
                </div>
              </form>
            </div>
          </ModalBackdrop>
        )}
      </div>
    </AdminShell>
  )
}
