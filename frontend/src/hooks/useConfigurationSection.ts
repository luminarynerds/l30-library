/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'

export interface ConfigurationSectionChange<T> {
  before: T[keyof T]
  after: T[keyof T]
}

export interface UseConfigurationSectionResult<T> {
  value: T
  initialValue: T
  setValue: React.Dispatch<React.SetStateAction<T>>
  setField: <K extends keyof T>(field: K, fieldValue: T[K]) => void
  loading: boolean
  saving: boolean
  dirty: boolean
  changedFields: Partial<Record<keyof T, ConfigurationSectionChange<T>>>
  save: (reason?: string, overridePayload?: Partial<Record<string, unknown>>) => Promise<void>
  reset: () => void
}

export function useConfigurationSection<T extends Record<string, unknown>>(
  key: string,
  defaults: T,
  options?: { successMessage?: string; errorMessage?: string; defaultReason?: string },
): UseConfigurationSectionResult<T> {
  const { features, loading, refetch } = useOrganizationFeatures()
  const [value, setValue] = useState<T>(defaults)
  const [initialValue, setInitialValue] = useState<T>(defaults)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!features?.configuration) return
    const stored = (features.configuration as Record<string, unknown>)[key] as
      | Partial<T>
      | undefined
    const hydrated = stored ? { ...defaults, ...stored } : defaults
    setValue(hydrated)
    setInitialValue(hydrated)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [features, key])

  const setField = useCallback(
    <K extends keyof T>(field: K, fieldValue: T[K]) => {
      setValue((prev) => ({ ...prev, [field]: fieldValue }))
    },
    [],
  )

  const changedFields = useMemo(() => {
    const changes: Partial<Record<keyof T, ConfigurationSectionChange<T>>> = {}
    for (const key of Object.keys(value) as Array<keyof T>) {
      if (value[key] !== initialValue[key]) {
        changes[key] = { before: initialValue[key], after: value[key] }
      }
    }
    return changes
  }, [value, initialValue])

  const dirty = Object.keys(changedFields).length > 0

  const save = useCallback(
    async (reason?: string, overridePayload?: Partial<Record<string, unknown>>) => {
      try {
        setSaving(true)
        const payload = {
          configuration: {
            ...((features?.configuration as Record<string, unknown>) || {}),
            [key]: value,
            ...(overridePayload || {}),
          },
          reason: reason || options?.defaultReason || `Admin update via ${key} settings UI`,
        }
        await api.patch(`${API_BASE}/organization-features`, payload)
        await refetch()
        setInitialValue(value)
        toast.success(options?.successMessage || 'Settings updated')
      } catch (error: unknown) {
        const err = error as { response?: { data?: { detail?: string } } }
        toast.error(
          err.response?.data?.detail ||
            options?.errorMessage ||
            'Failed to update settings',
        )
      } finally {
        setSaving(false)
      }
    },
    [features, key, value, refetch, options],
  )

  const reset = useCallback(() => {
    setValue(initialValue)
  }, [initialValue])

  return {
    value,
    initialValue,
    setValue,
    setField,
    loading,
    saving,
    dirty,
    changedFields,
    save,
    reset,
  }
}
