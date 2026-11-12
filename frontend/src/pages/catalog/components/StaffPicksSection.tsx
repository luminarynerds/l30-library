/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useTranslation } from '@/i18n/I18nContext'
import { fetchApi } from '@/lib/api-client'
import CatalogItemThumbnail, { CatalogCover } from './CatalogItemThumbnail'
import { catalogItemLink } from '../utils/catalogHelpers'

interface StaffPickItem {
  id: number
  catalog_item_id: number
  catalog_item: {
    id: number
    title: string
    cover_url: string | null
    item_type: string
  }
  staff_notes: string | null
  display_order: number
  added_by_id: number
}

interface StaffPicksList {
  id: number
  title: string
  description: string | null
  is_active: boolean
  display_order: number
  created_by_id: number
  items_count: number
  items: StaffPickItem[]
}

interface StaffPicksSectionProps {
  showImages: boolean
}

async function getFirstActiveStaffPicksList(): Promise<StaffPicksList | null> {
  const lists = await fetchApi<Array<{ id: number; title: string; is_active: boolean; display_order: number; created_by_id: number; items_count: number; description: string | null }>>('/staff/picks/public/lists?limit=1')
  const first = lists?.[0]
  if (!first) return null
  return await fetchApi<StaffPicksList>(`/staff/picks/public/${first.id}`)
}

export default function StaffPicksSection({ showImages }: StaffPicksSectionProps) {
  const { t } = useTranslation()

  const { data: picksList } = useQuery({
    queryKey: ['catalog', 'staff-picks'],
    queryFn: getFirstActiveStaffPicksList,
    staleTime: 10 * 60 * 1000,
  })

  if (!picksList || picksList.items.length === 0) return null

  return (
    <div className="mb-8">
      <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
        {picksList.title || t('catalog.staffPicks.title')}
      </h2>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-4">
        {picksList.description || t('catalog.staffPicks.subtitle')}
      </p>
      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
        role="list"
        aria-label={t('catalog.staffPicks.ariaLabel')}
      >
        {picksList.items.map((pick) => (
          <Link
            key={pick.id}
            to={catalogItemLink(pick.catalog_item.id, pick.catalog_item.title)}
            state={{ fromCatalog: true }}
            role="listitem"
            className="flex items-start gap-3 p-4 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50 hover:shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          >
            {showImages && (
              <div className="w-[60px] h-[85px] rounded-lg overflow-hidden bg-lsc-border dark:bg-earth-700 flex-shrink-0">
                {pick.catalog_item.cover_url ? (
                  <CatalogCover
                    coverUrl={pick.catalog_item.cover_url}
                    itemId={pick.catalog_item.id}
                    alt=""
                    title={pick.catalog_item.title}
                    itemType={pick.catalog_item.item_type}
                    size="sm"
                  />
                ) : (
                  <CatalogItemThumbnail title={pick.catalog_item.title} itemType={pick.catalog_item.item_type} />
                )}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-bold text-lsc-dark dark:text-lsc-cream line-clamp-2" title={pick.catalog_item.title}>
                {pick.catalog_item.title}
              </h3>
              {pick.staff_notes && (
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 line-clamp-3 italic">
                  "{pick.staff_notes}"
                </p>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
