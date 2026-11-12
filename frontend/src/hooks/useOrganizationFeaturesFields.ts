/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'

export interface UseOrganizationFeaturesFieldsResult<T> {
  value: T
  setValue: React.Dispatch<React.SetStateAction<T>>
  setField: <K extends keyof T>(field: K, fieldValue: T[K]) => void
  loading: boolean
  saving: boolean
  save: (reason?: string) => Promise<void>
  refresh: () => Promise<void>
}

export function useOrganizationFeaturesFields<T extends Record<string, unknown>>(
  defaults: T,
  options?: { successMessage?: string; errorMessage?: string; defaultReason?: string },
): UseOrganizationFeaturesFieldsResult<T> {
  const { features, loading, refetch } = useOrganizationFeatures()
  const [value, setValueRaw] = useState<T>(defaults)
  const [saving, setSaving] = useState(false)
  // The features context re-polls every 30s (live demo responsiveness). Each
  // poll produces a new `features` object, which used to re-run the hydration
  // effect below and silently wipe the user's unsaved edits mid-form (and the
  // poll's loading flip unmounted consumers gating on `loading`). Track
  // whether the user has edited anything; only hydrate from server state when
  // the form is pristine. save() and refresh() reset the flag so post-save
  // and Discard rehydration still work.
  const dirtyRef = useRef(false)

  useEffect(() => {
    if (!features) return
    if (dirtyRef.current) return
    const picked = {} as T
    ;(Object.keys(defaults) as Array<keyof T>).forEach((key) => {
      const fromFeatures = (features as unknown as Record<string, unknown>)[key as string]
      picked[key] = (fromFeatures !== undefined ? (fromFeatures as T[keyof T]) : defaults[key])
    })
    setValueRaw(picked)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [features])

  const setValue = useCallback<React.Dispatch<React.SetStateAction<T>>>((update) => {
    dirtyRef.current = true
    setValueRaw(update)
  }, [])

  const setField = useCallback(
    <K extends keyof T>(field: K, fieldValue: T[K]) => {
      dirtyRef.current = true
      setValueRaw((prev) => ({ ...prev, [field]: fieldValue }))
    },
    [],
  )

  const save = useCallback(
    async (reason?: string) => {
      try {
        setSaving(true)
        // PATCH only the fields whose value differs from the server's current
        // state. Sending the whole form state caused a mass-flip incident
        // (2026-05-21): callers seed defaults like `{flag_key: false}` for
        // every registry entry, and any field whose value never matched
        // server state during a save -- via stale hydration, partial GET
        // response, or registry/schema drift -- got persisted as false.
        // Diffing against `features` matches the backend's exclude_unset
        // semantics and lets a save touch only what the user changed.
        const payload: Record<string, unknown> = {}
        if (features) {
          const serverState = features as unknown as Record<string, unknown>
          ;(Object.keys(value) as Array<keyof T>).forEach((key) => {
            const k = key as string
            if (k in serverState && value[key] !== serverState[k]) {
              payload[k] = value[key]
            }
          })
        }
        const hasChanges = Object.keys(payload).length > 0
        if (reason || options?.defaultReason) {
          payload.reason = reason || options?.defaultReason
        }
        if (!hasChanges) {
          toast.success(options?.successMessage || 'No changes to save')
          return
        }
        await api.patch(`${API_BASE}/organization-features`, payload)
        dirtyRef.current = false
        await refetch()
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
    [value, features, refetch, options],
  )

  const refresh = useCallback(async () => {
    // Discard: drop local edits and rehydrate from the next fetch.
    dirtyRef.current = false
    await refetch()
  }, [refetch])

  // Initial load only: once features exist, background polls must not flip
  // consumers (which gate on `loading`) back into their unmounted state.
  return { value, setValue, setField, loading: loading && features === null, saving, save, refresh }
}
