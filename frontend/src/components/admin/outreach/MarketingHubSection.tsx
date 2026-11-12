/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Sparkles,
  Clock,
  Star,
  Trash2,
  Copy,
  Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import AIContentGenerator from '@/components/marketing/AIContentGenerator'
import {
  getSavedContent,
  deleteSavedContent,
  toggleFavorite,
  getContentTypeLabel,
  CONTENT_TYPE_OPTIONS,
  type ContentType,
  type SavedContent,
} from '@/api/marketing-hub-api'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { clean } from '@/lib/utils'
import ConfirmDialog from '@/components/ConfirmDialog'
import { SectionShell } from '../ai-settings/SectionShell'

interface MarketingHubSectionProps {
  onBack: () => void
}

export function MarketingHubSection({ onBack }: MarketingHubSectionProps) {
  const { token } = useAuth()

  return (
    <SectionShell
      title="Marketing Hub"
      description="Generate marketing copy, social posts, and newsletter content with AI."
      tabs={[
        { id: 'create', label: 'Create Content', icon: Sparkles },
        { id: 'history', label: 'Saved Content', icon: Clock },
      ]}
      defaultTab="create"
      backLabel="Back to Outreach Dashboard"
      onBack={onBack}
    >
      {(activeTab) => (
        <>
          {activeTab === 'create' && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <AIContentGenerator />
            </div>
          )}
          {activeTab === 'history' && token && <HistoryTab token={token} />}
        </>
      )}
    </SectionShell>
  )
}

function HistoryTab({ token }: { token: string }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [filterType, setFilterType] = useState<string>('all')
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<SavedContent | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['marketing-hub-history', filterType, favoritesOnly],
    queryFn: () =>
      getSavedContent(token, clean({
        content_type: filterType !== 'all' ? (filterType as ContentType) : undefined,
        favorites_only: favoritesOnly,
        limit: 50,
      })),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteSavedContent(token, id),
    onSuccess: () => {
      toast.success(t('toast.marketingHub.contentDeleted'))
      queryClient.invalidateQueries({ queryKey: ['marketing-hub-history'] })
      setDeleteConfirm(null)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const favoriteMutation = useMutation({
    mutationFn: (id: number) => toggleFavorite(token, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketing-hub-history'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success(t('toast.copiedToClipboard'))
    } catch {
      toast.error(t('marketingHub.failedToCopyToClipboard'))
    }
  }

  const items = data?.items ?? []

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
        <div className="flex gap-3">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="all">All Types</option>
            {CONTENT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <button
            onClick={() => setFavoritesOnly(!favoritesOnly)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl border transition-colors ${
              favoritesOnly
                ? 'bg-status-warning-100 dark:bg-status-warning-900/30 border-status-warning-300 dark:border-status-warning-700 text-status-warning-700 dark:text-status-warning-400'
                : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70'
            }`}
          >
            <Star className={`w-4 h-4 ${favoritesOnly ? 'fill-current' : ''}`} />
            Favorites
          </button>
        </div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {data?.total ?? 0} saved items
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : items.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 text-center border border-lsc-border dark:border-earth-700">
          <Clock className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {favoritesOnly ? 'No favorite content yet' : 'No saved content yet. Generate some content and save it!'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <div
              key={item.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden"
            >
              <div className="flex items-center justify-between px-4 py-3 bg-lsc-cream/50 dark:bg-lsc-brown/30 border-b border-lsc-border dark:border-earth-700">
                <div className="flex items-center gap-3">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-lsc-rose/10 text-lsc-rose">
                    {getContentTypeLabel(item.content_type)}
                  </span>
                  {item.title && (
                    <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {item.title}
                    </span>
                  )}
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {new Date(item.created_at).toLocaleDateString(getCurrentLocale(), {
                      month: 'short',
                      day: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => favoriteMutation.mutate(item.id)}
                    className="p-2 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors"
                    title={item.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                  >
                    <Star
                      className={`w-4 h-4 ${
                        item.is_favorite
                          ? 'text-status-warning-500 fill-current'
                          : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                      }`}
                    />
                  </button>
                  <button
                    onClick={() => handleCopy(item.generated_text)}
                    className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg transition-colors"
                    title="Copy to clipboard"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setDeleteConfirm(item)}
                    className="p-2 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="p-4">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Prompt: {item.user_prompt.length > 120 ? item.user_prompt.slice(0, 120) + '...' : item.user_prompt}
                </p>
                <div className="whitespace-pre-wrap text-lsc-dark dark:text-lsc-cream leading-relaxed text-sm">
                  {item.generated_text}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Delete Content?"
        message="This will permanently delete this saved content. This action cannot be undone."
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={() => { if (deleteConfirm) deleteMutation.mutate(deleteConfirm.id) }}
        onCancel={() => setDeleteConfirm(null)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}
