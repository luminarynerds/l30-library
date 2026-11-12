/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  listExceptions,
  resolveException,
  CheckInException,
  ExceptionType,
} from "@/api/book-drop-api"
import toast from "react-hot-toast"
import { clean } from '@/lib/utils'

export interface UseBookDropExceptionsReturn {
  exceptions: CheckInException[]
  isLoading: boolean
  isSaving: boolean
  filter: ExceptionType | "all"
  page: number
  pageSize: number
  setFilter: (filter: ExceptionType | "all") => void
  setPage: (page: number) => void
  handleResolveException: (exceptionId: number, action: string) => Promise<boolean>
}

export const exceptionsQueryKey = (
  filter: ExceptionType | "all",
  page: number,
  pageSize: number,
) => ["book-drop-exceptions", filter, page, pageSize] as const

export function useBookDropExceptions(token: string | null): UseBookDropExceptionsReturn {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<ExceptionType | "all">("all")
  const [page, setPage] = useState(1)
  const pageSize = 20

  const query = useQuery({
    queryKey: exceptionsQueryKey(filter, page, pageSize),
    queryFn: () => {
      const exceptionType = filter === "all" ? undefined : filter
      return listExceptions(token!, clean({
        exception_type: exceptionType,
        resolved: false,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      }))
    },
    enabled: !!token,
  })

  const resolveMutation = useMutation({
    mutationFn: ({ exceptionId, action }: { exceptionId: number; action: string }) =>
      resolveException(token!, exceptionId, { action_taken: action }),
    onSuccess: () => {
      toast.success("Exception resolved")
      queryClient.invalidateQueries({ queryKey: ["book-drop-exceptions"] })
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : "Failed to resolve exception")
    },
  })

  const handleResolveException = useCallback(
    async (exceptionId: number, action: string): Promise<boolean> => {
      if (!action.trim()) {
        toast.error("Please enter the action taken")
        return false
      }
      if (!token) return false
      try {
        await resolveMutation.mutateAsync({ exceptionId, action })
        return true
      } catch {
        return false
      }
    },
    [token, resolveMutation]
  )

  return {
    exceptions: query.data ?? [],
    isLoading: query.isLoading,
    isSaving: resolveMutation.isPending,
    filter,
    page,
    pageSize,
    setFilter,
    setPage,
    handleResolveException,
  }
}
