/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * StaffSearchPanel
 *
 * Staff-scope panel for HeaderSearch. Owns staff fan-out search across
 * patrons, staff directory, items, purchase orders, and events; the
 * staff-only entity-type filter strip; the navigation/page results;
 * and the "did you mean" suggestion.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { useTranslation } from '../../i18n/I18nContext'
import { getAccessToken } from '../../utils/tokenStore'
import { searchPatrons, listStaff } from '@/api/staff-api'
import { searchCatalog } from '../../api/catalog-api'
import { getPurchaseOrders } from '../../api/acquisition-po-api'
import { getEvents } from '@/api/events-api'
import { searchStaffNav, type StaffNavEntry } from './staff-nav-index'
import {
  type StaffSearchEntityType,
  type StaffSearchResult,
  buildDidYouMean,
  rankStaffSearchResults,
} from './staff-search-utils'

const TYPE_LABELS: Record<StaffSearchEntityType | 'page', string> = {
  patron: 'Patron',
  staff: 'Staff Member',
  item: 'Item',
  order: 'Order',
  event: 'Event',
  page: 'Page',
}

export interface StaffSearchPanelProps {
  query: string
  setQuery: (next: string) => void
  isStaffUser: boolean
  staffFilter: 'all' | StaffSearchEntityType
  onClose: () => void
  onClearQuery: () => void
  onConsumeQuery: () => void
  saveRecentSearch: (query: string) => void
  registerKeyHandler?: (handler: ((e: React.KeyboardEvent<HTMLInputElement>) => void) | null) => void
  registerSubmitHandler?: (handler: (() => void) | null) => void
}

