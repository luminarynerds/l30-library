/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Building2,
  Plus,
  Edit2,
  X,
  Loader2,
  Check,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  listConsortiums,
  getConsortium,
  createConsortium,
  updateConsortium,
  type Consortium,
  type ConsortiumCreate,
  type ConsortiumDetail,
} from '../../../api/consortium-api'
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

function ConsortiumsTab({
  token,
  onSelectConsortium,
}: {
  token: string | null
  onSelectConsortium: (consortium: ConsortiumDetail) => void
}) {
  const [consortiums, setConsortiums] = useState<Consortium[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formData, setFormData] = useState<ConsortiumCreate>({
    code: '',
    name: '',
    legal_name: '',
    email: '',
    phone: '',
    website: '',
    address_line1: '',
    city: '',
    state: '',
    zip_code: '',
  })

  const loadConsortiums = useCallback(async () => {
    try {
      setLoading(true)
      const data = await listConsortiums(false)
      setConsortiums(data)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.admin.failedToLoadConsortiums'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadConsortiums()
  }, [loadConsortiums])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return

    setIsSubmitting(true)
    try {
      if (editingId) {
        await updateConsortium(token, editingId, formData)
        toast.success(t('toast.admin.consortiumUpdated'))
      } else {
        await createConsortium(token, formData)
        toast.success(t('toast.admin.consortiumCreated'))
      }
      setShowForm(false)
      setEditingId(null)
      setFormData({ code: '', name: '' })
      loadConsortiums()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.admin.failedToSaveConsortium'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEdit = async (consortium: Consortium) => {
    setFormData({
      code: consortium.code,
      name: consortium.name,
      legal_name: consortium.legal_name || '',
      email: consortium.email || '',
      phone: consortium.phone || '',
      website: consortium.website || '',
      address_line1: consortium.address_line1 || '',
      city: consortium.city || '',
      state: consortium.state || '',
      zip_code: consortium.zip_code || '',
    })
    setEditingId(consortium.id)
    setShowForm(true)
  }

  const handleViewDetails = async (consortiumId: number) => {
    try {
      const details = await getConsortium(consortiumId)
      onSelectConsortium(details)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.admin.failedToLoadConsortiumDetails'))
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Library Consortiums
        </h2>
        <button
          onClick={() => {
            setFormData({ code: '', name: '' })
            setEditingId(null)
            setShowForm(true)
          }}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors"
        >
          <Plus className="w-5 h-5" />
          New Consortium
        </button>
      </div>

      {consortiums.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-12 text-center">
          <Building2 className="w-16 h-16 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            No consortiums yet
          </h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
            Create your first library consortium to enable shared resources between libraries.
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors"
          >
            Create Consortium
          </button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {consortiums.map((consortium) => (
            <div
              key={consortium.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                    {consortium.name}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Code: {consortium.code}
                  </p>
                </div>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    consortium.is_active
                      ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400'
                      : 'bg-earth-100 dark:bg-earth-900/30 text-lsc-dark/70 dark:text-lsc-cream/70'
                  }`}
                >
                  {consortium.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              {consortium.city && consortium.state && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  {consortium.city}, {consortium.state}
                </p>
              )}
              <div className="flex gap-2">
                <button
                  onClick={() => handleViewDetails(consortium.id)}
                  className="flex-1 px-3 py-2 text-sm font-medium text-lsc-rose hover:bg-lsc-rose/10 rounded-lg transition-colors"
                >
                  View Details
                </button>
                <button
                  onClick={() => handleEdit(consortium)}
                  className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
                  aria-label={t('aria.admin.editConsortium')}
                >
                  <Edit2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <ModalBackdrop onClose={() => setShowForm(false)} title={editingId ? "Edit Consortium" : "New Consortium"}>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-lsc-border dark:border-earth-700">
              <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {editingId ? 'Edit Consortium' : 'New Consortium'}
              </h2>
              <button
                onClick={() => setShowForm(false)}
                className="p-1 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-full"
              >
                <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Code *
                  </label>
                  <input
                    type="text"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    disabled={!!editingId}
                    className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream disabled:opacity-50"
                    required
                    maxLength={20}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Name *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                    required
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Legal Name
                </label>
                <input
                  type="text"
                  value={formData.legal_name || ''}
                  onChange={(e) => setFormData({ ...formData, legal_name: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Email
                  </label>
                  <input
                    type="email"
                    value={formData.email || ''}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Phone
                  </label>
                  <input
                    type="tel"
                    value={formData.phone || ''}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Website
                </label>
                <input
                  type="url"
                  value={formData.website || ''}
                  onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  placeholder={t('placeholder.admin.https')}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Address
                </label>
                <input
                  type="text"
                  value={formData.address_line1 || ''}
                  onChange={(e) => setFormData({ ...formData, address_line1: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    City
                  </label>
                  <input
                    type="text"
                    value={formData.city || ''}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    State
                  </label>
                  <input
                    type="text"
                    value={formData.state || ''}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value.toUpperCase() })}
                    className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                    maxLength={2}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    ZIP
                  </label>
                  <input
                    type="text"
                    value={formData.zip_code || ''}
                    onChange={(e) => setFormData({ ...formData, zip_code: e.target.value })}
                    className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  disabled={isSubmitting}
                  className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  {isSubmitting ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </ModalBackdrop>
      )}
    </div>
  )
}

export default ConsortiumsTab
