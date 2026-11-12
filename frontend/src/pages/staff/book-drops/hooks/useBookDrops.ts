/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  listBookDrops,
  createBookDrop,
  updateBookDrop,
  deleteBookDrop,
  BookDrop,
  BookDropCreate,
  BookDropUpdate,
  BookDropStatus,
} from "@/api/book-drop-api"
import toast from "react-hot-toast"

export interface BookDropFormState extends BookDropCreate {
  status?: BookDropStatus
}

const DEFAULT_FORM: BookDropFormState = {
  name: "",
  code: "",
  branch_location: "",
  description: "",
  physical_location: "",
  backdate_mode: "none",
  backdate_fixed_time: "",
  processing_start_time: "",
  processing_end_time: "",
  exempt_overnight_fines: false,
}

export const bookDropsQueryKey = (filter: "all" | BookDropStatus) => ["book-drops", filter] as const

export function useBookDrops(token: string | null) {
  const queryClient = useQueryClient()
  const [bookDropFilter, setBookDropFilter] = useState<"all" | BookDropStatus>("all")
  const [bookDropForm, setBookDropForm] = useState<BookDropFormState>(DEFAULT_FORM)
  const [isEditing, setIsEditing] = useState(false)
  const [selectedItem, setSelectedItem] = useState<BookDrop | null>(null)

  const query = useQuery({
    queryKey: bookDropsQueryKey(bookDropFilter),
    queryFn: () => {
      const status = bookDropFilter === "all" ? undefined : bookDropFilter
      return listBookDrops(token!, status ? { status } : {})
    },
    enabled: !!token,
  })

  const saveMutation = useMutation({
    mutationFn: async (form: BookDropFormState) => {
      if (isEditing && selectedItem) {
        const updateData: BookDropUpdate = { ...form }
        if (form.status) updateData.status = form.status
        return updateBookDrop(token!, selectedItem.id, updateData)
      }
      return createBookDrop(token!, form)
    },
    onSuccess: () => {
      toast.success(isEditing ? "Book drop updated successfully" : "Book drop created successfully")
      queryClient.invalidateQueries({ queryKey: ["book-drops"] })
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : "Failed to save book drop")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (bookDrop: BookDrop) => deleteBookDrop(token!, bookDrop.id),
    onSuccess: () => {
      toast.success("Book drop deleted successfully")
      queryClient.invalidateQueries({ queryKey: ["book-drops"] })
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : "Failed to delete book drop")
    },
  })

  const resetForm = useCallback(() => {
    setBookDropForm(DEFAULT_FORM)
    setIsEditing(false)
    setSelectedItem(null)
  }, [])

  const handleSaveBookDrop = useCallback(async (): Promise<boolean> => {
    if (!bookDropForm.name.trim() || !bookDropForm.code.trim()) {
      toast.error("Name and code are required")
      return false
    }
    if (!token) return false
    try {
      await saveMutation.mutateAsync(bookDropForm)
      resetForm()
      return true
    } catch {
      return false
    }
  }, [bookDropForm, token, saveMutation, resetForm])

  const handleDeleteBookDrop = useCallback(async (bookDrop: BookDrop): Promise<boolean> => {
    if (!token) return false
    try {
      await deleteMutation.mutateAsync(bookDrop)
      return true
    } catch {
      return false
    }
  }, [token, deleteMutation])

  const openEditBookDrop = useCallback((bookDrop: BookDrop) => {
    const formData: BookDropFormState = {
      name: bookDrop.name,
      code: bookDrop.code,
      branch_location: bookDrop.branch_location,
      description: bookDrop.description || "",
      physical_location: bookDrop.physical_location || "",
      backdate_mode: bookDrop.backdate_mode,
      backdate_fixed_time: bookDrop.backdate_fixed_time || "",
      processing_start_time: bookDrop.processing_start_time || "",
      processing_end_time: bookDrop.processing_end_time || "",
      exempt_overnight_fines: bookDrop.exempt_overnight_fines,
      status: bookDrop.status,
    }
    if (bookDrop.backdate_hours !== null) formData.backdate_hours = bookDrop.backdate_hours
    if (bookDrop.backdate_days !== null) formData.backdate_days = bookDrop.backdate_days
    if (bookDrop.max_backdate_hours !== null) formData.max_backdate_hours = bookDrop.max_backdate_hours
    setBookDropForm(formData)
    setSelectedItem(bookDrop)
    setIsEditing(true)
  }, [])

  return {
    bookDrops: query.data ?? [],
    bookDropFilter,
    isLoading: query.isLoading,
    isSaving: saveMutation.isPending,
    isDeleting: deleteMutation.isPending,
    bookDropForm,
    isEditing,
    selectedItem,
    setBookDropFilter,
    setBookDropForm,
    setSelectedItem,
    handleSaveBookDrop,
    handleDeleteBookDrop,
    resetForm,
    openEditBookDrop,
  }
}
