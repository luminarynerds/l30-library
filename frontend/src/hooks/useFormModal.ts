/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from 'react'

export interface UseFormModalOptions<T> {
  /** Initial form data */
  initialData: T
  /** Custom validation function - returns error map */
  onValidate?: (data: T) => Record<string, string>
  /** Success callback after form submission */
  onSuccess?: () => void
}

export interface UseFormModalReturn<T> {
  /** Current form data */
  formData: T
  /** Current form errors */
  errors: Record<string, string>
  /** Loading state during submission */
  loading: boolean
  /** Validate form - returns true if valid */
  validateForm: () => boolean
  /** Handle input change with error clearing */
  handleChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void
  /** Handle form submission */
  handleSubmit: (callback: (data: T) => Promise<void>) => (e: React.FormEvent) => Promise<void>
  /** Reset form to initial state */
  resetForm: () => void
  /** Set form data externally */
  setFormData: (data: T | ((prev: T) => T)) => void
  /** Set field error manually */
  setFieldError: (field: string, error: string) => void
  /** Clear a specific field error */
  clearFieldError: (field: string) => void
  /** Clear all errors */
  clearErrors: () => void
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function useFormModal<T extends Record<string, any>>({
  initialData,
  onValidate,
  onSuccess,
}: UseFormModalOptions<T>): UseFormModalReturn<T> {
  const [formData, setFormDataState] = useState<T>(initialData)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)

  const validateForm = useCallback((): boolean => {
    const newErrors = onValidate?.(formData) || {}
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }, [formData, onValidate])

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      const { name, type } = e.target
      const value =
        type === 'checkbox'
          ? (e.target as HTMLInputElement).checked
          : type === 'number'
            ? parseFloat(e.target.value)
            : e.target.value

      setFormDataState((prev) => ({ ...prev, [name]: value }))

      // Clear field error when user starts editing
      if (errors[name]) {
        setErrors((prev) => {
          const newErrors = { ...prev }
          delete newErrors[name]
          return newErrors
        })
      }
    },
    [errors]
  )

  const handleSubmit = useCallback(
    (callback: (data: T) => Promise<void>) => async (e: React.FormEvent) => {
      e.preventDefault()

      if (!validateForm()) return

      setLoading(true)
      try {
        await callback(formData)
        onSuccess?.()
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : "Something didn't work as expected. Please try again."
        setErrors((prev) => ({ ...prev, submit: message }))
      } finally {
        setLoading(false)
      }
    },
    [formData, validateForm, onSuccess]
  )

  const resetForm = useCallback(() => {
    setFormDataState(initialData)
    setErrors({})
  }, [initialData])

  const setFormData = useCallback((data: T | ((prev: T) => T)) => {
    setFormDataState(data)
  }, [])

  const setFieldError = useCallback((field: string, error: string) => {
    setErrors((prev) => ({ ...prev, [field]: error }))
  }, [])

  const clearFieldError = useCallback((field: string) => {
    setErrors((prev) => {
      const newErrors = { ...prev }
      delete newErrors[field]
      return newErrors
    })
  }, [])

  const clearErrors = useCallback(() => {
    setErrors({})
  }, [])

  return {
    formData,
    errors,
    loading,
    validateForm,
    handleChange,
    handleSubmit,
    resetForm,
    setFormData,
    setFieldError,
    clearFieldError,
    clearErrors,
  }
}
