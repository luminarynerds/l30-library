/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from "react"
import { Loader2, Copy, Check } from "lucide-react"
import { staffCreatePatron, type StaffCreatePatronData, type StaffCreatePatronResponse } from "../../api/staff-api/patrons"
import { useAuth } from "../../contexts/AuthContext"
import { useFormModal } from "../../hooks/useFormModal"
import { Modal } from "../ui/Modal"
import toast from "react-hot-toast"

interface AddPatronModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function AddPatronModal({
  isOpen,
  onClose,
  onSuccess,
}: AddPatronModalProps): React.ReactElement | null {
  const { token } = useAuth()
  const [createdPatron, setCreatedPatron] = useState<StaffCreatePatronResponse | null>(null)
  const [copied, setCopied] = useState(false)

  const form = useFormModal<StaffCreatePatronData>({
    initialData: {
      first_name: "",
      last_name: "",
      email: "",
      phone: "",
      address: "",
    },
    onValidate: (data) => {
      const errors: Record<string, string> = {}
      if (!data.first_name.trim()) errors.first_name = "First name is required"
      if (!data.last_name.trim()) errors.last_name = "Last name is required"
      return errors
    },
    onSuccess: () => {},
  })

  if (!isOpen) return null

  const handleFormSubmit = form.handleSubmit(async (data) => {
    if (!token) throw new Error("Not authenticated")
    const cleaned: StaffCreatePatronData = {
      first_name: data.first_name.trim(),
      last_name: data.last_name.trim(),
    }
    if (data.email?.trim()) cleaned.email = data.email.trim()
    if (data.phone?.trim()) cleaned.phone = data.phone.trim()
    if (data.address?.trim()) cleaned.address = data.address.trim()

    const result = await staffCreatePatron(token, cleaned)
    setCreatedPatron(result)
    toast.success(`Patron ${result.first_name} ${result.last_name} created`)
  })

  const handleClose = () => {
    if (createdPatron) {
      form.resetForm()
      setCreatedPatron(null)
      setCopied(false)
      onSuccess()
    }
    onClose()
  }

  const handleCopyPassword = async () => {
    if (createdPatron?.temporary_password) {
      await navigator.clipboard.writeText(createdPatron.temporary_password)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Success view: show card number and temp password
  if (createdPatron) {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title="Patron Created" size="md">
        <div className="space-y-4">
          <div className="p-4 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-lg">
            <p className="font-semibold text-status-success-800 dark:text-status-success-300">
              {createdPatron.first_name} {createdPatron.last_name}
            </p>
          </div>

          <div className="space-y-3">
            <div>
              <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Library Card</span>
              <p className="font-mono text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                {createdPatron.library_card}
              </p>
            </div>

            {createdPatron.temporary_password && (
              <div>
                <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Temporary Password</span>
                <div className="flex items-center gap-2 mt-1">
                  <code className="flex-1 px-3 py-2 bg-lsc-cream/50 dark:bg-earth-800 rounded font-mono text-sm">
                    {createdPatron.temporary_password}
                  </code>
                  <button
                    type="button"
                    onClick={handleCopyPassword}
                    className="p-2 rounded-lg hover:bg-lsc-cream/50 dark:hover:bg-earth-700 transition-colors"
                    aria-label="Copy password"
                  >
                    {copied ? <Check className="w-4 h-4 text-status-success-600" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  Give this to the patron. They will be asked to change it on first login.
                </p>
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={handleClose}
              className="w-full px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      </Modal>
    )
  }

  // Form view
  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Register New Patron" size="md">
      <form onSubmit={handleFormSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="patron-first-name" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
              First Name <span className="text-status-danger-600">*</span>
            </label>
            <input
              id="patron-first-name"
              type="text"
              name="first_name"
              value={form.formData.first_name}
              onChange={form.handleChange}
              autoFocus
              maxLength={100}
              className={`w-full px-3 py-2 rounded-lg border bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors ${
                form.errors.first_name ? "border-status-danger-500" : "border-lsc-border dark:border-earth-700"
              }`}
            />
            {form.errors.first_name && (
              <p className="text-status-danger-600 text-sm mt-1">{form.errors.first_name}</p>
            )}
          </div>
          <div>
            <label htmlFor="patron-last-name" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
              Last Name <span className="text-status-danger-600">*</span>
            </label>
            <input
              id="patron-last-name"
              type="text"
              name="last_name"
              value={form.formData.last_name}
              onChange={form.handleChange}
              maxLength={100}
              className={`w-full px-3 py-2 rounded-lg border bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors ${
                form.errors.last_name ? "border-status-danger-500" : "border-lsc-border dark:border-earth-700"
              }`}
            />
            {form.errors.last_name && (
              <p className="text-status-danger-600 text-sm mt-1">{form.errors.last_name}</p>
            )}
          </div>
        </div>

        <div>
          <label htmlFor="patron-email" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
            Email
          </label>
          <input
            id="patron-email"
            type="email"
            name="email"
            value={form.formData.email}
            onChange={form.handleChange}
            placeholder="Optional"
            className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
          />
        </div>

        <div>
          <label htmlFor="patron-phone" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
            Phone
          </label>
          <input
            id="patron-phone"
            type="tel"
            name="phone"
            value={form.formData.phone}
            onChange={form.handleChange}
            placeholder="Optional"
            className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
          />
        </div>

        <div>
          <label htmlFor="patron-address" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
            Address
          </label>
          <input
            id="patron-address"
            type="text"
            name="address"
            value={form.formData.address}
            onChange={form.handleChange}
            placeholder="Optional"
            className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-earth-700 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
          />
        </div>

        {form.errors.submit && (
          <div className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg">
            <p className="text-status-danger-700 dark:text-status-danger-400 text-sm">{form.errors.submit}</p>
          </div>
        )}

        <div className="flex gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
          <button
            type="button"
            onClick={handleClose}
            disabled={form.loading}
            className="flex-1 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700 transition-colors disabled:opacity-50 font-medium"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={form.loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors disabled:opacity-50 font-medium"
          >
            {form.loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            {form.loading ? "Creating..." : "Register Patron"}
          </button>
        </div>
      </form>
    </Modal>
  )
}
