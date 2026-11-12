/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import ConfirmDialog from "@/components/ConfirmDialog"
import { useState, useId } from "react"
import { Plus, Edit2, Trash2, Copy, X, Check, Save } from "lucide-react"
import toast from "react-hot-toast"
import AcquisitionErrorBoundary from "../../components/acquisition/AcquisitionErrorBoundary"
import FundSpendPreview from "../../components/acquisition/FundSpendPreview"
import TemplateSuggestions from "../../components/acquisition/TemplateSuggestions"
import {
  type OrderTemplate,
  type TemplateItem,
  type OrderTemplateCreate,
  type OrderTemplateUpdate,
  createOrderTemplate,
  updateOrderTemplate,
  deleteOrderTemplate,
  createPOFromTemplate,
  savePOAsTemplate,
} from "@/api/order-templates-api"
import { type Fund, type Vendor, formatMoney } from "./types"
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface TemplatesTabProps {
  token: string
  funds: Fund[]
  vendors: Vendor[]
  templates: OrderTemplate[]
  loadData: () => void
  setActiveTab: (tab: string) => void
  showSaveAsTemplate: boolean
  setShowSaveAsTemplate: (show: boolean) => void
  saveTemplatePOId: number
  saveTemplateForm: { name: string; description: string; is_shared: boolean }
  setSaveTemplateForm: (form: { name: string; description: string; is_shared: boolean }) => void
}

