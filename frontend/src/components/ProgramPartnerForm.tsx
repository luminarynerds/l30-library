/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, type FormEvent } from "react"
import { useTranslation } from "@/i18n"
import type {
  EventProgramPartner,
  EventProgramPartnerCreate,
  EventProgramPartnerUpdate,
} from "@/api/domains/services/program-partners-api"

export interface ProgramPartnerFormProps {
  mode: "create" | "edit"
  initial?: EventProgramPartner | undefined
  onSubmit: (
    payload: EventProgramPartnerCreate | EventProgramPartnerUpdate,
  ) => Promise<void> | void
  onCancel: () => void
  isSubmitting?: boolean | undefined
}

interface FieldErrors {
  name?: string
  website?: string
  contact_email?: string
}

const URL_RE = /^https?:\/\/.+/i
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function ProgramPartnerForm({
  mode,
  initial,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: ProgramPartnerFormProps): React.ReactElement {
  const { t } = useTranslation()
  const [name, setName] = useState(initial?.name ?? "")
  const [website, setWebsite] = useState(initial?.website ?? "")
  const [contactEmail, setContactEmail] = useState(initial?.contact_email ?? "")
  const [contactPhone, setContactPhone] = useState(initial?.contact_phone ?? "")
  const [notes, setNotes] = useState(initial?.notes ?? "")
  const [isActive, setIsActive] = useState(initial?.is_active ?? true)
  const [errors, setErrors] = useState<FieldErrors>({})

  const validate = (): FieldErrors => {
    const next: FieldErrors = {}
    if (!name.trim()) {
      next.name = t("programPartners.form.errors.nameRequired", "Name is required")
    } else if (name.length > 200) {
      next.name = t("programPartners.form.errors.nameTooLong", "Name must be 200 characters or fewer")
    }
    if (website.trim() && !URL_RE.test(website.trim())) {
      next.website = t(
        "programPartners.form.errors.websiteInvalid",
        "Website must start with http:// or https://",
      )
    }
    if (contactEmail.trim() && !EMAIL_RE.test(contactEmail.trim())) {
      next.contact_email = t(
        "programPartners.form.errors.emailInvalid",
        "Enter a valid email address",
      )
    }
    return next
  }

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const found = validate()
    setErrors(found)
    if (Object.keys(found).length > 0) return

    const trimmedName = name.trim()
    const trimmedWebsite = website.trim()
    const trimmedEmail = contactEmail.trim()
    const trimmedPhone = contactPhone.trim()
    const trimmedNotes = notes.trim()

    if (mode === "create") {
      const payload: EventProgramPartnerCreate = {
        name: trimmedName,
        website: trimmedWebsite || null,
        contact_email: trimmedEmail || null,
        contact_phone: trimmedPhone || null,
        notes: trimmedNotes || null,
        is_active: true,
      }
      await onSubmit(payload)
    } else {
      const payload: EventProgramPartnerUpdate = {
        name: trimmedName,
        website: trimmedWebsite || null,
        contact_email: trimmedEmail || null,
        contact_phone: trimmedPhone || null,
        notes: trimmedNotes || null,
        is_active: isActive,
      }
      await onSubmit(payload)
    }
  }

  const inputClass =
    "w-full px-3 py-2 border rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
  const labelClass =
    "block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <div>
        <label htmlFor="program-partner-name" className={labelClass}>
          {t("programPartners.form.name", "Name")} <span aria-hidden="true">*</span>
        </label>
        <input
          id="program-partner-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={200}
          aria-invalid={errors.name ? true : undefined}
          aria-describedby={errors.name ? "program-partner-name-error" : undefined}
          className={`${inputClass} ${errors.name ? "border-status-danger-500" : "border-lsc-border dark:border-earth-700"}`}
        />
        {errors.name && (
          <p
            id="program-partner-name-error"
            className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400"
          >
            {errors.name}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="program-partner-website" className={labelClass}>
          {t("programPartners.form.website", "Website")}
        </label>
        <input
          id="program-partner-website"
          type="url"
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
          placeholder="https://example.org"
          maxLength={500}
          aria-invalid={errors.website ? true : undefined}
          aria-describedby={errors.website ? "program-partner-website-error" : undefined}
          className={`${inputClass} ${errors.website ? "border-status-danger-500" : "border-lsc-border dark:border-earth-700"}`}
        />
        {errors.website && (
          <p
            id="program-partner-website-error"
            className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400"
          >
            {errors.website}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="program-partner-email" className={labelClass}>
          {t("programPartners.form.contactEmail", "Contact email")}
        </label>
        <input
          id="program-partner-email"
          type="email"
          value={contactEmail}
          onChange={(e) => setContactEmail(e.target.value)}
          aria-invalid={errors.contact_email ? true : undefined}
          aria-describedby={errors.contact_email ? "program-partner-email-error" : undefined}
          className={`${inputClass} ${errors.contact_email ? "border-status-danger-500" : "border-lsc-border dark:border-earth-700"}`}
        />
        {errors.contact_email && (
          <p
            id="program-partner-email-error"
            className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400"
          >
            {errors.contact_email}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="program-partner-phone" className={labelClass}>
          {t("programPartners.form.contactPhone", "Contact phone")}
        </label>
        <input
          id="program-partner-phone"
          type="tel"
          value={contactPhone}
          onChange={(e) => setContactPhone(e.target.value)}
          maxLength={50}
          className={`${inputClass} border-lsc-border dark:border-earth-700`}
        />
      </div>

      <div>
        <label htmlFor="program-partner-notes" className={labelClass}>
          {t("programPartners.form.notes", "Notes")}
        </label>
        <textarea
          id="program-partner-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          className={`${inputClass} border-lsc-border dark:border-earth-700`}
        />
      </div>

      {mode === "edit" && (
        <div className="flex items-center gap-2">
          <input
            id="program-partner-active"
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="h-4 w-4"
          />
          <label htmlFor="program-partner-active" className="text-sm text-lsc-dark dark:text-lsc-cream">
            {t("programPartners.form.isActive", "Active")}
          </label>
        </div>
      )}

      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors disabled:opacity-50"
        >
          {t("programPartners.form.cancel", "Cancel")}
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:opacity-50 text-white rounded-xl transition-colors"
        >
          {isSubmitting
            ? t("programPartners.form.saving", "Saving...")
            : mode === "create"
              ? t("programPartners.form.create", "Create partner")
              : t("programPartners.form.save", "Save changes")}
        </button>
      </div>
    </form>
  )
}
