/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { List, Plus, Globe, Lock, Loader2, Trash2 } from "lucide-react"
import {
  getMyIndieReadingLists,
  createIndieReadingList,
  deleteIndieReadingList,
  type IndieReadingListSummary,
} from "@/api/indie-engagement-api"
import { useBranding } from "@/contexts/BrandingContext"
import PageContainer from '@/components/layout/PageContainer'

export default function IndieReadingListsPage() {
  const branding = useBranding()
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState("")
  const [newDesc, setNewDesc] = useState("")

  useEffect(() => {
    document.title = "My Reading Lists | Indie Catalog"
    return () => { document.title = branding.library_name }
  }, [branding.library_name])

  const { data: lists, isLoading } = useQuery({
    queryKey: ["indie-reading-lists"],
    queryFn: getMyIndieReadingLists,
  })

  const createMutation = useMutation({
    mutationFn: () => createIndieReadingList(newName, newDesc || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["indie-reading-lists"] })
      setShowCreate(false)
      setNewName("")
      setNewDesc("")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteIndieReadingList(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["indie-reading-lists"] })
    },
  })

  return (
    <PageContainer className="py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <List className="w-6 h-6 text-lsc-rose" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            My Reading Lists
          </h1>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New List
        </button>
      </div>

      {showCreate && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 mb-6">
          <input
            type="text"
            placeholder="List name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            maxLength={200}
            className="w-full px-3 py-2 border border-earth-300 dark:border-earth-600 rounded-lg bg-transparent text-lsc-dark dark:text-lsc-cream mb-2 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
          <textarea
            placeholder="Description (optional)"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            className="w-full px-3 py-2 border border-earth-300 dark:border-earth-600 rounded-lg bg-transparent text-lsc-dark dark:text-lsc-cream mb-3 focus:outline-none focus:ring-2 focus:ring-lsc-rose resize-none"
            rows={2}
          />
          <div className="flex gap-2">
            <button
              onClick={() => createMutation.mutate()}
              disabled={!newName.trim() || createMutation.isPending}
              className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending ? "Creating..." : "Create"}
            </button>
            <button
              onClick={() => { setShowCreate(false); setNewName(""); setNewDesc("") }}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : !lists || lists.length === 0 ? (
        <div className="text-center py-12">
          <List className="w-12 h-12 mx-auto text-lsc-dark/20 dark:text-lsc-cream/20 mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            No reading lists yet
          </p>
          <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50">
            Create a list to organize your favorite indie ebooks.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {lists.map((list: IndieReadingListSummary) => (
            <div
              key={list.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 flex items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <Link
                  to={`/indie/lists/${list.id}`}
                  className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose block truncate"
                >
                  {list.name}
                </Link>
                {list.description && (
                  <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60 truncate">
                    {list.description}
                  </p>
                )}
                <div className="flex items-center gap-3 mt-1 text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
                  <span>{list.item_count} {list.item_count === 1 ? "book" : "books"}</span>
                  <span className="flex items-center gap-1">
                    {list.is_public ? <Globe className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
                    {list.is_public ? "Public" : "Private"}
                  </span>
                </div>
              </div>
              <button
                onClick={() => { if (confirm("Delete this list?")) deleteMutation.mutate(list.id) }}
                className="p-2 text-lsc-dark/30 dark:text-lsc-cream/30 hover:text-status-danger-500 transition-colors"
                aria-label={`Delete ${list.name}`}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  )
}
