/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useId } from "react"
import { Plus, Edit, X, Check } from "lucide-react"
import toast from "react-hot-toast"
import AcquisitionErrorBoundary from "../../components/acquisition/AcquisitionErrorBoundary"
import VendorComparison from "../../components/acquisition/VendorComparison"
import { type Vendor, apiFetch, formatMoney } from "./types"
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface VendorsTabProps {
  token: string
  vendors: Vendor[]
  loadData: () => void
}

export default function VendorsTab({ token, vendors, loadData }: VendorsTabProps) {
  const [showVendorForm, setShowVendorForm] = useState(false)
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null)
  const [vendorForm, setVendorForm] = useState({ name: "", contact_name: "", email: "", phone: "" })
  const nameId = useId()
  const contactId = useId()
  const emailId = useId()
  const phoneId = useId()

  const handleSaveVendor = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    try {
      if (editingVendor) {
        await apiFetch(token, "/vendors/" + editingVendor.id, { method: "PATCH", body: JSON.stringify(vendorForm) })
        toast.success(t('toast.acquisitionVendors.vendorUpdated'))
      } else {
        await apiFetch(token, "/vendors", { method: "POST", body: JSON.stringify(vendorForm) })
        toast.success(t('toast.acquisitionVendors.vendorCreated'))
      }
      setShowVendorForm(false)
      setEditingVendor(null)
      loadData()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  return (
    <>
      <div className="space-y-4">
        <div className="flex justify-between items-center"><h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Vendors</h2><button onClick={() => { setEditingVendor(null); setVendorForm({ name: "", contact_name: "", email: "", phone: "" }); setShowVendorForm(true) }} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"><Plus aria-hidden="true" className="w-4 h-4" />Add Vendor</button></div>
        {vendors.length === 0 ? <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">No vendors yet</p> : <div className="grid gap-4 md:grid-cols-2">{vendors.map((vendor) => (<div key={vendor.id} className="border border-lsc-border dark:border-earth-700 rounded-xl p-4"><div className="flex justify-between items-start"><div><h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{vendor.name}</h3>{vendor.contact_name && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{vendor.contact_name}</p>}{vendor.email && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{vendor.email}</p>}{vendor.phone && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{vendor.phone}</p>}</div><button onClick={() => { setEditingVendor(vendor); setVendorForm({ name: vendor.name, contact_name: vendor.contact_name || "", email: vendor.email || "", phone: vendor.phone || "" }); setShowVendorForm(true) }} className="p-2 text-lsc-dark/70 hover:text-lsc-rose rounded-xl" aria-label={`Edit vendor ${vendor.name}`}><Edit aria-hidden="true" className="w-4 h-4" /></button></div></div>))}</div>}
        <AcquisitionErrorBoundary fallbackMessage="Failed to load vendor performance">
          <VendorComparison token={token || ""} vendors={vendors} formatMoney={formatMoney} />
        </AcquisitionErrorBoundary>
      </div>

      {showVendorForm && <ModalBackdrop onClose={() => setShowVendorForm(false)} labelledBy="vendor-modal-title"><div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md"><div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between"><h2 id="vendor-modal-title" className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{editingVendor ? "Edit Vendor" : "Add Vendor"}</h2><button onClick={() => setShowVendorForm(false)} className="p-2 text-lsc-dark/70 hover:text-lsc-dark/70 rounded-xl" aria-label={t('aria.vendorsTab.closeVendorForm')}><X aria-hidden="true" className="w-5 h-5" /></button></div><form onSubmit={handleSaveVendor} className="p-6 space-y-4"><div><label htmlFor={nameId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Name *</label><input id={nameId} type="text" value={vendorForm.name} onChange={(e) => setVendorForm({ ...vendorForm, name: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required /></div><div><label htmlFor={contactId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Contact</label><input id={contactId} type="text" value={vendorForm.contact_name} onChange={(e) => setVendorForm({ ...vendorForm, contact_name: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /></div><div><label htmlFor={emailId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Email</label><input id={emailId} type="email" value={vendorForm.email} onChange={(e) => setVendorForm({ ...vendorForm, email: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /></div><div><label htmlFor={phoneId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Phone</label><input id={phoneId} type="tel" value={vendorForm.phone} onChange={(e) => setVendorForm({ ...vendorForm, phone: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /></div><div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700"><button type="button" onClick={() => setShowVendorForm(false)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl font-medium">Cancel</button><button type="submit" className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2"><Check aria-hidden="true" className="w-4 h-4" />Save</button></div></form></div></ModalBackdrop>}
    </>
  )
}
