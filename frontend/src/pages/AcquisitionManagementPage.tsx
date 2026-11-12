/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable @typescript-eslint/no-unused-expressions */
import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Plus, Edit2, Trash2, X, Loader2, Check, Search } from 'lucide-react'
import toast from 'react-hot-toast'
import ConfirmDialog from '../components/ConfirmDialog'
import { fetchApi } from '@/api/fetchApi'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { parseDate } from '@/utils/format-utils'
import PageContainer from '@/components/layout/PageContainer'

interface Vendor {
  id: number
  name: string
  email: string
  phone?: string
  address?: string
  status: 'active' | 'inactive'
}

interface PurchaseOrder {
  id: number
  po_number: string
  vendor_id: number
  vendor_name?: string
  total_amount: number
  status: 'draft' | 'pending' | 'approved' | 'received'
  order_date: string
}

// Mirrors FundResponse (backend/app/schemas/acquisition.py): the API exposes
// allocated_amount + available_amount, not balance/allocated.
interface AcquisitionFund {
  id: number
  code: string
  name: string
  allocated_amount: number
  available_amount: number
}

export default function AcquisitionManagementPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token } = useAuth()
  const [activeTab, setActiveTab] = useState<'vendors' | 'orders' | 'funds'>('vendors')
  const [isLoading, setIsLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Vendors
  const [vendors, setVendors] = useState<Vendor[]>([])
  const [vendorSearch, setVendorSearch] = useState('')
  const [editingVendor, setEditingVendor] = useState<number | null>(null)
  const [vendorForm, setVendorForm] = useState<{ name: string; email: string; phone: string; address: string; status: 'active' | 'inactive' }>({ name: '', email: '', phone: '', address: '', status: 'active' })

  // Orders
  const [orders, setOrders] = useState<PurchaseOrder[]>([])
  const [editingOrder, setEditingOrder] = useState<number | null>(null)
  const [orderForm, setOrderForm] = useState<{ po_number: string; vendor_id: number; total_amount: number; status: 'draft' | 'pending' | 'approved' | 'received' }>({ po_number: '', vendor_id: 0, total_amount: 0, status: 'draft' })

  // Funds
  const [funds, setFunds] = useState<AcquisitionFund[]>([])
  const [editingFund, setEditingFund] = useState<number | null>(null)
  const [fundForm, setFundForm] = useState({ name: '', code: '', allocated_amount: 0 })

  // Delete confirmations
  const [deleteVendorConfirm, setDeleteVendorConfirm] = useState<{ id: number; name: string } | null>(null)
  const [deleteOrderConfirm, setDeleteOrderConfirm] = useState<{ id: number; name: string } | null>(null)

  const loadData = async () => {
    if (!token) return
    setIsLoading(true)
    try {
      if (activeTab === 'vendors') {
        const data = await fetchApi(`/acquisition/vendors?search=${vendorSearch}`)
        setVendors(Array.isArray(data) ? data : data.items ?? [])
      } else if (activeTab === 'orders') {
        const data = await fetchApi('/acquisition/purchase-orders')
        setOrders(Array.isArray(data) ? data : data.items ?? [])
      } else if (activeTab === 'funds') {
        const data = await fetchApi('/acquisition/funds')
        setFunds(Array.isArray(data) ? data : data.items ?? [])
      }
    } catch (_err) {
      toast.error(t('acquisitionManagement.failedToLoadData'))
    } finally {
      setIsLoading(false)
    }
  }


  useEffect(() => {
    if (!user || !['admin', 'super_admin', 'staff'].includes(user.role)) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      return
    }
    loadData()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, activeTab])

  // Vendor handlers
  const openVendorForm = (vendor?: Vendor) => {
    if (vendor) {
      setVendorForm({ name: vendor.name, email: vendor.email, phone: vendor.phone || '', address: vendor.address || '', status: vendor.status })
      setEditingVendor(vendor.id)
    } else {
      setVendorForm({ name: '', email: '', phone: '', address: '', status: 'active' })
      setEditingVendor(null)
    }
    setActiveTab('vendors')
    setShowForm(true)
  }

  const saveVendor = async () => {
    if (!token || !vendorForm.name || !vendorForm.email) return
    setIsSubmitting(true)
    try {
      const method = editingVendor ? 'PUT' : 'POST'
      const path = editingVendor ? `/acquisition/vendors/${editingVendor}` : '/acquisition/vendors'
      await fetchApi(path, { method, body: JSON.stringify(vendorForm) })
      toast.success(editingVendor ? t('toast.acquisitionVendors.vendorUpdated') : t('toast.acquisitionManagement.vendorAdded'))
      setShowForm(false)
      loadData()
    } catch (_err) {
      toast.error(t('acquisitionManagement.failedToSaveVendor'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const deleteVendor = async (id: number) => {
    if (!token) return
    try {
      await fetchApi(`/acquisition/vendors/${id}`, { method: 'DELETE' })
      toast.success(t('toast.acquisitionManagement.vendorDeleted'))
      setDeleteVendorConfirm(null)
      loadData()
    } catch {
      toast.error(t('acquisitionManagement.failedToDeleteVendor'))
    }
  }

  // Order handlers
  const openOrderForm = (order?: PurchaseOrder) => {
    if (order) {
      setOrderForm({ po_number: order.po_number, vendor_id: order.vendor_id, total_amount: order.total_amount, status: order.status })
      setEditingOrder(order.id)
    } else {
      setOrderForm({ po_number: '', vendor_id: 0, total_amount: 0, status: 'draft' })
      setEditingOrder(null)
    }
    setActiveTab('orders')
    setShowForm(true)
  }

  const saveOrder = async () => {
    if (!token || !orderForm.po_number || orderForm.vendor_id === 0) return
    setIsSubmitting(true)
    try {
      const method = editingOrder ? 'PUT' : 'POST'
      const path = editingOrder ? `/acquisition/purchase-orders/${editingOrder}` : '/acquisition/purchase-orders'
      await fetchApi(path, { method, body: JSON.stringify(orderForm) })
      toast.success(editingOrder ? t('toast.acquisitionManagement.orderUpdated') : t('toast.acquisitionManagement.orderCreated'))
      setShowForm(false)
      loadData()
    } catch (_err) {
      toast.error(t('acquisitionManagement.failedToSaveOrder'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const deleteOrder = async (id: number) => {
    if (!token) return
    try {
      await fetchApi(`/acquisition/purchase-orders/${id}`, { method: 'DELETE' })
      toast.success(t('toast.acquisitionManagement.orderDeleted'))
      setDeleteOrderConfirm(null)
      loadData()
    } catch {
      toast.error(t('acquisitionManagement.failedToDeleteOrder'))
    }
  }

  // Fund handlers
  const openFundForm = (fund?: AcquisitionFund) => {
    if (fund) {
      setFundForm({ name: fund.name, code: fund.code, allocated_amount: fund.allocated_amount })
      setEditingFund(fund.id)
    } else {
      setFundForm({ name: '', code: '', allocated_amount: 0 })
      setEditingFund(null)
    }
    setActiveTab('funds')
    setShowForm(true)
  }

  const saveFund = async () => {
    if (!token || !fundForm.name || (!editingFund && !fundForm.code)) return
    setIsSubmitting(true)
    try {
      const method = editingFund ? 'PUT' : 'POST'
      const path = editingFund ? `/acquisition/funds/${editingFund}` : '/acquisition/funds'
      await fetchApi(path, { method, body: JSON.stringify(fundForm) })
      toast.success(editingFund ? t('toast.acquisitionFunds.fundUpdated') : t('toast.acquisitionFunds.fundCreated'))
      setShowForm(false)
      loadData()
    } catch (_err) {
      toast.error(t('acquisitionManagement.failedToSaveFund'))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!user || !['admin', 'super_admin', 'staff'].includes(user.role)) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-earth-950 py-20">
        <PageContainer className="text-center">
          <p className="text-lsc-dark dark:text-lsc-cream">Staff access required</p>
        </PageContainer>
      </div>
    )
  }

  return (
    <AdminShell title="Acquisition Management" subtitle={t('acquisitionManagement.manageVendorsPurchaseOrdersAnd')}>
      <div className="min-h-screen bg-lsc-cream dark:bg-earth-950 py-8 transition-colors duration-500">
        <PageContainer>
          <div className="flex items-center justify-between mb-10">
            <div className="flex gap-1">
              {(['vendors', 'orders', 'funds'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  role="tab"
                  aria-selected={activeTab === tab}
                  className={`px-6 py-2.5 font-bold rounded-full transition-all duration-300 ${
                    activeTab === tab
                      ? 'bg-lsc-rose text-white shadow-md shadow-lsc-rose/20'
                      : 'text-earth-600 hover:text-lsc-rose hover:bg-white dark:hover:bg-earth-800'
                  }`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>
            <button 
              onClick={() => { setShowForm(true); }} 
              className="px-6 py-2.5 bg-lsc-dark dark:bg-lsc-cream text-white dark:text-lsc-dark font-bold rounded-xl flex items-center gap-2 transition-all duration-300 hover:scale-105 shadow-soft-sm active:scale-95"
            >
              <Plus className="w-5 h-5" />
              Add New
            </button>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-32">
              <Loader2 className="w-10 h-10 text-lsc-rose motion-safe:animate-spin" />
            </div>
          ) : activeTab === 'vendors' ? (
            <div className="bg-lsc-white dark:bg-earth-900 rounded-xl border border-earth-200 dark:border-earth-800 overflow-hidden shadow-soft-sm">
              <div className="p-6 border-b border-earth-100 dark:border-earth-800 bg-earth-50/50 dark:bg-earth-900/50">
                <div className="relative max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-600" />
                  <input 
                    type="text" 
                    placeholder={t('placeholder.acquisitionManagement.searchVendors')} 
                    value={vendorSearch} 
                    onChange={(e) => setVendorSearch(e.target.value)} 
                    className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-earth-800 border border-earth-200 dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream placeholder:text-earth-400 focus:outline-none focus:ring-2 focus:ring-lsc-rose/30 transition-all" 
                  />
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-earth-50/50 dark:bg-earth-900/50 border-b border-earth-100 dark:border-earth-800">
                      <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.15em] text-earth-600">Name</th>
                      <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.15em] text-earth-600">Email</th>
                      <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.15em] text-earth-600">Phone</th>
                      <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.15em] text-earth-600">Status</th>
                      <th className="px-6 py-4 text-right text-xs font-bold uppercase tracking-[0.15em] text-earth-600">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-earth-50 dark:divide-earth-800">
                    {vendors.map((v) => (
                      <tr key={v.id} className="group hover:bg-earth-50/30 dark:hover:bg-earth-800/30 transition-colors">
                        <td className="px-6 py-5 font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream">{v.name}</td>
                        <td className="px-6 py-5 text-sm text-earth-600 dark:text-earth-400 font-mono">{v.email}</td>
                        <td className="px-6 py-5 text-sm text-earth-600 dark:text-earth-400 font-mono">{v.phone || '-'}</td>
                        <td className="px-6 py-5">
                          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                            v.status === 'active' 
                              ? 'bg-forest-50 text-forest-700 dark:bg-forest-900/20 dark:text-forest-400' 
                              : 'bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-300'
                          }`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${v.status === 'active' ? 'bg-forest-600' : 'bg-earth-400'}`} />
                            {v.status}
                          </span>
                        </td>
                        <td className="px-6 py-5 text-right">
                          <div className="flex gap-2 justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                            <button onClick={() => openVendorForm(v)} className="p-2 text-earth-600 hover:text-lsc-rose hover:bg-lsc-rose/5 rounded-lg transition-all" aria-label={`Edit vendor ${v.name}`}>
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button onClick={() => setDeleteVendorConfirm({ id: v.id, name: v.name })} className="p-2 text-earth-600 hover:text-status-danger-600 hover:bg-status-danger-50 rounded-lg transition-all" aria-label={`Delete vendor ${v.name}`}>
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : activeTab === 'orders' ? (
            <div className="bg-lsc-white dark:bg-earth-900 rounded-xl border border-earth-200 dark:border-earth-800 overflow-hidden shadow-soft-sm">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-earth-50/50 dark:bg-earth-900/50 border-b border-earth-100 dark:border-earth-800">
                      <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.15em] text-earth-600">PO Number</th>
                      <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.15em] text-earth-600">Vendor</th>
                      <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.15em] text-earth-600">Amount</th>
                      <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.15em] text-earth-600">Status</th>
                      <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.15em] text-earth-600">Date</th>
                      <th className="px-6 py-4 text-right text-xs font-bold uppercase tracking-[0.15em] text-earth-600">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-earth-50 dark:divide-earth-800">
                    {orders.map((o) => (
                      <tr key={o.id} className="group hover:bg-earth-50/30 dark:hover:bg-earth-800/30 transition-colors">
                        <td className="px-6 py-5 font-mono text-sm font-bold text-lsc-dark dark:text-lsc-cream">{o.po_number}</td>
                        <td className="px-6 py-5 text-sm font-medium text-earth-700 dark:text-earth-300">{o.vendor_name || 'N/A'}</td>
                        <td className="px-6 py-5 font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream">${o.total_amount.toLocaleString()}</td>
                        <td className="px-6 py-5">
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest bg-earth-100 dark:bg-earth-800 text-earth-600 dark:text-earth-400 border border-earth-200 dark:border-earth-700">
                            {o.status}
                          </span>
                        </td>
                        <td className="px-6 py-5 text-sm text-earth-600 dark:text-earth-300">{parseDate(o.order_date)?.toLocaleDateString() ?? '-'}</td>
                        <td className="px-6 py-5 text-right">
                          <div className="flex gap-2 justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                            <button onClick={() => openOrderForm(o)} className="p-2 text-earth-600 hover:text-lsc-rose hover:bg-lsc-rose/5 rounded-lg transition-all" aria-label={`Edit order ${o.po_number}`}>
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button onClick={() => setDeleteOrderConfirm({ id: o.id, name: o.po_number })} className="p-2 text-earth-600 hover:text-status-danger-600 hover:bg-status-danger-50 rounded-lg transition-all" aria-label={`Delete order ${o.po_number}`}>
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : activeTab === 'funds' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {funds.map((f) => (
                <div key={f.id} className="group bg-lsc-white dark:bg-earth-900 rounded-xl p-8 border border-earth-200 dark:border-earth-800 shadow-soft-sm hover:shadow-soft-md hover:scale-[1.02] transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]">
                  <div className="flex justify-between items-start mb-8">
                    <h3 className="font-serif font-bold text-2xl text-lsc-dark dark:text-lsc-cream leading-tight">{f.name}</h3>
                    <button onClick={() => openFundForm(f)} className="p-2 text-earth-600 hover:text-lsc-rose hover:bg-lsc-rose/5 rounded-lg transition-all opacity-0 group-hover:opacity-100" aria-label={`Edit fund ${f.name}`}>
                      <Edit2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="space-y-6">
                    <div className="flex items-end justify-between">
                      <div>
                        <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-earth-600 dark:text-earth-300 mb-1">Available Balance</p>
                        <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream tracking-tight">${(f.available_amount ?? 0).toLocaleString()}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-earth-600 dark:text-earth-300 mb-1">Allocated</p>
                        <p className="text-xl font-bold text-lsc-rose tracking-tight">${(f.allocated_amount ?? 0).toLocaleString()}</p>
                      </div>
                    </div>
                    <div className="relative pt-2">
                      <div className="w-full bg-earth-100 dark:bg-earth-800 rounded-full h-2.5 overflow-hidden">
                        <div
                          className="bg-lsc-rose rounded-full h-full transition-all duration-1000 ease-[cubic-bezier(0.16,1,0.3,1)]"
                          style={{ width: `${f.allocated_amount > 0 ? Math.min(((f.allocated_amount - f.available_amount) / f.allocated_amount) * 100, 100) : 0}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </PageContainer>

        {showForm && (
          <ModalBackdrop onClose={() => setShowForm(false)} title="Dialog">
            <div className="bg-lsc-white dark:bg-earth-900 rounded-xl shadow-soft-lg w-full max-w-md border border-earth-200 dark:border-earth-800 motion-safe:animate-hero-fade-up-1">
              <div className="flex items-center justify-between p-6 border-b border-earth-100 dark:border-earth-800">
                <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                  {activeTab === 'vendors' ? `${editingVendor ? 'Edit' : 'Add'} Vendor` : activeTab === 'orders' ? `${editingOrder ? 'Edit' : 'Create'} Order` : `${editingFund ? 'Edit' : 'Create'} Fund`}
                </h2>
                <button onClick={() => setShowForm(false)} className="p-2 hover:bg-earth-50 dark:hover:bg-earth-800 rounded-full transition-colors" aria-label={t('aria.authModals.close')}>
                  <X className="w-5 h-5 text-earth-600" />
                </button>
              </div>
              <form onSubmit={(e) => { e.preventDefault(); activeTab === 'vendors' ? saveVendor() : activeTab === 'orders' ? saveOrder() : saveFund(); }} className="p-8 space-y-6">
                {activeTab === 'vendors' && (
                  <div className="space-y-4">
                    <label htmlFor="acq-vendor-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.vendorName', 'Vendor Name')}</label>
                    <input id="acq-vendor-name" type="text" placeholder="Vendor Name" value={vendorForm.name} onChange={(e) => setVendorForm({ ...vendorForm, name: e.target.value })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all" required />
                    <label htmlFor="acq-vendor-email" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.email', 'Email Address')}</label>
                    <input id="acq-vendor-email" type="email" placeholder="Email Address" value={vendorForm.email} onChange={(e) => setVendorForm({ ...vendorForm, email: e.target.value })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all" required />
                    <label htmlFor="acq-vendor-phone" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.phone', 'Phone')}</label>
                    <input id="acq-vendor-phone" type="tel" placeholder="Phone" value={vendorForm.phone} onChange={(e) => setVendorForm({ ...vendorForm, phone: e.target.value })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all" />
                    <label htmlFor="acq-vendor-address" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.address', 'Address')}</label>
                    <input id="acq-vendor-address" type="text" placeholder="Address" value={vendorForm.address} onChange={(e) => setVendorForm({ ...vendorForm, address: e.target.value })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all" />
                    <label htmlFor="acq-vendor-status" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.status', 'Status')}</label>
                    <select id="acq-vendor-status" value={vendorForm.status} onChange={(e) => setVendorForm({ ...vendorForm, status: e.target.value as 'active' | 'inactive' })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all">
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                    </select>
                  </div>
                )}
                {activeTab === 'orders' && (
                  <div className="space-y-4">
                    <label htmlFor="acq-order-po-number" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.poNumber', 'PO Number')}</label>
                    <input id="acq-order-po-number" type="text" placeholder="PO Number" value={orderForm.po_number} onChange={(e) => setOrderForm({ ...orderForm, po_number: e.target.value })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all" required />
                    <label htmlFor="acq-order-vendor" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.vendor', 'Vendor')}</label>
                    <select id="acq-order-vendor" value={orderForm.vendor_id} onChange={(e) => setOrderForm({ ...orderForm, vendor_id: parseInt(e.target.value) })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all">
                      <option value={0}>Select Vendor</option>
                      {vendors.map((v) => (
                        <option key={v.id} value={v.id}>{v.name}</option>
                      ))}
                    </select>
                    <label htmlFor="acq-order-total" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.totalAmount', 'Total Amount')}</label>
                    <input id="acq-order-total" type="number" placeholder="Total Amount" value={orderForm.total_amount || ''} onChange={(e) => setOrderForm({ ...orderForm, total_amount: parseFloat(e.target.value) })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all" required />
                    <label htmlFor="acq-order-status" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.orderStatus', 'Order Status')}</label>
                    <select id="acq-order-status" value={orderForm.status} onChange={(e) => setOrderForm({ ...orderForm, status: e.target.value as 'pending' | 'approved' | 'draft' | 'received' })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all">
                      <option value="draft">Draft</option>
                      <option value="pending">Pending</option>
                      <option value="approved">Approved</option>
                      <option value="received">Received</option>
                    </select>
                  </div>
                )}
                {activeTab === 'funds' && (
                  <div className="space-y-4">
                    <label htmlFor="acq-fund-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.fundName', 'Fund Name')}</label>
                    <input id="acq-fund-name" type="text" placeholder="Fund Name" value={fundForm.name} onChange={(e) => setFundForm({ ...fundForm, name: e.target.value })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all" required />
                    <label htmlFor="acq-fund-code" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.fundCode', 'Fund Code (e.g. ADULT-FY26)')}</label>
                    <input id="acq-fund-code" type="text" placeholder="Fund Code (e.g. ADULT-FY26)" value={fundForm.code} onChange={(e) => setFundForm({ ...fundForm, code: e.target.value })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all" required />
                    <label htmlFor="acq-fund-amount" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('label.acquisitionManagement.allocatedAmount', 'Allocated Amount')}</label>
                    <input id="acq-fund-amount" type="number" placeholder="Allocated Amount" value={fundForm.allocated_amount || ''} onChange={(e) => setFundForm({ ...fundForm, allocated_amount: parseFloat(e.target.value) })} className="w-full px-5 py-3 rounded-xl border border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/30 transition-all" />
                  </div>
                )}
                <div className="flex justify-end gap-3 pt-6 border-t border-earth-100 dark:border-earth-800">
                  <button type="button" onClick={() => setShowForm(false)} disabled={isSubmitting} className="px-6 py-2.5 text-earth-600 font-bold hover:bg-earth-50 dark:hover:bg-earth-800 rounded-xl transition-all disabled:opacity-50">
                    Cancel
                  </button>
                  <button type="submit" disabled={isSubmitting} className="px-8 py-2.5 bg-lsc-rose text-white font-bold rounded-xl flex items-center gap-2 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 shadow-md shadow-lsc-rose/20">
                    {isSubmitting ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Check className="w-4 h-4" />}
                    {isSubmitting ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </div>
          </ModalBackdrop>
        )}

        <ConfirmDialog
          isOpen={!!deleteVendorConfirm}
          title="Delete Vendor?"
          message={`Are you sure you want to delete "${deleteVendorConfirm?.name}"? This action cannot be undone.`}
          confirmText="Delete"
          cancelText="Cancel"
          confirmVariant="danger"
          onConfirm={() => { if (deleteVendorConfirm) deleteVendor(deleteVendorConfirm.id) }}
          onCancel={() => setDeleteVendorConfirm(null)}
        />

        <ConfirmDialog
          isOpen={!!deleteOrderConfirm}
          title="Delete Order?"
          message={`Are you sure you want to delete order "${deleteOrderConfirm?.name}"? This action cannot be undone.`}
          confirmText="Delete"
          cancelText="Cancel"
          confirmVariant="danger"
          onConfirm={() => { if (deleteOrderConfirm) deleteOrder(deleteOrderConfirm.id) }}
          onCancel={() => setDeleteOrderConfirm(null)}
        />
      </div>
    </AdminShell>
  )
}
