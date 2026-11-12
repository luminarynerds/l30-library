/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Building2,
  Plus,
  Edit,
  Search,
  Mail,
  Phone,
  Globe,
  MapPin,
  Percent,
  Clock,
  Loader2,
  X,
  Zap,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getVendors,
  getVendor,
  createVendor,
  updateVendor,
  type Vendor,
  type VendorCreateData,
} from '@/api/acquisition-api'
import { getVendorEDIProfile } from '@/api/domains/admin/edi-api'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

export default function AcquisitionVendorsPage(): React.ReactElement {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null)
  const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null)
  const [vendorEDIStatus, setVendorEDIStatus] = useState<Record<number, boolean>>({})

  // Form state
  const [formData, setFormData] = useState<VendorCreateData>({
    name: '',
    code: '',
    contact_name: '',
    email: '',
    phone: '',
    address: '',
    website: '',
    notes: '',
    discount_percentage: 0,
  })

  // Queries
  const { data: vendorsData, isLoading } = useQuery({
    queryKey: ['acquisition', 'vendors', searchQuery, statusFilter],
    queryFn: () => getVendors({
      ...(searchQuery ? { q: searchQuery } : {}),
      ...(statusFilter ? { status: statusFilter } : {}),
    }),
  })

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { data: _vendorDetail } = useQuery({
    queryKey: ['acquisition', 'vendor', selectedVendor?.id],
    queryFn: () => getVendor(selectedVendor!.id),
    enabled: !!selectedVendor,
  })

  useEffect(() => {
    if (!vendorsData?.items) return
    vendorsData.items.forEach(async (vendor) => {
      try {
        const profile = await getVendorEDIProfile(vendor.id)
        setVendorEDIStatus(prev => ({ ...prev, [vendor.id]: !!profile?.is_enabled }))
      } catch {
        setVendorEDIStatus(prev => ({ ...prev, [vendor.id]: false }))
      }
    })
  }, [vendorsData])

  // Mutations
  const createMutation = useMutation({
    mutationFn: createVendor,
    onSuccess: () => {
      toast.success(t('toast.acquisitionVendors.vendorCreated'))
      queryClient.invalidateQueries({ queryKey: ['acquisition', 'vendors'] })
      setShowModal(false)
      resetForm()
    },
    onError: () => toast.error(t('acquisitionVendors.failedToCreateVendor')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<VendorCreateData> }) => updateVendor(id, data),
    onSuccess: () => {
      toast.success(t('toast.acquisitionVendors.vendorUpdated'))
      queryClient.invalidateQueries({ queryKey: ['acquisition', 'vendors'] })
      setShowModal(false)
      setEditingVendor(null)
      resetForm()
    },
    onError: () => toast.error(t('acquisitionVendors.failedToUpdateVendor')),
  })

  const resetForm = () => {
    setFormData({
      name: '',
      code: '',
      contact_name: '',
      email: '',
      phone: '',
      address: '',
      website: '',
      notes: '',
      discount_percentage: 0,
    })
  }

  const openEditModal = (vendor: Vendor) => {
    setEditingVendor(vendor)
    setFormData({
      name: vendor.name,
      code: vendor.code,
      contact_name: vendor.contact_name || '',
      email: vendor.email || '',
      phone: vendor.phone || '',
      address: vendor.address || '',
      website: vendor.website || '',
      notes: vendor.notes || '',
      discount_percentage: vendor.discount_percentage,
    })
    setShowModal(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingVendor) {
      updateMutation.mutate({ id: editingVendor.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const getStatusBadge = (status: string) => {
    return status === 'active'
      ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400'
      : 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
  }

  return (

    <AdminShell title="Acquisition Vendors">    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      <PageContainer width="wide" className="py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
              <Building2 className="w-8 h-8 text-lsc-rose" />
              Vendor Management
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('acquisitionVendors.manageSupplierRelationshipsAndContacts')}</p>
          </div>
          <button
            onClick={() => { resetForm(); setEditingVendor(null); setShowModal(true) }}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90"
          >
            <Plus className="w-4 h-4" />
            New Vendor
          </button>
        </div>

        {/* Search & Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="relative flex-1 min-w-full sm:min-w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('placeholder.acquisitionManagement.searchVendors')}
              aria-label={t('aria.acquisitionManagement.searchVendors')}
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <select
            id="vendors-status-filter"
            aria-label={t('aria.acquisition.filterByStatus')}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        {/* Vendors Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {vendorsData?.items.map((vendor) => (
              <div
                key={vendor.id}
                className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => setSelectedVendor(vendor)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => setSelectedVendor(vendor))(); } }}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{vendor.name}</h3>
                    <p className="text-sm font-mono text-lsc-dark/70 dark:text-lsc-cream/70">{vendor.code}</p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {vendorEDIStatus[vendor.id] && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        EDI
                      </span>
                    )}
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(vendor.status)}`}>
                      {vendor.status}
                    </span>
                  </div>
                </div>

                {vendor.contact_name && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{vendor.contact_name}</p>
                )}

                <div className="space-y-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {vendor.email && (
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4" />
                      <span className="truncate" title={vendor.email}>{vendor.email}</span>
                    </div>
                  )}
                  {vendor.phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="w-4 h-4" />
                      <span>{vendor.phone}</span>
                    </div>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-earth-100 dark:border-earth-700 flex items-center justify-between text-sm">
                  {vendor.discount_percentage > 0 && (
                    <div className="flex items-center gap-1 text-status-success-600 dark:text-status-success-400">
                      <Percent className="w-4 h-4" />
                      <span>{vendor.discount_percentage}% discount</span>
                    </div>
                  )}
                  {vendor.average_delivery_days && (
                    <div className="flex items-center gap-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Clock className="w-4 h-4" />
                      <span>{vendor.average_delivery_days} days avg</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {vendorsData?.items.length === 0 && (
          <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
            <Building2 className="w-12 h-12 text-earth-300 dark:text-earth-300 mx-auto mb-4" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No vendors found.</p>
          </div>
        )}

        {/* Create/Edit Modal */}
        {showModal && (
          <ModalBackdrop onClose={() => { setShowModal(false); setEditingVendor(null) }} title="Dialog">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-lg w-full max-h-[90vh] overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  {editingVendor ? 'Edit Vendor' : 'New Vendor'}
                </h3>
                <button onClick={() => { setShowModal(false); setEditingVendor(null) }} aria-label={t('aria.acquisitionVendors.closeVendorForm', 'Close')} className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleSubmit} className="p-4 space-y-4 overflow-y-auto max-h-[70vh]">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="vendor-form-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Vendor Name *</label>
                    <input
                      id="vendor-form-name"
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required
                      className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div>
                    <label htmlFor="vendor-form-code" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Vendor Code *</label>
                    <input
                      id="vendor-form-code"
                      type="text"
                      value={formData.code}
                      onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                      required
                      disabled={!!editingVendor}
                      className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream disabled:opacity-50"
                    />
                  </div>
                </div>
                <div>
                  <label htmlFor="vendor-form-contact-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Contact Name</label>
                  <input
                    id="vendor-form-contact-name"
                    type="text"
                    value={formData.contact_name}
                    onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="vendor-form-email" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Email</label>
                    <input
                      id="vendor-form-email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div>
                    <label htmlFor="vendor-form-phone" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Phone</label>
                    <input
                      id="vendor-form-phone"
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                </div>
                <div>
                  <label htmlFor="vendor-form-address" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Address</label>
                  <textarea
                    id="vendor-form-address"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    rows={2}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label htmlFor="vendor-form-website" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Website</label>
                  <input
                    id="vendor-form-website"
                    type="url"
                    value={formData.website}
                    onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                    placeholder={t('placeholder.acquisitionVendors.httpswwwvendorsitecom')}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label htmlFor="vendor-form-discount" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Discount %</label>
                  <input
                    id="vendor-form-discount"
                    type="number"
                    value={formData.discount_percentage}
                    onChange={(e) => setFormData({ ...formData, discount_percentage: parseFloat(e.target.value) || 0 })}
                    min="0"
                    max="100"
                    step="0.1"
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label htmlFor="vendor-form-notes" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Notes</label>
                  <textarea
                    id="vendor-form-notes"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows={2}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </form>
              <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); setEditingVendor(null) }}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {createMutation.isPending || updateMutation.isPending ? (
                    <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                  ) : editingVendor ? 'Update' : 'Create'}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* Vendor Detail Modal */}
        {selectedVendor && (
          <ModalBackdrop onClose={() => setSelectedVendor(null)} title="EDI Integration">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-lg w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{selectedVendor.name}</h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => { openEditModal(selectedVendor); setSelectedVendor(null) }}
                    aria-label={t('aria.acquisitionVendors.editVendor', 'Edit vendor {{name}}').replace('{{name}}', selectedVendor.name)}
                    className="p-2 text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button onClick={() => setSelectedVendor(null)} aria-label={t('aria.acquisitionVendors.closeEdiIntegration', 'Close')} className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200">
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-lsc-dark/70 dark:text-lsc-cream/70">{selectedVendor.code}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(selectedVendor.status)}`}>
                    {selectedVendor.status}
                  </span>
                </div>

                {selectedVendor.contact_name && (
                  <div className="text-lsc-dark/70 dark:text-lsc-cream/70">{selectedVendor.contact_name}</div>
                )}

                <div className="space-y-2">
                  {selectedVendor.email && (
                    <a href={`mailto:${selectedVendor.email}`} className="flex items-center gap-2 text-lsc-rose hover:underline">
                      <Mail className="w-4 h-4" />
                      {selectedVendor.email}
                    </a>
                  )}
                  {selectedVendor.phone && (
                    <a href={`tel:${selectedVendor.phone}`} className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose hover:underline">
                      <Phone className="w-4 h-4" />
                      {selectedVendor.phone}
                    </a>
                  )}
                  {selectedVendor.website && (
                    <a href={selectedVendor.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose hover:underline">
                      <Globe className="w-4 h-4" />
                      {selectedVendor.website}
                    </a>
                  )}
                  {selectedVendor.address && (
                    <div className="flex items-start gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <MapPin className="w-4 h-4 mt-0.5" />
                      <span className="whitespace-pre-wrap">{selectedVendor.address}</span>
                    </div>
                  )}
                </div>

                <div className="pt-4 border-t border-lsc-border dark:border-earth-700 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Discount</p>
                    <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{selectedVendor.discount_percentage}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Avg Delivery</p>
                    <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{selectedVendor.average_delivery_days ?? '-'} days</p>
                  </div>
                </div>

                {selectedVendor.notes && (
                  <div className="pt-4 border-t border-lsc-border dark:border-earth-700">
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Notes</p>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{selectedVendor.notes}</p>
                  </div>
                )}

                <div className="pt-4 border-t border-lsc-border dark:border-earth-700">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Zap className="w-4 h-4 text-earth-600" />
                      <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">EDI Integration</span>
                    </div>
                    {vendorEDIStatus[selectedVendor.id] ? (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400">Connected</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300">Not Configured</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </ModalBackdrop>
        )}
      </PageContainer>
    </div>
  </AdminShell>
  )
}
