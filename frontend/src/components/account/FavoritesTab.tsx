/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Heart, Calendar, Trash2, RefreshCw, Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { Favorite } from '../../services/api'

interface FavoritesTabProps {
  favorites: Favorite[]
  favoritesLoading: boolean
  removingFavId: number | null
  onRefresh: () => void
  onRemove: (catalogItemId: number) => void
  formatDate: (dateStr: string) => string
}

export function FavoritesTab({
  favorites,
  favoritesLoading,
  removingFavId,
  onRefresh,
  onRemove,
  formatDate,
}: FavoritesTabProps): React.ReactElement {
  const { t } = useTranslation()

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('account.myFavorites')}</h2>
        <button
          onClick={onRefresh}
          disabled={favoritesLoading}
          aria-label={t('account.refreshFavorites')}
          className="flex items-center gap-2 px-3 py-2 text-lsc-dark/70 hover:text-lsc-dark transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-5 h-5 ${favoritesLoading ? 'motion-safe:animate-spin' : ''}`} />
          {t('account.refresh')}
        </button>
      </div>

      {favoritesLoading ? (
        <div className="flex justify-center py-12" role="status">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
        </div>
      ) : favorites.length === 0 ? (
        <div className="text-center py-12">
          <Heart className="w-12 h-12 text-sage/30 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('account.noFavorites')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {favorites.map(favorite => (
            <div key={favorite.id} className="p-4 rounded-xl border-2 border-sage/20 bg-cream dark:bg-earth-800">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg">{favorite.catalog_item.title}</h3>
                  {favorite.catalog_item.author && (
                    <p className="text-lsc-dark/70 text-sm mt-1">{t('account.byAuthor')} {favorite.catalog_item.author}</p>
                  )}
                  {favorite.catalog_item.item_type && (
                    <p className="text-lsc-dark/70 text-sm mt-1">{t('account.type', { type: favorite.catalog_item.item_type })}</p>
                  )}
                  <div className="flex items-center gap-1 mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Calendar className="w-4 h-4" />
                    <span>{t('account.added', { date: formatDate(favorite.created_at) })}</span>
                  </div>
                </div>
                <button
                  onClick={() => onRemove(favorite.catalog_item_id)}
                  disabled={removingFavId === favorite.catalog_item_id}
                  className="ml-4 px-4 py-2 bg-status-danger-600 text-white rounded-xl hover:bg-status-danger-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {removingFavId === favorite.catalog_item_id ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      {t('account.remove')}
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