export default function StaffSearchPanel({
  query,
  setQuery,
  isStaffUser,
  staffFilter,
  onClose,
  onClearQuery,
  onConsumeQuery,
  saveRecentSearch,
  registerKeyHandler,
  registerSubmitHandler,
}: StaffSearchPanelProps): React.ReactElement {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [staffResults, setStaffResults] = useState<StaffSearchResult[]>([])
  const [navResults, setNavResults] = useState<StaffNavEntry[]>([])
  const [isStaffSearching, setIsStaffSearching] = useState(false)

  const runStaffSearch = useCallback(async (searchQuery: string) => {
    const token = getAccessToken()
    if (!token || !isStaffUser || searchQuery.trim().length < 2) {
      setStaffResults([])
      setNavResults([])
      return
    }

    setIsStaffSearching(true)

    // Search navigation index (instant, no API call)
    setNavResults(searchStaffNav(searchQuery))

    try {
      const [patronsResult, staffResult, itemsResult, ordersResult, eventsResult] = await Promise.allSettled([
        searchPatrons(token, searchQuery, 1),
        listStaff(token, 1, 25, { search: searchQuery }),
        searchCatalog({ query: searchQuery, page: 1, per_page: 25 }),
        getPurchaseOrders({ page: 1, per_page: 100 }),
        getEvents({ search: searchQuery, page: 1, per_page: 50, upcoming: false }),
      ])

      const patrons = patronsResult.status === 'fulfilled' ? patronsResult.value : { patrons: [], total: 0, page: 1, per_page: 20 }
      const staffMembers = staffResult.status === 'fulfilled' ? staffResult.value : { staff: [], total: 0, page: 1, per_page: 25 }
      const items = itemsResult.status === 'fulfilled' ? itemsResult.value : { items: [], total: 0, page: 1, per_page: 25, pages: 0 }
      const orders = ordersResult.status === 'fulfilled' ? ordersResult.value : { items: [], total: 0, page: 1, per_page: 100 }
      const events = eventsResult.status === 'fulfilled' ? eventsResult.value : { data: [], pagination: { page: 1, per_page: 50, total: 0, total_pages: 0, has_next: false, has_previous: false } }

      const patronResults: StaffSearchResult[] = patrons.patrons.map((patron) => ({
        id: `patron-${patron.id}`,
        type: 'patron',
        title: `${patron.first_name} ${patron.last_name}`,
        subtitle: `${patron.library_card ?? 'No card'} • ${patron.email}`,
        route: '/staff/patrons',
        searchableText: `${patron.email} ${patron.phone ?? ''} ${patron.library_card ?? ''}`,
      }))

      const staffMemberResults: StaffSearchResult[] = staffMembers.staff.map((member) => ({
        id: `staff-${member.id}`,
        type: 'staff',
        title: `${member.first_name} ${member.last_name}`,
        subtitle: `${member.role} • ${member.email}`,
        route: '/staff/directory',
        searchableText: `${member.email} ${member.department ?? ''} ${member.role}`,
      }))

      const itemResults: StaffSearchResult[] = items.items.map((item) => ({
        id: `item-${item.id}`,
        type: 'item',
        title: item.title,
        subtitle: `${item.author ?? 'Unknown author'} • ${item.barcode ?? item.isbn ?? 'No barcode/ISBN'}`,
        route: '/catalog',
        searchableText: `${item.isbn ?? ""} ${item.barcode ?? ""} ${item.publisher ?? ""} ${item.subjects ?? ""} ${(item.description ?? "").slice(0, 200)}`,
      }))

      const filteredOrders = orders.items.filter((order) => {
        const haystack = `${order.po_number} ${order.vendor_name ?? ''} ${order.fund_name ?? ''} ${order.status}`.toLowerCase()
        return haystack.includes(searchQuery.toLowerCase())
      })

      const orderResults: StaffSearchResult[] = filteredOrders.map((order) => ({
        id: `order-${order.id}`,
        type: 'order',
        title: order.po_number,
        subtitle: `${order.vendor_name ?? 'Unknown vendor'} • ${order.status}`,
        route: '/staff/acquisition',
        searchableText: `${order.fund_name ?? ''} ${order.total_amount}`,
      }))

      const eventResults: StaffSearchResult[] = events.data.map((event) => ({
        id: `event-${event.id}`,
        type: 'event',
        title: event.title,
        subtitle: `${event.category ?? 'General'} • ${event.location ?? (event.is_virtual ? 'Virtual' : 'TBD')}`,
        route: '/staff/admin/events',
        searchableText: `${event.description ?? ''} ${event.tags?.join(' ') ?? ''}`,
      }))

      const ranked = rankStaffSearchResults(searchQuery, [
        ...patronResults,
        ...staffMemberResults,
        ...itemResults,
        ...orderResults,
        ...eventResults,
      ])
      setStaffResults(ranked)
    } catch (err) {
      console.error("[StaffSearch] error:", err)
      setStaffResults([])
    } finally {
      setIsStaffSearching(false)
    }
  }, [isStaffUser])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      runStaffSearch(query)
    }, 250)

    return () => window.clearTimeout(timer)
  }, [query, runStaffSearch])

  const filteredNavResults = useMemo(() => {
    if (staffFilter !== 'all' && staffFilter !== ('page' as StaffSearchEntityType)) return []
    return navResults
  }, [staffFilter, navResults])

  const filteredStaffResults = useMemo(() => {
    if (staffFilter === ('page' as StaffSearchEntityType)) return []
    if (staffFilter === 'all') return staffResults
    return staffResults.filter((result) => result.type === staffFilter)
  }, [staffFilter, staffResults])

  const didYouMean = useMemo(() => buildDidYouMean(query, filteredStaffResults), [query, filteredStaffResults])

  const handleSubmit = useCallback(() => {
    if (!query.trim() || !isStaffUser) return
    saveRecentSearch(query.trim())
    if (filteredNavResults[0]) {
      navigate(filteredNavResults[0].route)
    } else if (filteredStaffResults[0]) {
      navigate(filteredStaffResults[0].route)
    }
    onConsumeQuery()
    setStaffResults([])
    setNavResults([])
    onClose()
  }, [query, isStaffUser, filteredNavResults, filteredStaffResults, saveRecentSearch, navigate, onConsumeQuery, onClose])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape' && query) {
      e.preventDefault()
      onClearQuery()
    }
  }, [query, onClearQuery])

  useEffect(() => {
    registerKeyHandler?.(handleKeyDown)
    return () => registerKeyHandler?.(null)
  }, [registerKeyHandler, handleKeyDown])

  useEffect(() => {
    registerSubmitHandler?.(handleSubmit)
    return () => registerSubmitHandler?.(null)
  }, [registerSubmitHandler, handleSubmit])

  const handleNavClick = useCallback((route: string) => {
    saveRecentSearch(query)
    navigate(route)
    onClose()
  }, [saveRecentSearch, query, navigate, onClose])

  const handleResultClick = useCallback((route: string) => {
    saveRecentSearch(query)
    navigate(route)
    onClose()
  }, [saveRecentSearch, query, navigate, onClose])

  if (!query) return <></>

  return (
    <div className="space-y-3">
      {didYouMean && (
        <button type="button" onClick={() => setQuery(didYouMean)} className="flex items-center gap-2 text-sm text-earth-200 hover:text-white">
          <Sparkles className="w-4 h-4 text-brand-300" aria-hidden="true" />
          {t('components.headerSearch.didYouMean', 'Did you mean')} <span className="font-semibold">{didYouMean}</span>?
        </button>
      )}

      {/* Navigation / Pages results */}
      {filteredNavResults.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-medium text-earth-300 uppercase tracking-wider mb-2">{t('components.headerSearch.pagesAndTools', 'Pages & Tools')}</h4>
          <ul className="space-y-1">
            {filteredNavResults.slice(0, 5).map((nav) => (
              <li key={nav.route}>
                <button
                  type="button"
                  onClick={() => handleNavClick(nav.route)}
                  className="w-full text-left px-3 py-2 bg-earth-800 hover:bg-earth-700 rounded-lg"
                >
                  <p className="text-lsc-cream font-medium">{nav.title}</p>
                  <p className="text-xs text-earth-300">{t('components.headerSearch.resultTypePage', 'Page')} &bull; {nav.description}</p>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Data results */}
      {isStaffSearching ? (
        <p className="text-sm text-earth-300">{t('components.headerSearch.searchingPatronsItemsOrdersAnd')}</p>
      ) : filteredStaffResults.length > 0 ? (
        <ul className="space-y-2">
          {filteredStaffResults.slice(0, 20).map((result) => (
            <li key={result.id}>
              <button
                type="button"
                onClick={() => handleResultClick(result.route)}
                className="w-full text-left px-3 py-2 bg-earth-800 hover:bg-earth-700 rounded-lg"
              >
                <p className="text-lsc-cream font-medium">{result.title}</p>
                <p className="text-xs text-earth-300">{t(`components.headerSearch.typeLabel.${result.type}`, TYPE_LABELS[result.type])} • {result.subtitle}</p>
              </button>
            </li>
          ))}
        </ul>
      ) : filteredNavResults.length === 0 ? (
        <p className="text-sm text-earth-300">{t('components.headerSearch.noResultsYetTryBarcode')}</p>
      ) : null}
    </div>
  )
}
