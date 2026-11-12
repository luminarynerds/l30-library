/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Public A-Z Database List Page
 *
 * Displays available databases for patrons to access.
 * Features:
 * - Category filtering
 * - Search functionality
 * - Featured databases section
 * - Proxy URL generation on click
 */

import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useBranding } from '@/contexts/BrandingContext'
import {
  Search,
  Database,
  ExternalLink,
  Star,
  Filter,
  BookOpen,
  Globe,
  ChevronDown,
  Info,
} from 'lucide-react'

import {
  DatabaseCardSkeletonGrid,
  DatabaseItemSkeletonList,
} from '../components/skeletons'
import {
  getPublicDatabaseList,
  logDatabaseAccess,
  getCategoryDisplayName,
  type PublicDatabase,
  type DatabaseCategory,
} from '../api/databases-api'
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

export default function DatabasesPage(): React.ReactElement {
  const branding = useBranding()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [showFeaturedOnly, setShowFeaturedOnly] = useState(false)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  // Fetch database list
  const { data, isLoading, error } = useQuery({
    queryKey: ['public-databases', selectedCategory, searchQuery, showFeaturedOnly],
    queryFn: () =>
      getPublicDatabaseList({
        ...(selectedCategory ? { category: selectedCategory } : {}),
        ...(searchQuery ? { search: searchQuery } : {}),
        ...(showFeaturedOnly ? { featured_only: showFeaturedOnly } : {}),
      }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Group databases by first letter for A-Z navigation
  const databases = data?.databases
  const groupedDatabases = useMemo(() => {
    if (!databases) return {}

    const groups: Record<string, PublicDatabase[]> = {}
    databases.forEach((db) => {
      const letter = db.name.charAt(0).toUpperCase()
      if (!groups[letter]) groups[letter] = []
      groups[letter]!.push(db)
    })

    return groups
  }, [databases])

  // Get featured databases
  const featuredDatabases = useMemo(() => {
    return data?.databases.filter((db) => db.is_featured) || []
  }, [data?.databases])

  // Handle database click - log access and open URL
  const handleDatabaseClick = async (db: PublicDatabase) => {
    try {
      const result = await logDatabaseAccess(db.id)
      window.open(result.url, '_blank', 'noopener,noreferrer')
    } catch {
      // Fallback to proxy_url if logging fails
      window.open(db.proxy_url, '_blank', 'noopener,noreferrer')
    }
  }

  // Scroll to letter section
  const scrollToLetter = (letter: string) => {
    const element = document.getElementById(`section-${letter}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  if (error) {
    return (
      <PageContainer className="py-8">
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-6 text-center" role="alert">
          <h2 className="font-serif text-lg font-semibold text-status-danger-800 dark:text-status-danger-200">
            Unable to load databases
          </h2>
          <p className="mt-2 text-status-danger-600 dark:text-status-danger-300">
            Please try again later or contact the library for assistance.
          </p>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer className="py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
          <Database className="h-8 w-8 text-lsc-rose dark:text-lsc-rose-light" />
          Research Databases
        </h1>
        <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">
          Access our collection of online databases, journals, and research tools.
          Use your library card to access these resources from home.
        </p>
      </div>

      {/* Search and Filters */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <input
              type="text"
              placeholder={t('placeholder.databases.searchDatabases')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label={t('aria.databases.searchDatabases')}
              className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>

          {/* Category Filter */}
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              aria-label={t('aria.training.filterByCategory')}
              className="pl-10 pr-8 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent appearance-none cursor-pointer min-w-[200px]"
            >
              <option value="">All Categories</option>
              {data?.categories.map((cat) => (
                <option key={cat} value={cat}>
                  {getCategoryDisplayName(cat as DatabaseCategory)}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70 pointer-events-none" />
          </div>

          {/* Featured Toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showFeaturedOnly}
              onChange={(e) => setShowFeaturedOnly(e.target.checked)}
              className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light border-lsc-border dark:border-earth-700 rounded focus:ring-lsc-rose"
            />
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
              <Star className="h-4 w-4 text-status-warning-500" />
              Featured Only
            </span>
          </label>
        </div>
      </div>

      {/* Screen reader announcement for search/filter results */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {isLoading
          ? 'Loading databases...'
          : data
            ? `${data.databases.length} ${data.databases.length === 1 ? 'database' : 'databases'} found`
            : ''}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="space-y-8">
          {/* Featured section skeleton */}
          <div>
            <div className="h-7 w-48 bg-earth-200 dark:bg-earth-700 rounded mb-4 motion-safe:animate-pulse motion-reduce:animate-none" />
            <DatabaseCardSkeletonGrid count={3} />
          </div>
          {/* Database list skeleton */}
          <div>
            <div className="h-8 w-12 bg-earth-200 dark:bg-earth-700 rounded mb-4 motion-safe:animate-pulse motion-reduce:animate-none" />
            <DatabaseItemSkeletonList count={5} />
          </div>
        </div>
      )}

      {/* Featured Databases */}
      {!isLoading && featuredDatabases.length > 0 && !showFeaturedOnly && !searchQuery && (
        <div className="mb-8">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <Star className="h-5 w-5 text-status-warning-500" />
            Featured Databases
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {featuredDatabases.slice(0, 6).map((db) => (
              <DatabaseCard
                key={db.id}
                database={db}
                onClick={() => handleDatabaseClick(db)}
                featured
              />
            ))}
          </div>
        </div>
      )}

      {/* A-Z Navigation */}
      {!isLoading && data && Object.keys(groupedDatabases).length > 0 && (
        <div className="mb-6 flex flex-wrap gap-1">
          {'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').map((letter) => (
            <button
              key={letter}
              onClick={() => scrollToLetter(letter)}
              disabled={!groupedDatabases[letter]}
              className={`w-8 h-8 rounded font-medium text-sm transition-colors ${
                groupedDatabases[letter]
                  ? 'bg-earth-100 dark:bg-earth-800 text-lsc-rose dark:text-lsc-rose-light/80 hover:bg-earth-200 dark:hover:bg-earth-800'
                  : 'bg-earth-100 dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
              }`}
            >
              {letter}
            </button>
          ))}
        </div>
      )}

      {/* Database List by Letter */}
      {!isLoading && data && (
        <div className="space-y-8">
          {Object.keys(groupedDatabases)
            .sort()
            .map((letter) => (
              <div key={letter} id={`section-${letter}`}>
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream border-b border-lsc-border dark:border-earth-700 pb-2 mb-4">
                  {letter}
                </h2>
                <div className="space-y-3">
                  {groupedDatabases[letter]!.map((db) => (
                    <DatabaseListItem
                      key={db.id}
                      database={db}
                      onClick={() => handleDatabaseClick(db)}
                      expanded={expandedId === db.id}
                      onToggleExpand={() =>
                        setExpandedId(expandedId === db.id ? null : db.id)
                      }
                    />
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && data && data.databases.length === 0 && (
        <div className="text-center py-12">
          <Database className="h-16 w-16 text-earth-300 dark:text-earth-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
            No databases found
          </h3>
          <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">
            Try adjusting your search or filters.
          </p>
        </div>
      )}

      {/* Help Section */}
      <div className="mt-12 bg-earth-50 dark:bg-earth-800/20 rounded-lg p-6">
        <h2 className="font-serif text-lg font-semibold text-earth-900 dark:text-earth-200 flex items-center gap-2">
          <Info className="h-5 w-5" />
          Need Help?
        </h2>
        <div className="mt-3 text-earth-800 dark:text-lsc-rose-light/80 space-y-2">
          <p>
            <strong>From home:</strong> You'll need your library account (email and
            password) to access these databases remotely.
          </p>
          <p>
            <strong>At the library:</strong> Access is automatic on library
            computers.
          </p>
          <p>
            <strong>Questions?</strong> Contact the Reference Desk at {branding.phone} or{' '}
            <a
              href={`mailto:${branding.contact_email}`}
              className="underline hover:no-underline"
            >
              {branding.contact_email}
            </a>
          </p>
        </div>
      </div>
    </PageContainer>
  )
}

// ============ SUB-COMPONENTS ============

interface DatabaseCardProps {
  database: PublicDatabase
  onClick: () => void
  featured?: boolean
}

function DatabaseCard({
  database,
  onClick,
  featured,
}: DatabaseCardProps): React.ReactElement {
  return (
    <button
      onClick={onClick}
      className={`text-left p-4 rounded-lg border transition-all hover:shadow-md ${
        featured
          ? 'bg-gradient-to-br from-yellow-50 to-status-warning-50 dark:from-yellow-900/20 dark:to-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800 hover:border-status-warning-300'
          : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 hover:border-lsc-border'
      }`}
    >
      <div className="flex items-start gap-3">
        {database.logo_url ? (
          <img
            src={database.logo_url}
            alt={`${database.name} logo`}
            className="w-12 h-12 object-contain rounded"
          />
        ) : (
          <div className="w-12 h-12 bg-earth-100 dark:bg-earth-800 rounded flex items-center justify-center">
            <BookOpen className="h-6 w-6 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            {database.name}
            <ExternalLink className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2 mt-1" title={database.description || 'Click to access this database.'}>
            {database.description || 'Click to access this database.'}
          </p>
          <span className="inline-block mt-2 text-xs px-2 py-1 bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded">
            {getCategoryDisplayName(database.category)}
          </span>
        </div>
      </div>
    </button>
  )
}

interface DatabaseListItemProps {
  database: PublicDatabase
  onClick: () => void
  expanded: boolean
  onToggleExpand: () => void
}

function DatabaseListItem({
  database,
  onClick,
  expanded,
  onToggleExpand,
}: DatabaseListItemProps): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
      <div className="flex items-center p-4">
        {/* Logo/Icon */}
        {database.logo_url ? (
          <img
            src={database.logo_url}
            alt={`${database.name} logo`}
            className="w-10 h-10 object-contain rounded mr-4"
          />
        ) : (
          <div className="w-10 h-10 bg-earth-100 dark:bg-earth-800 rounded flex items-center justify-center mr-4">
            <Globe className="h-5 w-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
        )}

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              {database.name}
            </h3>
            {database.is_featured && (
              <Star className="h-4 w-4 text-status-warning-500 fill-current" />
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-1">
            <span className="text-xs px-2 py-0.5 bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded whitespace-nowrap flex-shrink-0">
              {getCategoryDisplayName(database.category)}
            </span>
            {database.subjects.slice(0, 2).map((subject) => (
              <span
                key={subject}
                className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap flex-shrink-0"
              >
                {subject}
              </span>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 ml-4">
          <button
            onClick={onToggleExpand}
            className="p-2 text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200"
            aria-label={expanded ? 'Hide details' : 'Show details'}
          >
            <Info className="h-5 w-5" />
          </button>
          <button
            onClick={onClick}
            className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
          >
            Access
            <ExternalLink className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-earth-100 dark:border-earth-700 pt-3">
          {database.description && (
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-3">
              {database.description}
            </p>
          )}
          <div className="flex flex-wrap gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {database.help_url && (
              <a
                href={database.help_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                Help Guide
              </a>
            )}
            {database.mobile_url && (
              <a
                href={database.mobile_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                Mobile Version
              </a>
            )}
            {database.simultaneous_users && (
              <span>
                {database.simultaneous_users} simultaneous user
                {database.simultaneous_users > 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
