/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import { Cpu, Loader2, Plus, FileCheck, XCircle } from "lucide-react"
import toast from "react-hot-toast"
import { getStatusColor, formatResourceType, formatStatus, type ResourceSummary } from "@/api/domains/makerspace"
import { fetchApi } from "@/lib/api-client"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { t } from '@/i18n'

const EMPTY_FORM = {
  name: '', resource_type: 'printer_3d', location: '', manufacturer: '', model: '', hourly_cost: 0, requires_certification: true,
}

export default function StaffMakerspacePage(): React.ReactElement {
  const { user, token, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error("Staff access required")
      navigate("/account")
    }
  }, [authLoading, user, navigate])

  const { data, isLoading } = useQuery({
    queryKey: ["staff-makerspace-resources"],
    queryFn: async () => {
      if (!token) return { items: [] as ResourceSummary[], total: 0, page: 1, per_page: 50 }
      return await fetchApi<{ items: ResourceSummary[]; total: number; page: number; per_page: number }>(
        "/staff/makerspace/resources?per_page=50",
        { token }
      )
    },
    enabled: !!token,
  })

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await fetchApi('/staff/makerspace/resources', { method: 'POST', body: form, ...(token ? { token } : {}) })
      toast.success('Equipment added')
      setShowModal(false)
      setForm(EMPTY_FORM)
      queryClient.invalidateQueries({ queryKey: ['staff-makerspace-resources'] })
    } catch {
      toast.error('Failed to add equipment')
    } finally {
      setSaving(false)
    }
  }

  if (!user || user.role === "patron") return <></>

  const items = data?.items ?? []

  return (
    <AdminShell title="Equipment Inventory">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <Cpu className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Equipment Inventory
            </h1>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm"
          >
            <Plus className="w-4 h-4" /> Add Equipment
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : items.length > 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((resource) => (
              <div
                key={resource.id}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700"
              >
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">{resource.name}</h4>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(resource.status)}`}>
                    {formatStatus(resource.status)}
                  </span>
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  {formatResourceType(resource.resource_type)}
                </p>
                {resource.location && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{resource.location}</p>
                )}
                {resource.requires_certification && (
                  <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700">
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
                      <FileCheck className="w-3 h-3" /> Cert required
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
            <Cpu className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No equipment yet. Add your first item.</p>
          </div>
        )}
      </div>

      {showModal && (
        <ModalBackdrop onClose={() => setShowModal(false)} title="Add Equipment">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
            <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Add Equipment</h3>
              <button onClick={() => setShowModal(false)} aria-label={t('aria.staffMakerspacePage.closeModal', 'Close')} className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream">
                <XCircle className="w-5 h-5" aria-hidden="true" />
              </button>
            </div>
            <form onSubmit={handleAdd} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Name *</label>
                <input type="text" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" placeholder="Prusa i3 MK3S+" />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Type *</label>
                <select required value={form.resource_type} onChange={(e) => setForm({ ...form, resource_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream">
                  <option value="printer_3d">3D Printer</option>
                  <option value="laser_cutter">Laser Cutter</option>
                  <option value="cnc_router">CNC Router</option>
                  <option value="vinyl_cutter">Vinyl Cutter</option>
                  <option value="embroidery_machine">Embroidery Machine</option>
                  <option value="sewing_machine">Sewing Machine</option>
                  <option value="soldering_station">Soldering Station</option>
                  <option value="electronics_workbench">Electronics Workbench</option>
                  <option value="recording_studio">Recording Studio</option>
                  <option value="vr_station">VR Station</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Location</label>
                  <input type="text" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" placeholder="Makerspace" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Hourly cost</label>
                  <input type="number" min="0" step="0.50" value={form.hourly_cost} onChange={(e) => setForm({ ...form, hourly_cost: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Manufacturer</label>
                  <input type="text" value={form.manufacturer} onChange={(e) => setForm({ ...form, manufacturer: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Model</label>
                  <input type="text" value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" />
                </div>
              </div>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={form.requires_certification} onChange={(e) => setForm({ ...form, requires_certification: e.target.checked })}
                  className="rounded border-lsc-border dark:border-earth-600" />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Requires staff sign-off / certification</span>
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70">Cancel</button>
                <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50">
                  {saving ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Add Equipment'}
                </button>
              </div>
            </form>
          </div>
        </ModalBackdrop>
      )}
    </AdminShell>
  )
}