export default function TemplatesTab({ token, funds, vendors, templates, loadData, setActiveTab, showSaveAsTemplate, setShowSaveAsTemplate, saveTemplatePOId, saveTemplateForm, setSaveTemplateForm }: TemplatesTabProps) {
  const [showTemplateForm, setShowTemplateForm] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<OrderTemplate | null>(null)
  const [templateForm, setTemplateForm] = useState<{ name: string; description: string; vendor_id: number | null; fund_id: number | null; is_shared: boolean; template_items: TemplateItem[] }>({ name: "", description: "", vendor_id: null, fund_id: null, is_shared: false, template_items: [] })
  const [showCreatePOFromTemplate, setShowCreatePOFromTemplate] = useState(false)
  const [selectedTemplateForPO, setSelectedTemplateForPO] = useState<OrderTemplate | null>(null)
  const [templatePOVendorId, setTemplatePOVendorId] = useState<number | null>(null)
  const [templatePOFundId, setTemplatePOFundId] = useState<number | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null)
  const templateNameId = useId()
  const templateDescriptionId = useId()
  const templateVendorId = useId()
  const templateFundId = useId()
  const templatePOVendorSelectId = useId()
  const templatePOFundSelectId = useId()
  const saveTemplateNameId = useId()
  const saveTemplateDescriptionId = useId()

  const openCreateTemplate = () => {
    setEditingTemplate(null)
    setTemplateForm({ name: "", description: "", vendor_id: null, fund_id: null, is_shared: false, template_items: [] })
    setShowTemplateForm(true)
  }

  const openEditTemplate = (tmpl: OrderTemplate) => {
    setEditingTemplate(tmpl)
    setTemplateForm({
      name: tmpl.name,
      description: tmpl.description || "",
      vendor_id: tmpl.vendor_id || null,
      fund_id: tmpl.fund_id || null,
      is_shared: tmpl.is_shared,
      template_items: tmpl.template_items.map(i => ({ ...i })),
    })
    setShowTemplateForm(true)
  }

  const handleSaveTemplate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const payload = {
        name: templateForm.name,
        description: templateForm.description || undefined,
        vendor_id: templateForm.vendor_id,
        fund_id: templateForm.fund_id,
        is_shared: templateForm.is_shared,
        template_items: templateForm.template_items,
      }
      if (editingTemplate) {
        await updateOrderTemplate(editingTemplate.id, payload as OrderTemplateUpdate)
        toast.success(t('toast.adminBanTracker.templateUpdated'))
      } else {
        await createOrderTemplate(payload as OrderTemplateCreate)
        toast.success(t('toast.adminBanTracker.templateCreated'))
      }
      setShowTemplateForm(false)
      setEditingTemplate(null)
      loadData()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.templatesTab.failedToSaveTemplate'))
    }
  }

  const handleDeleteTemplate = (id: number) => {
    setPendingAction(() => async () => {
      try {
        await deleteOrderTemplate(id)
        toast.success(t('toast.adminBanTracker.templateDeleted'))
        loadData()
      } catch (err) {
        toast.error(err instanceof Error ? err.message : t('toast.staffMangaCataloging.failedToDeleteTemplate'))
      }
    })
    setConfirmOpen(true)
  }

  const openCreatePOFromTemplate = (tmpl: OrderTemplate) => {
    setSelectedTemplateForPO(tmpl)
    setTemplatePOVendorId(tmpl.vendor_id || (vendors.length > 0 ? vendors[0]?.id ?? null : null))
    setTemplatePOFundId(tmpl.fund_id || (funds.length > 0 ? funds[0]?.id ?? null : null))
    setShowCreatePOFromTemplate(true)
  }

  const handleConfirmCreatePOFromTemplate = async () => {
    if (!selectedTemplateForPO) return
    try {
      const result = await createPOFromTemplate(selectedTemplateForPO.id, {
        vendor_id: templatePOVendorId,
        fund_id: templatePOFundId,
      })
      toast.success(t('toast.templatesTab.poPonumberCreatedWithItemsadded', { ponumber: result.po_number, itemsadded: result.items_added }))
      setShowCreatePOFromTemplate(false)
      setSelectedTemplateForPO(null)
      setActiveTab("orders")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.templatesTab.failedToCreatePoFrom'))
    }
  }

  const handleConfirmSaveAsTemplate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await savePOAsTemplate(saveTemplatePOId, saveTemplateForm)
      toast.success(t('toast.templatesTab.savedAsTemplate'))
      setShowSaveAsTemplate(false)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.templatesTab.failedToSaveAsTemplate'))
    }
  }

  const addTemplateItem = () => {
    setTemplateForm(prev => ({
      ...prev,
      template_items: [...prev.template_items, { title: "", author: "", isbn: "", quantity: 1, unit_price: 0 }],
    }))
  }

  const removeTemplateItem = (index: number) => {
    setTemplateForm(prev => ({
      ...prev,
      template_items: prev.template_items.filter((_, i) => i !== index),
    }))
  }

  const updateTemplateItem = (index: number, field: keyof TemplateItem, value: string | number) => {
    setTemplateForm(prev => ({
      ...prev,
      template_items: prev.template_items.map((item, i) => i === index ? { ...item, [field]: value } : item),
    }))
  }

  return (
    <>
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Order Templates</h2>
          <button onClick={openCreateTemplate} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"><Plus aria-hidden="true" className="w-4 h-4" />Create Template</button>
        </div>
        <AcquisitionErrorBoundary fallbackMessage="Failed to load template suggestions">
          <TemplateSuggestions token={token || ""} onTemplateCreated={loadData} />
        </AcquisitionErrorBoundary>
        {templates.length === 0 ? (
          <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">No templates yet. Create one to speed up recurring orders.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Vendor</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Fund</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Items</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Shared</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {templates.map((tmpl) => (
                  <tr key={tmpl.id} className="hover:bg-lsc-cream dark:hover:bg-lsc-brown">
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">{tmpl.name}</p>
                        {tmpl.description && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">{tmpl.description}</p>}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{tmpl.vendor_name || "\u2014"}</td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{tmpl.fund_name || "\u2014"}</td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{tmpl.item_count}</td>
                    <td className="px-4 py-3">{tmpl.is_shared ? <span className="text-xs px-2 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 rounded font-medium">Yes</span> : <span className="text-xs px-2 py-0.5 bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded font-medium">No</span>}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button onClick={() => openCreatePOFromTemplate(tmpl)} className="p-1.5 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-dark/20 rounded" title="Create PO from Template" aria-label={`Create PO from template ${tmpl.name}`}><Copy aria-hidden="true" className="w-4 h-4" /></button>
                        <button onClick={() => openEditTemplate(tmpl)} className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded" title="Edit" aria-label={`Edit template ${tmpl.name}`}><Edit2 aria-hidden="true" className="w-4 h-4" /></button>
                        <button onClick={() => handleDeleteTemplate(tmpl.id)} className="p-1.5 text-status-danger-500 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded" title="Delete" aria-label={`Delete template ${tmpl.name}`}><Trash2 aria-hidden="true" className="w-4 h-4" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showTemplateForm && (
        <ModalBackdrop onClose={() => setShowTemplateForm(false)} labelledBy="template-modal-title" role="alertdialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
              <h2 id="template-modal-title" className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{editingTemplate ? "Edit Template" : "Create Template"}</h2>
              <button onClick={() => setShowTemplateForm(false)} className="p-2 text-lsc-dark/70 hover:text-lsc-dark rounded-xl" aria-label={t('aria.templatesTab.closeTemplateForm')}><X aria-hidden="true" className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSaveTemplate} className="p-6 space-y-4">
              <div>
                <label htmlFor={templateNameId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Name *</label>
                <input id={templateNameId} type="text" value={templateForm.name} onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required />
              </div>
              <div>
                <label htmlFor={templateDescriptionId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Description</label>
                <input id={templateDescriptionId} type="text" value={templateForm.description} onChange={(e) => setTemplateForm({ ...templateForm, description: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor={templateVendorId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Default Vendor</label>
                  <select id={templateVendorId} value={templateForm.vendor_id ?? ""} onChange={(e) => setTemplateForm({ ...templateForm, vendor_id: e.target.value ? parseInt(e.target.value) : null })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream">
                    <option value="">None</option>
                    {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                  </select>
                </div>
                <div>
                  <label htmlFor={templateFundId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Default Fund</label>
                  <select id={templateFundId} value={templateForm.fund_id ?? ""} onChange={(e) => setTemplateForm({ ...templateForm, fund_id: e.target.value ? parseInt(e.target.value) : null })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream">
                    <option value="">None</option>
                    {funds.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="template-shared" checked={templateForm.is_shared} onChange={(e) => setTemplateForm({ ...templateForm, is_shared: e.target.checked })} className="w-4 h-4 rounded border-lsc-border text-lsc-rose" />
                <label htmlFor="template-shared" className="text-sm font-medium text-lsc-dark dark:text-earth-300">Shared with all staff</label>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="block text-sm font-medium text-lsc-dark dark:text-earth-300">Line Items</label>
                  <button type="button" onClick={addTemplateItem} className="flex items-center gap-1 px-3 py-1 text-sm bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"><Plus aria-hidden="true" className="w-3 h-3" />Add Row</button>
                </div>
                {templateForm.template_items.length === 0 ? (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 py-2">No line items yet. Click "Add Row" to start.</p>
                ) : (
                  <div className="overflow-x-auto border border-lsc-border dark:border-earth-700 rounded-xl">
                    <table className="w-full text-sm">
                      <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
                        <tr>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Title</th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Author</th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">ISBN</th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 w-20">Qty</th>
                          <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 w-24">Price</th>
                          <th className="px-3 py-2 w-10"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                        {templateForm.template_items.map((item, idx) => (
                          <tr key={idx}>
                            <td className="px-2 py-1"><input type="text" value={item.title} onChange={(e) => updateTemplateItem(idx, "title", e.target.value)} className="w-full px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm" placeholder={t('placeholder.templatesTab.title')} /></td>
                            <td className="px-2 py-1"><input type="text" value={item.author || ""} onChange={(e) => updateTemplateItem(idx, "author", e.target.value)} className="w-full px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm" placeholder={t('placeholder.acquisition.author')} /></td>
                            <td className="px-2 py-1"><input type="text" value={item.isbn || ""} onChange={(e) => updateTemplateItem(idx, "isbn", e.target.value)} className="w-full px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm" placeholder={t('placeholder.acquisition.isbn')} /></td>
                            <td className="px-2 py-1"><input type="number" min={1} value={item.quantity} onChange={(e) => updateTemplateItem(idx, "quantity", parseInt(e.target.value) || 1)} className="w-full px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm" /></td>
                            <td className="px-2 py-1"><input type="number" min={0} step="0.01" value={item.unit_price ?? 0} onChange={(e) => updateTemplateItem(idx, "unit_price", parseFloat(e.target.value) || 0)} className="w-full px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm" /></td>
                            <td className="px-2 py-1"><button type="button" onClick={() => removeTemplateItem(idx)} className="p-1 text-status-danger-500 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded" aria-label={t('aria.templatesTab.removeRow')}><Trash2 aria-hidden="true" className="w-3.5 h-3.5" /></button></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
                <button type="button" onClick={() => setShowTemplateForm(false)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl font-medium">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2"><Check aria-hidden="true" className="w-4 h-4" />Save</button>
              </div>
            </form>
          </div>
        </ModalBackdrop>
      )}

      {showCreatePOFromTemplate && selectedTemplateForPO && (
        <ModalBackdrop onClose={() => setShowCreatePOFromTemplate(false)} title="Create PO from Template">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
            <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
              <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Create PO from Template</h2>
              <button onClick={() => setShowCreatePOFromTemplate(false)} className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark rounded-xl" aria-label={t('aria.authModals.close')}><X aria-hidden="true" className="w-5 h-5" /></button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Creating PO from template "<span className="font-medium">{selectedTemplateForPO.name}</span>" ({selectedTemplateForPO.item_count} items)
              </p>
              <div>
                <label htmlFor={templatePOVendorSelectId} className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">Vendor (override)</label>
                <select id={templatePOVendorSelectId} value={templatePOVendorId ?? ""} onChange={(e) => setTemplatePOVendorId(e.target.value ? parseInt(e.target.value) : null)} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream">
                  <option value="">Use template default</option>
                  {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor={templatePOFundSelectId} className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">Fund (override)</label>
                <select id={templatePOFundSelectId} value={templatePOFundId ?? ""} onChange={(e) => setTemplatePOFundId(e.target.value ? parseInt(e.target.value) : null)} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream">
                  <option value="">Use template default</option>
                  {funds.map(f => <option key={f.id} value={f.id}>{f.name} (Available: {formatMoney(f.available_amount)})</option>)}
                </select>
              </div>
              {/* Live fund-spend preview. Resolves the effective fund: explicit override
                  (templatePOFundId) wins, otherwise falls back to the template's default. */}
              <FundSpendPreview
                fund={funds.find(f => f.id === (templatePOFundId ?? selectedTemplateForPO.fund_id)) || null}
                newAmount={(selectedTemplateForPO.template_items || []).reduce(
                  (sum, item) => sum + (Number(item.quantity) || 0) * (Number(item.unit_price) || 0),
                  0
                )}
                formatMoney={formatMoney}
              />
              <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
                <button type="button" onClick={() => setShowCreatePOFromTemplate(false)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl font-medium">Cancel</button>
                <button onClick={handleConfirmCreatePOFromTemplate} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2"><Copy aria-hidden="true" className="w-4 h-4" />Create PO</button>
              </div>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {showSaveAsTemplate && (
        <ModalBackdrop onClose={() => setShowSaveAsTemplate(false)} title="Save as Template">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
            <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
              <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Save as Template</h2>
              <button onClick={() => setShowSaveAsTemplate(false)} className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark rounded-xl" aria-label={t('aria.authModals.close')}><X aria-hidden="true" className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleConfirmSaveAsTemplate} className="p-6 space-y-4">
              <div>
                <label htmlFor={saveTemplateNameId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Template Name *</label>
                <input id={saveTemplateNameId} type="text" value={saveTemplateForm.name} onChange={(e) => setSaveTemplateForm({ ...saveTemplateForm, name: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required />
              </div>
              <div>
                <label htmlFor={saveTemplateDescriptionId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Description</label>
                <input id={saveTemplateDescriptionId} type="text" value={saveTemplateForm.description} onChange={(e) => setSaveTemplateForm({ ...saveTemplateForm, description: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="save-template-shared" checked={saveTemplateForm.is_shared} onChange={(e) => setSaveTemplateForm({ ...saveTemplateForm, is_shared: e.target.checked })} className="w-4 h-4 rounded border-lsc-border text-lsc-rose" />
                <label htmlFor="save-template-shared" className="text-sm font-medium text-lsc-dark dark:text-earth-300">Shared with all staff</label>
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
                <button type="button" onClick={() => setShowSaveAsTemplate(false)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl font-medium">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2"><Save aria-hidden="true" className="w-4 h-4" />Save Template</button>
              </div>
            </form>
          </div>
        </ModalBackdrop>
      )}
      <ConfirmDialog
        isOpen={confirmOpen}
        title="Delete this template?"
        message="This cannot be undone."
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={() => { pendingAction?.(); setConfirmOpen(false); setPendingAction(null) }}
        onCancel={() => { setConfirmOpen(false); setPendingAction(null) }}
      />
    </>
  )
}
