/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo, useId } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Tag, X, Plus, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import {
  listTags,
  getPatronTags,
  assignTagToPatron,
  removeTagFromPatron,
  getTagColorClasses,
  type PatronTag,
  type Tag as TagType,
} from '@/api/domains/patron/patron-segmentation-api'

interface PatronTagsSectionProps {
  patronId: number
}

export function PatronTagsSection({ patronId }: PatronTagsSectionProps) {
  const { token } = useAuth()
  const queryClient = useQueryClient()
  const [showDropdown, setShowDropdown] = useState(false)
  const [search, setSearch] = useState('')
  const dropdownId = useId()

  const {
    data: currentTags = [],
    isLoading: isLoadingCurrent,
  } = useQuery({
    queryKey: ['patron-tags', patronId],
    queryFn: () => getPatronTags(token!, patronId),
    enabled: !!token,
  })

  const { data: allTagsResponse } = useQuery({
    queryKey: ['all-tags'],
    queryFn: () => listTags(token!),
    enabled: !!token,
  })

  const allTags = allTagsResponse?.tags ?? []

  const availableTags = useMemo(() => {
    const assignedIds = new Set(currentTags.map((t: PatronTag) => t.tag_id))
    return allTags
      .filter((t: TagType) => t.is_active && !assignedIds.has(t.id))
      .filter((t: TagType) =>
        !search || t.name.toLowerCase().includes(search.toLowerCase())
      )
  }, [allTags, currentTags, search])

  const assignMutation = useMutation({
    mutationFn: (tagId: number) => assignTagToPatron(token!, patronId, tagId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patron-tags', patronId] })
      setShowDropdown(false)
      setSearch('')
      toast.success('Tag assigned')
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const removeMutation = useMutation({
    mutationFn: (tagId: number) => removeTagFromPatron(token!, patronId, tagId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patron-tags', patronId] })
      toast.success('Tag removed')
    },
    onError: (err: Error) => toast.error(err.message),
  })

  return (
    <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <Tag className="w-5 h-5 text-lsc-rose" />
          Tags
        </h3>
        <div className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            aria-haspopup="true"
            aria-expanded={showDropdown}
            aria-controls={dropdownId}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-lsc-rose hover:bg-lsc-rose/10 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Tag
          </button>

          {showDropdown && (
            <div id={dropdownId} className="absolute right-0 top-full mt-1 w-64 bg-lsc-white dark:bg-earth-800 border border-sage/30 rounded-xl shadow-lg z-20">
              <div className="p-2">
                <input
                  type="text"
                  placeholder="Search tags..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  autoFocus
                  className="w-full px-3 py-1.5 text-sm border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose/50"
                />
              </div>
              <div className="max-h-48 overflow-y-auto">
                {availableTags.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {search ? 'No matching tags' : 'No tags available'}
                  </div>
                ) : (
                  availableTags.map((tag: TagType) => (
                    <button
                      key={tag.id}
                      onClick={() => assignMutation.mutate(tag.id)}
                      disabled={assignMutation.isPending}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 flex items-center gap-2 transition-colors"
                    >
                      <span className={`inline-block w-2.5 h-2.5 rounded-full ${getTagColorClasses(tag.color)}`} />
                      <span className="text-lsc-dark dark:text-lsc-cream">{tag.name}</span>
                    </button>
                  ))
                )}
              </div>
              <div className="border-t border-sage/20 p-1">
                <button
                  onClick={() => { setShowDropdown(false); setSearch('') }}
                  className="w-full text-left px-3 py-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 rounded-lg"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {isLoadingCurrent ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : currentTags.length === 0 ? (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          No tags assigned to this patron.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {currentTags.map((pt: PatronTag) => (
            <span
              key={pt.id}
              className={`inline-flex items-center gap-1.5 px-3 py-1 text-sm font-medium rounded-full ${getTagColorClasses(pt.tag_color)}`}
            >
              {pt.tag_name}
              <button
                onClick={() => removeMutation.mutate(pt.tag_id)}
                disabled={removeMutation.isPending}
                className="hover:opacity-70 transition-opacity"
                title={`Remove ${pt.tag_name}`}
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
