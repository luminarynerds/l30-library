/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useCallback, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  listSessions,
  listActiveSessions,
  startCheckInSession,
  endSession,
  getSession,
  getSessionResults,
  checkInItem,
  CheckInSession,
  CheckInResult,
} from "@/api/book-drop-api"
import toast from "react-hot-toast"
import { clean } from '@/lib/utils'

export interface SessionFormState {
  branch_location: string
  book_drop_id: number | undefined
  workstation_id: string
  backdate_to: string
}

const DEFAULT_SESSION_FORM: SessionFormState = {
  branch_location: "",
  book_drop_id: undefined,
  workstation_id: "",
  backdate_to: "",
}

export const sessionsQueryKey = ["book-drop-sessions"] as const
export const activeSessionsQueryKey = ["book-drop-active-sessions"] as const

export function useBookDropProcessing(token: string | null) {
  const queryClient = useQueryClient()
  const [currentSession, setCurrentSession] = useState<CheckInSession | null>(null)
  const [sessionResults, setSessionResults] = useState<CheckInResult[]>([])
  const [recentResults, setRecentResults] = useState<CheckInResult[]>([])
  const [barcodeInput, setBarcodeInput] = useState("")
  const [isProcessing, setIsProcessing] = useState(false)
  const [sessionForm, setSessionForm] = useState<SessionFormState>(DEFAULT_SESSION_FORM)

  const sessionsQuery = useQuery({
    queryKey: sessionsQueryKey,
    queryFn: () => listSessions(token!, { limit: 50 }),
    enabled: !!token,
  })

  const activeSessionsQuery = useQuery({
    queryKey: activeSessionsQueryKey,
    queryFn: () => listActiveSessions(token!),
    enabled: !!token,
  })

  const invalidateSessions = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: sessionsQueryKey })
    queryClient.invalidateQueries({ queryKey: activeSessionsQueryKey })
  }, [queryClient])

  const startMutation = useMutation({
    mutationFn: (form: SessionFormState) =>
      startCheckInSession(token!, clean({
        branch_location: form.branch_location,
        book_drop_id: form.book_drop_id,
        ...(form.workstation_id ? { workstation_id: form.workstation_id } : {}),
        ...(form.backdate_to ? { backdate_to: form.backdate_to } : {}),
      })),
    onSuccess: (session) => {
      toast.success(`Session ${session.session_code} started`)
      setCurrentSession(session)
      setSessionForm(DEFAULT_SESSION_FORM)
      invalidateSessions()
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : "Failed to start session")
    },
  })

  const endMutation = useMutation({
    mutationFn: (sessionId: number) => endSession(token!, sessionId),
    onSuccess: (_, sessionId) => {
      toast.success("Session ended")
      if (currentSession?.id === sessionId) {
        setCurrentSession(null)
        setRecentResults([])
      }
      invalidateSessions()
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : "Failed to end session")
    },
  })

  const handleStartSession = useCallback(async (): Promise<boolean> => {
    if (!sessionForm.branch_location.trim()) {
      toast.error("Branch location is required")
      return false
    }
    if (!token) return false
    try {
      await startMutation.mutateAsync(sessionForm)
      return true
    } catch {
      return false
    }
  }, [sessionForm, token, startMutation])

  const handleEndSession = useCallback(async (sessionId: number) => {
    if (!token) return
    await endMutation.mutateAsync(sessionId).catch(() => undefined)
  }, [token, endMutation])

  const handleSelectSession = useCallback(async (session: CheckInSession) => {
    if (!token) return
    setCurrentSession(session)
    try {
      const results = await getSessionResults(token, session.id, { limit: 50 })
      setSessionResults(results)
      setRecentResults(results.slice(0, 10))
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token])

  const handleCheckIn = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (!token || !currentSession || !barcodeInput.trim()) return

      setIsProcessing(true)
      try {
        const result = await checkInItem(token, currentSession.id, {
          barcode: barcodeInput.trim(),
        })

        setRecentResults((prev) => [result, ...prev.slice(0, 9)])

        if (result.status === "success") {
          toast.success(`Checked in: ${result.item_title || result.barcode}`)
        } else if (result.status === "hold_triggered") {
          toast.success(`Hold triggered for ${result.hold_patron_name}`, { icon: "📚" })
        } else if (result.status === "transit") {
          toast.success(`Transit to ${result.destination_branch}`, { icon: "🚚" })
        } else if (result.status === "exception") {
          toast.error(`Exception: ${result.exception_message}`)
        } else {
          toast.error(`Item not found: ${barcodeInput}`)
        }

        setBarcodeInput("")

        const updatedSession = await getSession(token, currentSession.id)
        setCurrentSession(updatedSession)
      } catch (error: unknown) {
        toast.error(error instanceof Error ? error.message : "Check-in failed")
      } finally {
        setIsProcessing(false)
      }
    },
    [currentSession, barcodeInput, token]
  )

  return {
    sessions: sessionsQuery.data ?? [],
    activeSessions: activeSessionsQuery.data ?? [],
    currentSession,
    sessionResults,
    recentResults,
    barcodeInput,
    isLoading: sessionsQuery.isLoading || activeSessionsQuery.isLoading,
    isSaving: startMutation.isPending,
    isProcessing,
    sessionForm,
    setCurrentSession,
    setRecentResults,
    setBarcodeInput,
    setSessionForm,
    handleStartSession,
    handleEndSession,
    handleSelectSession,
    handleCheckIn,
  }
}
