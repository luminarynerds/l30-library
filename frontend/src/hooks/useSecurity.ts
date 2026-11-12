/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Custom hook for managing security-related operations (password, sessions)
 */
import { useState, useCallback } from 'react'
import {
  changePassword,
  getSessions,
  revokeSession,
  revokeAllOtherSessions,
  Session,
} from '../api/api'
import toast from 'react-hot-toast'

export function useSessions(token: string | null) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(false)
  const [revokingId, setRevokingId] = useState<number | null>(null)
  const [revokingAll, setRevokingAll] = useState(false)

  const refresh = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const data = await getSessions(token)
      setSessions(data.sessions)
    } catch (_err) {
      toast.error("We're having trouble loading your active sessions. Please refresh the page.")
    } finally {
      setLoading(false)
    }
  }, [token])

  const revoke = useCallback(async (sessionId: number) => {
    if (!token) return
    setRevokingId(sessionId)
    try {
      await revokeSession(token, sessionId)
      toast.success('Session revoked successfully', { duration: 5000 })
      await refresh()
    } catch (_err) {
      toast.error("We couldn't revoke that session. Please try again.")
    } finally {
      setRevokingId(null)
    }
  }, [token, refresh])

  const revokeAllOthers = useCallback(async () => {
    if (!token) return
    setRevokingAll(true)
    try {
      const result = await revokeAllOtherSessions(token)
      toast.success(result.message, { duration: 5000 })
      await refresh()
    } catch (_err) {
      toast.error("We couldn't revoke those sessions. Please try again.")
    } finally {
      setRevokingAll(false)
    }
  }, [token, refresh])

  return { sessions, loading, revokingId, revokingAll, refresh, revoke, revokeAllOthers }
}

export interface PasswordFormData {
  currentPassword: string
  newPassword: string
  confirmPassword: string
}

export function validatePasswordChange(formData: PasswordFormData): string | null {
  if (formData.newPassword !== formData.confirmPassword) {
    return 'New passwords do not match'
  }
  if (formData.newPassword.length < 8) {
    return 'Password must be at least 8 characters long'
  }
  return null
}

export function usePasswordChange(token: string | null) {
  const [isChanging, setIsChanging] = useState(false)

  const change = useCallback(
    async (formData: PasswordFormData) => {
      if (!token) return false

      // Validate
      const error = validatePasswordChange(formData)
      if (error) {
        toast.error(error)
        return false
      }

      setIsChanging(true)
      try {
        await changePassword(token, formData.currentPassword, formData.newPassword)
        toast.success('Password changed successfully', { duration: 5000 })
        return true
      } catch (_err) {
        toast.error(_err instanceof Error ? _err.message : "We couldn't update your password. Please try again.")
        return false
      } finally {
        setIsChanging(false)
      }
    },
    [token]
  )

  return { isChanging, change }
}
