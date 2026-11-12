/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import toast from "react-hot-toast"
import { Plus, Edit, Trash2, Loader2, Info, User, GripVertical } from "lucide-react"
import { AdminShell } from '../components/shells'
import ConfirmDialog from "../components/ConfirmDialog"
import { useAuth } from "../contexts/AuthContext"
import {
  getStaffBios,
  createStaffBio,
  updateStaffBio,
  deleteStaffBio,
  type StaffBio,
  type StaffBioCreate,
  type StaffBioUpdate,
} from "../api/domains/services/community-api"

const inputClass = "w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
const labelClass = "block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"

function StaffBioForm({
  bio,
  onSave,
  onCancel,
}: {
  bio?: StaffBio
  onSave: (data: StaffBioCreate | StaffBioUpdate) => Promise<void>
  onCancel: () => void
}) {
  const [staffName, setStaffName] = useState(bio?.staff_name || "")
  const [role, setRole] = useState(bio?.role || "")
  const [bioText, setBioText] = useState(bio?.bio || "")
  const [photoUrl, setPhotoUrl] = useState(bio?.photo_url || "")
  const [funFact, setFunFact] = useState(bio?.fun_fact || "")
  const [favoriteBook, setFavoriteBook] = useState(bio?.favorite_book || "")
  const [yearsOfService, setYearsOfService] = useState(bio?.years_of_service?.toString() || "")
  const [sortOrder, setSortOrder] = useState(bio?.sort_order?.toString() || "0")
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await onSave({
        staff_name: staffName,
        role,
        bio: bioText,
        photo_url: photoUrl || null,
        fun_fact: funFact || null,
        favorite_book: favoriteBook || null,
        years_of_service: yearsOfService ? parseInt(yearsOfService) : null,
        sort_order: parseInt(sortOrder) || 0,
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-6 mb-6 space-y-4">
      <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
        {bio ? "Edit Staff Bio" : "Add Staff Bio"}
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label htmlFor="bio-form-name" className={labelClass}>Name *</label>
          <input id="bio-form-name" type="text" value={staffName} onChange={e => setStaffName(e.target.value)} required className={inputClass} />
        </div>
        <div>
          <label htmlFor="bio-form-role" className={labelClass}>Role / Title *</label>
          <input id="bio-form-role" type="text" value={role} onChange={e => setRole(e.target.value)} required className={inputClass} placeholder="e.g. Library Director" />
        </div>
        <div>
          <label htmlFor="bio-form-photo-url" className={labelClass}>Photo URL</label>
          <input id="bio-form-photo-url" type="url" value={photoUrl} onChange={e => setPhotoUrl(e.target.value)} className={inputClass} placeholder="https://..." />
          <p className="mt-1 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">Square photos work best, hosted anywhere accessible (e.g., S3, Cloudinary).</p>
        </div>
        <div>
          <label htmlFor="bio-form-favorite-book" className={labelClass}>Favorite Book</label>
          <input id="bio-form-favorite-book" type="text" value={favoriteBook} onChange={e => setFavoriteBook(e.target.value)} className={inputClass} />
        </div>
        <div>
          <label htmlFor="bio-form-years-of-service" className={labelClass}>Years of Service</label>
          <input id="bio-form-years-of-service" type="number" value={yearsOfService} onChange={e => setYearsOfService(e.target.value)} className={inputClass} min="0" />
        </div>
        <div>
          <label htmlFor="bio-form-sort-order" className={labelClass}>Sort Order</label>
          <input id="bio-form-sort-order" type="number" value={sortOrder} onChange={e => setSortOrder(e.target.value)} className={inputClass} min="0" />
        </div>
      </div>
      <div>
        <label htmlFor="bio-form-bio" className={labelClass}>Bio *</label>
        <textarea id="bio-form-bio" value={bioText} onChange={e => setBioText(e.target.value)} required rows={3} className={inputClass} />
      </div>
      <div>
        <label htmlFor="bio-form-fun-fact" className={labelClass}>Fun Fact</label>
        <input id="bio-form-fun-fact" type="text" value={funFact} onChange={e => setFunFact(e.target.value)} className={inputClass} />
      </div>
      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onCancel} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700">
          Cancel
        </button>
        <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2">
          {saving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
          {bio ? "Save Changes" : "Add Staff Bio"}
        </button>
      </div>
    </form>
  )
}

export default function AdminAboutUsPage() {
  const { token } = useAuth()
  const [bios, setBios] = useState<StaffBio[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingBio, setEditingBio] = useState<StaffBio | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; name: string } | null>(null)

  const fetchBios = async () => {
    try {
      setLoading(true)
      const data = await getStaffBios()
      setBios(data)
    } catch (_err) {
      toast.error("Failed to load staff bios")
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    fetchBios()
  }, [])

  const handleCreate = async (data: StaffBioCreate | StaffBioUpdate) => {
    try {
      await createStaffBio(token!, data as StaffBioCreate)
      toast.success("Staff bio added")
      setShowForm(false)
      fetchBios()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to add staff bio")
    }
  }

  const handleUpdate = async (data: StaffBioUpdate) => {
    if (!editingBio) return
    try {
      await updateStaffBio(token!, editingBio.id, data)
      toast.success("Staff bio updated")
      setEditingBio(null)
      fetchBios()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to update staff bio")
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteStaffBio(token!, id)
      setDeleteConfirm(null)
      toast.success("Staff bio deleted")
      fetchBios()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to delete staff bio")
    }
  }

  return (
    <AdminShell
      title="Manage About Us"
      subtitle="Manage staff bios displayed on the public About Us page"
      icon={<Info className="w-7 h-7 text-lsc-rose" />}
      actions={
        !showForm && !editingBio ? (
          <button
            onClick={() => setShowForm(true)}
            className="bg-lsc-rose text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-lsc-rose/90"
          >
            <Plus className="w-5 h-5" />
            Add Staff Bio
          </button>
        ) : undefined
      }
    >
      {showForm && (
        <StaffBioForm onSave={handleCreate} onCancel={() => setShowForm(false)} />
      )}
      {editingBio && (
        <StaffBioForm bio={editingBio} onSave={handleUpdate} onCancel={() => setEditingBio(null)} />
      )}

      {loading ? (
        <div className="text-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin mx-auto text-lsc-rose" />
        </div>
      ) : bios.length === 0 ? (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          <User className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No staff bios yet. Add one to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {bios.map((bio) => (
            <div
              key={bio.id}
              className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-4 flex items-start gap-4"
            >
              <div className="flex-shrink-0 mt-1">
                <GripVertical className="w-4 h-4 text-lsc-dark/30 dark:text-lsc-cream/30" />
              </div>
              {bio.photo_url ? (
                <img
                  src={bio.photo_url}
                  alt={bio.staff_name}
                  className="w-12 h-12 rounded-full object-cover flex-shrink-0"
                />
              ) : (
                <div className="w-12 h-12 rounded-full bg-lsc-rose/10 flex items-center justify-center flex-shrink-0">
                  <User className="w-6 h-6 text-lsc-rose" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{bio.staff_name}</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                    {bio.role}
                  </span>
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 line-clamp-2">{bio.bio}</p>
                <div className="flex gap-4 mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {bio.favorite_book && <span>Fav book: {bio.favorite_book}</span>}
                  {bio.years_of_service != null && <span>{bio.years_of_service} yrs</span>}
                  <span>Order: {bio.sort_order}</span>
                </div>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                <button
                  onClick={() => { setEditingBio(bio); setShowForm(false) }}
                  className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/50 hover:text-lsc-rose"
                  title="Edit"
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setDeleteConfirm({ id: bio.id, name: bio.staff_name })}
                  className="p-2 rounded-lg hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 text-lsc-dark/70 dark:text-lsc-cream/50 hover:text-status-danger-600"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Delete Staff Bio"
        message={`Are you sure you want to delete "${deleteConfirm?.name}"? This cannot be undone.`}
        onConfirm={() => { if (deleteConfirm) handleDelete(deleteConfirm.id) }}
        onCancel={() => setDeleteConfirm(null)}
      />
    </AdminShell>
  )
}
