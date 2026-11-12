/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import {
  getPatronTags,
  renamePatronTag,
  deletePatronTag,
} from '@/api/domains/content/patron-tags-api'

export function usePatronTags() {
  const { token } = useAuth()
  const queryClient = useQueryClient()
  const [activeFilters, setActiveFilters] = useState<string[]>([])

  const { data: allTags = [], isLoading } = useQuery({
    queryKey: ['patron-tags', token],
    queryFn: () => getPatronTags(token!),
    enabled: !!token,
  })

  const handleRename = async (oldName: string, newName: string) => {
    if (!token) return
    try {
      await renamePatronTag(token, oldName, newName)
      toast.success(`Renamed tag "${oldName}" to "${newName}"`)
      queryClient.invalidateQueries({ queryKey: ['patron-tags'] })
      queryClient.invalidateQueries({ queryKey: ['reading-statuses'] })
      // Update active filters if the renamed tag was active
      setActiveFilters((prev) => prev.map((t) => (t === oldName ? newName : t)))
    } catch {
      toast.error('Failed to rename tag')
    }
  }

  const handleDelete = async (tagName: string) => {
    if (!token) return
    try {
      await deletePatronTag(token, tagName)
      toast.success(`Removed tag "${tagName}"`)
      queryClient.invalidateQueries({ queryKey: ['patron-tags'] })
      queryClient.invalidateQueries({ queryKey: ['reading-statuses'] })
      setActiveFilters((prev) => prev.filter((t) => t !== tagName))
    } catch {
      toast.error('Failed to delete tag')
    }
  }

  const toggleFilter = (tag: string) => {
    setActiveFilters((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    )
  }

  const clearFilters = () => setActiveFilters([])

  return {
    allTags,
    isLoading,
    activeFilters,
    toggleFilter,
    clearFilters,
    handleRename,
    handleDelete,
  }
}
