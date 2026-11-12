/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import {
  getContentPreferences,
  updateContentPreferences,
  getWarningCategories} from '@/api/indie-engagement-api'

interface ContentPreferencesPanelProps {
  onClose: () => void
}

export default function ContentPreferencesPanel({ onClose }: ContentPreferencesPanelProps): React.ReactElement {
  const queryClient = useQueryClient()

  const { data: categories, isLoading: catLoading } = useQuery({
    queryKey: ['indie-warning-categories'],
    queryFn: getWarningCategories,
  })

  const { data: prefs, isLoading: prefsLoading } = useQuery({
    queryKey: ['indie-content-prefs'],
    queryFn: getContentPreferences,
  })

  const mutation = useMutation({
    mutationFn: updateContentPreferences,
    onSuccess: (data) => {
      queryClient.setQueryData(['indie-content-prefs'], data)
    },
  })

  const isLoading = catLoading || prefsLoading

  const toggleCategory = (category: string, list: 'hidden' | 'flagged') => {
    if (!prefs) return
    const hidden = [...(prefs.hidden_warnings || [])]
    const flagged = [...(prefs.flagged_warnings || [])]

    if (list === 'hidden') {
      const idx = hidden.indexOf(category)
      if (idx >= 0) {
        hidden.splice(idx, 1)
      } else {
        hidden.push(category)
        const fIdx = flagged.indexOf(category)
        if (fIdx >= 0) flagged.splice(fIdx, 1)
      }
    } else {
      const idx = flagged.indexOf(category)
      if (idx >= 0) {
        flagged.splice(idx, 1)
      } else {
        flagged.push(category)
        const hIdx = hidden.indexOf(category)
        if (hIdx >= 0) hidden.splice(hIdx, 1)
      }
    }

    mutation.mutate({ hidden_warnings: hidden, flagged_warnings: flagged })
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg p-4 w-80 max-h-96 overflow-y-auto">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-serif font-semibold text-sm text-lsc-dark dark:text-lsc-cream">
          Content Warning Preferences
        </h3>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-lsc-rose"
          aria-label="Close preferences"
        >
          Done
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-6">
          <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : (
        <div className="space-y-1">
          <div className="grid grid-cols-[1fr_auto_auto] gap-x-3 gap-y-1 text-xs">
            <div className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70 pb-1">Category</div>
            <div className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70 pb-1 text-center">Hide</div>
            <div className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70 pb-1 text-center">Flag</div>
            {(categories || []).map((cat) => {
              const isHidden = prefs?.hidden_warnings?.includes(cat)
              const isFlagged = prefs?.flagged_warnings?.includes(cat)
              return (
                <div key={cat} className="contents">
                  <span className="text-lsc-dark dark:text-lsc-cream capitalize py-0.5">
                    {cat}
                  </span>
                  <div className="flex justify-center">
                    <input
                      type="checkbox"
                      checked={!!isHidden}
                      onChange={() => toggleCategory(cat, 'hidden')}
                      className={clsx(
                        'w-4 h-4 rounded border-lsc-border accent-status-danger-500',
                        mutation.isPending && 'opacity-50'
                      )}
                      aria-label={`Hide books with ${cat}`}
                    />
                  </div>
                  <div className="flex justify-center">
                    <input
                      type="checkbox"
                      checked={!!isFlagged}
                      onChange={() => toggleCategory(cat, 'flagged')}
                      className={clsx(
                        'w-4 h-4 rounded border-lsc-border accent-status-warning-500',
                        mutation.isPending && 'opacity-50'
                      )}
                      aria-label={`Flag books with ${cat}`}
                    />
                  </div>
                </div>
              )
            })}
          </div>
          <p className="text-[10px] text-lsc-dark/40 dark:text-lsc-cream/40 pt-2">
            Hidden books are filtered from results. Flagged books show amber badges.
          </p>
        </div>
      )}
    </div>
  )
}

