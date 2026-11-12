/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ListPlus, Check, Plus, Loader2 } from "lucide-react"
import {
  getMyIndieReadingLists,
  addToIndieReadingList,
  createIndieReadingList,
  type IndieReadingListSummary,
} from "@/api/indie-engagement-api"
import { getAccessToken } from "@/utils/tokenStore"

interface AddToListButtonProps {
  ebookId: number
  existingListIds?: number[]
}

export default function AddToListButton({ ebookId, existingListIds }: AddToListButtonProps) {
  const [open, setOpen] = useState(false)
  const [newListName, setNewListName] = useState("")
  const ref = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()
  const loggedIn = !!getAccessToken()

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  const { data: lists } = useQuery({
    queryKey: ["indie-reading-lists"],
    queryFn: getMyIndieReadingLists,
    enabled: open && loggedIn,
  })

  const addMutation = useMutation({
    mutationFn: (listId: number) => addToIndieReadingList(listId, ebookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["indie-reading-lists"] })
    },
  })

  const createAndAddMutation = useMutation({
    mutationFn: async () => {
      const newList = await createIndieReadingList(newListName)
      await addToIndieReadingList(newList.id, ebookId)
      return newList
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["indie-reading-lists"] })
      setNewListName("")
    },
  })

  if (!loggedIn) return null

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="p-2 text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-lsc-rose transition-colors"
        aria-label="Add to reading list"
        title="Add to reading list"
      >
        <ListPlus className="w-5 h-5" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-64 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-earth-200 dark:border-earth-600 z-50 overflow-hidden">
          <div className="p-2 border-b border-earth-200 dark:border-earth-600">
            <p className="text-xs font-medium text-lsc-dark/50 dark:text-lsc-cream/50 px-2 py-1">
              Add to list
            </p>
          </div>
          <div className="max-h-48 overflow-y-auto">
            {!lists ? (
              <div className="flex justify-center py-3">
                <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : lists.length === 0 ? (
              <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 px-4 py-3">
                No lists yet. Create one below.
              </p>
            ) : (
              lists.map((list: IndieReadingListSummary) => {
                const inList = existingListIds?.includes(list.id)
                return (
                  <button
                    key={list.id}
                    onClick={() => { if (!inList) addMutation.mutate(list.id) }}
                    disabled={!!inList || addMutation.isPending}
                    className="w-full text-left px-4 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-earth-100 dark:hover:bg-earth-700 flex items-center gap-2 disabled:opacity-50 transition-colors"
                  >
                    {inList && <Check className="w-3.5 h-3.5 text-status-success-500 flex-shrink-0" />}
                    <span className="truncate">{list.name}</span>
                    <span className="text-xs text-lsc-dark/40 dark:text-lsc-cream/40 ml-auto flex-shrink-0">
                      {list.item_count}
                    </span>
                  </button>
                )
              })
            )}
          </div>
          <div className="p-2 border-t border-earth-200 dark:border-earth-600">
            <div className="flex gap-1">
              <input
                type="text"
                value={newListName}
                onChange={(e) => setNewListName(e.target.value)}
                placeholder="New list name"
                maxLength={200}
                className="flex-1 px-2 py-1 text-sm border border-earth-300 dark:border-earth-600 rounded bg-transparent text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-1 focus:ring-lsc-rose"
                onKeyDown={(e) => { if (e.key === "Enter" && newListName.trim()) createAndAddMutation.mutate() }}
              />
              <button
                onClick={() => createAndAddMutation.mutate()}
                disabled={!newListName.trim() || createAndAddMutation.isPending}
                className="p-1.5 text-lsc-rose hover:text-lsc-rose/80 disabled:opacity-50 transition-colors"
                aria-label="Create list and add book"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
