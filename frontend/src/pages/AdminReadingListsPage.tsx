/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ListChecks, Search, Trash2, Eye, EyeOff, Pencil, X, Check, User } from 'lucide-react'
import { fetchApi } from '@/lib/api-client'
import { AdminShell } from '../components/shells/AdminShell'
import toast from 'react-hot-toast'
import { getCurrentLocale } from '@/i18n'

interface ReadingListAdmin {
  id: number
  name: string
  description: string | null
  is_public: boolean
  item_count: number
  owner_name: string
  owner_email: string
  owner_id: number
  created_at: string | null
  updated_at: string | null
}

function formatDate(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function AdminReadingListsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [publicOnly, setPublicOnly] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)

  const { data: lists = [], isLoading } = useQuery({
    queryKey: ['admin-reading-lists', search, publicOnly],
    queryFn: () => {
      const params = new URLSearchParams()
      if (search) params.append('search', search)
      if (publicOnly) params.append('public_only', 'true')
      return fetchApi<ReadingListAdmin[]>(`/admin/reading-lists?${params}`)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ReadingListAdmin> }) =>
      fetchApi(`/admin/reading-lists/${id}`, { method: 'PATCH', body: JSON.stringify(data), headers: { 'Content-Type': 'application/json' } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-reading-lists'] })
      setEditingId(null)
      toast.success('List updated')
    },
    onError: () => toast.error('Failed to update list'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      fetchApi(`/admin/reading-lists/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-reading-lists'] })
      setConfirmDelete(null)
      toast.success('List deleted')
    },
    onError: () => toast.error('Failed to delete list'),
  })

  const startEdit = (list: ReadingListAdmin) => {
    setEditingId(list.id)
    setEditName(list.name)
    setEditDesc(list.description || '')
  }

  const saveEdit = (id: number) => {
    updateMutation.mutate({ id, data: { name: editName, description: editDesc || null } })
  }

  const togglePublic = (list: ReadingListAdmin) => {
    updateMutation.mutate({ id: list.id, data: { is_public: !list.is_public } })
  }

  const publicCount = lists.filter(l => l.is_public).length

  return (
    <AdminShell title="Reading Lists">
      <div className="max-w-6xl mx-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <ListChecks className="w-6 h-6 text-lsc-rose" />
              Reading Lists
            </h1>
            <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">
              {lists.length} lists total, {publicCount} public
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-600" />
            <input
              type="text"
              placeholder="Search lists..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream cursor-pointer">
            <input
              type="checkbox"
              checked={publicOnly}
              onChange={(e) => setPublicOnly(e.target.checked)}
              className="rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
            />
            Public only
          </label>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="text-center py-12 text-earth-600 dark:text-earth-400">Loading...</div>
        ) : lists.length === 0 ? (
          <div className="text-center py-12 text-earth-600 dark:text-earth-400">No reading lists found</div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-lsc-border dark:border-earth-700">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-earth-50 dark:bg-earth-800 text-left text-earth-600 dark:text-earth-400">
                  <th className="px-4 py-3 font-medium">List</th>
                  <th className="px-4 py-3 font-medium">Owner</th>
                  <th className="px-4 py-3 font-medium text-center">Items</th>
                  <th className="px-4 py-3 font-medium text-center">Public</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-earth-100 dark:divide-earth-700">
                {lists.map((list) => (
                  <tr key={list.id} className="bg-lsc-white dark:bg-earth-900 hover:bg-earth-50 dark:hover:bg-earth-800/50">
                    <td className="px-4 py-3">
                      {editingId === list.id ? (
                        <div className="space-y-1">
                          <input
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            className="w-full px-2 py-1 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream"
                            autoFocus
                          />
                          <input
                            value={editDesc}
                            onChange={(e) => setEditDesc(e.target.value)}
                            placeholder="Description"
                            className="w-full px-2 py-1 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-800 text-sm text-earth-600 dark:text-earth-400"
                          />
                        </div>
                      ) : (
                        <div>
                          <div className="font-medium text-lsc-dark dark:text-lsc-cream">{list.name}</div>
                          {list.description && (
                            <div className="text-xs text-earth-600 dark:text-earth-400 mt-0.5 line-clamp-1">{list.description}</div>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-earth-600" />
                        <span className="text-lsc-dark dark:text-lsc-cream">{list.owner_name || 'Unknown'}</span>
                      </div>
                      <div className="text-xs text-earth-600 dark:text-earth-400">{list.owner_email}</div>
                    </td>
                    <td className="px-4 py-3 text-center text-lsc-dark dark:text-lsc-cream">{list.item_count}</td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => togglePublic(list)}
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                          list.is_public
                            ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400 hover:bg-status-success-200 dark:hover:bg-status-success-900/50'
                            : 'bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-400 hover:bg-earth-200 dark:hover:bg-earth-700'
                        }`}
                        title={list.is_public ? 'Click to make private' : 'Click to make public'}
                      >
                        {list.is_public ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                        {list.is_public ? 'Public' : 'Private'}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-earth-600 dark:text-earth-400 whitespace-nowrap">{formatDate(list.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {editingId === list.id ? (
                          <>
                            <button onClick={() => saveEdit(list.id)} className="p-1.5 rounded hover:bg-status-success-100 dark:hover:bg-status-success-900/30 text-status-success-600" title="Save">
                              <Check className="w-4 h-4" />
                            </button>
                            <button onClick={() => setEditingId(null)} className="p-1.5 rounded hover:bg-earth-100 dark:hover:bg-earth-800 text-earth-600" title="Cancel">
                              <X className="w-4 h-4" />
                            </button>
                          </>
                        ) : (
                          <>
                            <button onClick={() => startEdit(list)} className="p-1.5 rounded hover:bg-earth-100 dark:hover:bg-earth-800 text-earth-600 dark:text-earth-400" title="Edit">
                              <Pencil className="w-4 h-4" />
                            </button>
                            {confirmDelete === list.id ? (
                              <>
                                <button
                                  onClick={() => deleteMutation.mutate(list.id)}
                                  className="px-2 py-1 rounded bg-status-danger-600 text-white text-xs hover:bg-status-danger-700"
                                >
                                  Confirm
                                </button>
                                <button
                                  onClick={() => setConfirmDelete(null)}
                                  className="px-2 py-1 rounded bg-earth-200 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs hover:bg-earth-300 dark:hover:bg-earth-600"
                                >
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <button onClick={() => setConfirmDelete(list.id)} className="p-1.5 rounded hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 text-status-danger-500" title="Delete">
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminShell>
  )
}
