/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import Modal from '../../components/ui/Modal'
import {
  createSubscription,
  updateSubscription,
  type DatabaseSubscription,
  type DatabaseVendor,
  type CreateSubscriptionRequest,
} from '../../api/databases-api'
import { CATEGORY_OPTIONS, inputClasses, labelClasses } from './databases-data'
import type { SubFormState } from './types'

interface EditSubscriptionModalProps {
  isOpen: boolean
  onClose: () => void
  subscription: DatabaseSubscription | null
  vendors: DatabaseVendor[] | undefined
}

function getInitialFormState(sub: DatabaseSubscription | null): SubFormState {
  if (sub) {
    return {
      name: sub.name,
      category: sub.category,
      vendor_id: sub.vendor_id != null ? String(sub.vendor_id) : '',
      access_url: sub.access_url,
      subscription_start: sub.subscription_start.slice(0, 10),
      subscription_end: sub.subscription_end.slice(0, 10),
      annual_cost: sub.annual_cost ?? '',
      is_active: sub.is_active,
      is_featured: sub.is_featured,
      notes: sub.notes ?? '',
    }
  }
  return {
    name: '',
    category: 'general_reference',
    vendor_id: '',
    access_url: '',
    subscription_start: new Date().toISOString().slice(0, 10),
    subscription_end: '',
    annual_cost: '',
    is_active: true,
    is_featured: false,
    notes: '',
  }
}

export function EditSubscriptionModal({
  isOpen,
  onClose,
  subscription,
  vendors,
}: EditSubscriptionModalProps): React.ReactElement | null {
  const queryClient = useQueryClient()
  const isEditMode = subscription !== null
  const [form, setForm] = useState<SubFormState>(() => getInitialFormState(subscription))

  const [prevSub, setPrevSub] = useState<DatabaseSubscription | null>(subscription)
  if (subscription !== prevSub) {
    setPrevSub(subscription)
    setForm(getInitialFormState(subscription))
  }

  const saveMutation = useMutation({
    mutationFn: (data: Partial<CreateSubscriptionRequest>) => {
      if (isEditMode) {
        return updateSubscription(subscription.id, data)
      }
      return createSubscription(data as CreateSubscriptionRequest)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['database-subscriptions'] })
      queryClient.invalidateQueries({ queryKey: ['database-dashboard'] })
      toast.success(isEditMode ? 'Subscription updated' : 'Subscription created')
      onClose()
    },
    onError: () => {
      toast.error(isEditMode ? 'Failed to update subscription' : 'Failed to create subscription')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data: Partial<CreateSubscriptionRequest> = {
      name: form.name,
      category: form.category,
      access_url: form.access_url,
      subscription_start: form.subscription_start,
      subscription_end: form.subscription_end,
      is_active: form.is_active,
      is_featured: form.is_featured,
      ...(form.vendor_id ? { vendor_id: Number(form.vendor_id) } : {}),
      ...(form.annual_cost ? { annual_cost: form.annual_cost } : {}),
      ...(form.notes ? { notes: form.notes } : {}),
    }
    saveMutation.mutate(data)
  }

  const update = (field: keyof SubFormState, value: string | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditMode ? `Edit ${subscription.name}` : 'Add Subscription'}
      size="xl"
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:hover:bg-earth-700"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="sub-form"
            disabled={saveMutation.isPending}
            className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-lg disabled:opacity-50"
          >
            {saveMutation.isPending ? 'Saving...' : isEditMode ? 'Save Changes' : 'Create'}
          </button>
        </>
      }
    >
      <form id="sub-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="sub-name" className={labelClasses}>
            Name *
          </label>
          <input
            id="sub-name"
            type="text"
            required
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            className={inputClasses}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="sub-category" className={labelClasses}>
              Category
            </label>
            <select
              id="sub-category"
              value={form.category}
              onChange={(e) => update('category', e.target.value)}
              className={inputClasses}
            >
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="sub-vendor" className={labelClasses}>
              Vendor
            </label>
            <select
              id="sub-vendor"
              value={form.vendor_id}
              onChange={(e) => update('vendor_id', e.target.value)}
              className={inputClasses}
            >
              <option value="">No vendor</option>
              {vendors?.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="sub-url" className={labelClasses}>
            Access URL *
          </label>
          <input
            id="sub-url"
            type="url"
            required
            value={form.access_url}
            onChange={(e) => update('access_url', e.target.value)}
            className={inputClasses}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="sub-start" className={labelClasses}>
              Subscription Start *
            </label>
            <input
              id="sub-start"
              type="date"
              required
              value={form.subscription_start}
              onChange={(e) => update('subscription_start', e.target.value)}
              className={inputClasses}
            />
          </div>

          <div>
            <label htmlFor="sub-end" className={labelClasses}>
              Subscription End *
            </label>
            <input
              id="sub-end"
              type="date"
              required
              value={form.subscription_end}
              onChange={(e) => update('subscription_end', e.target.value)}
              className={inputClasses}
            />
          </div>
        </div>

        <div>
          <label htmlFor="sub-cost" className={labelClasses}>
            Annual Cost
          </label>
          <input
            id="sub-cost"
            type="text"
            inputMode="decimal"
            placeholder="0.00"
            value={form.annual_cost}
            onChange={(e) => update('annual_cost', e.target.value)}
            className={inputClasses}
          />
        </div>

        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => update('is_active', e.target.checked)}
              className="rounded border-lsc-border dark:border-earth-700"
            />
            Active
          </label>
          <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <input
              type="checkbox"
              checked={form.is_featured}
              onChange={(e) => update('is_featured', e.target.checked)}
              className="rounded border-lsc-border dark:border-earth-700"
            />
            Featured
          </label>
        </div>

        <div>
          <label htmlFor="sub-notes" className={labelClasses}>
            Notes
          </label>
          <textarea
            id="sub-notes"
            rows={3}
            value={form.notes}
            onChange={(e) => update('notes', e.target.value)}
            className={inputClasses}
          />
        </div>
      </form>
    </Modal>
  )
}
