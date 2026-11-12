/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link, useNavigate } from 'react-router-dom'
import { Home, Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from '@/i18n'
import './NotFoundPage.css'

export default function NotFoundPage(): React.ReactElement {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const navigate = useNavigate()

  const handleSearch = (e: React.FormEvent): void => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/catalog?q=${encodeURIComponent(searchQuery)}`)
    }
  }

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4 py-12">
      {/* Bookshelf illustration */}
      <nav
        className="shelf"
        aria-roledescription="illustration"
        aria-label="A library shelf with cabinet doors opening to reveal books, with one book missing"
      >
        <Link to="/" className="book home-page">Home</Link>
        <Link to="/about" className="book about-us">About</Link>
        <Link to="/catalog" className="book catalog">Catalog</Link>
        <Link to="/events" className="book events">Events</Link>

        <span className="book not-found" aria-hidden="true" />

        <span className="door left" aria-hidden="true" />
        <span className="door right" aria-hidden="true" />
      </nav>

      {/* Message */}
      <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3 mt-8">
        {t('notFound.title')}
      </h1>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-md mb-8">
        The page you're looking for doesn't seem to be on our shelves.
      </p>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-4 mb-10">
        <Link
          to="/"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-xl transition-colors"
        >
          <Home aria-hidden="true" className="w-5 h-5" />
          {t('notFound.backToHome')}
        </Link>
        <Link
          to="/catalog"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream font-medium rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose-light transition-colors"
        >
          <Search aria-hidden="true" className="w-5 h-5" />
          {t('notFound.catalog')}
        </Link>
      </div>

      {/* Search */}
      <div className="w-full max-w-md">
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          Try searching for what you need:
        </p>
        <form onSubmit={handleSearch} className="flex gap-0 shadow-md rounded-xl overflow-hidden">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('notFound.searchBooksEventsResources')}
              aria-label={t('notFound.searchAriaLabel')}
              className="w-full pl-10 pr-4 py-3 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 border-0 focus:ring-0 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="px-5 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium transition-colors"
            aria-label={t('notFound.searchButtonAriaLabel')}
          >
            Search
          </button>
        </form>
      </div>
    </div>
  )
}
