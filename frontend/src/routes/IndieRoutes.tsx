/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Routes, Route, Navigate } from 'react-router-dom'
import RequireAuth from '../components/RequireAuth'
import { lazyWithRetry } from '../utils/lazyWithRetry'

const IndieCatalogPage = lazyWithRetry(() => import('../pages/IndieCatalogPage'), 'indie-indie-catalog-page')
const IndieDiscoverPage = lazyWithRetry(() => import('../pages/IndieDiscoverPage'), 'indie-indie-discover-page')
const IndieBookDetailPage = lazyWithRetry(() => import('../pages/IndieBookDetailPage'), 'indie-indie-book-detail-page')
const IndieAuthorProfilePage = lazyWithRetry(() => import('../pages/IndieAuthorProfilePage'), 'indie-indie-author-profile-page')
const IndieAuthorBrowsePage = lazyWithRetry(() => import('../pages/IndieAuthorBrowsePage'), 'indie-indie-author-browse-page')
const IndieGenrePage = lazyWithRetry(() => import('../pages/IndieGenrePage'), 'indie-indie-genre-page')
const IndieCollectionPage = lazyWithRetry(() => import('../pages/IndieCollectionPage'), 'indie-indie-collection-page')
const IndieMyBorrowsPage = lazyWithRetry(() => import('../pages/IndieMyBorrowsPage'), 'indie-indie-my-borrows-page')
const IndieSavedBooksPage = lazyWithRetry(() => import('../pages/IndieSavedBooksPage'), 'indie-indie-saved-books-page')
const ReaderPage = lazyWithRetry(() => import('../pages/ReaderPage'), 'indie-reader-page')
const IndieReadingListsPage = lazyWithRetry(() => import('../pages/IndieReadingListsPage'), 'indie-indie-reading-lists-page')
const IndieReadingListDetailPage = lazyWithRetry(() => import('../pages/IndieReadingListDetailPage'), 'indie-indie-reading-list-detail-page')
const IndiePublicListPage = lazyWithRetry(() => import('../pages/IndiePublicListPage'), 'indie-indie-public-list-page')
const IndieVaultSubscribePage = lazyWithRetry(() => import('../pages/IndieVaultSubscribePage'), 'indie-indie-vault-subscribe-page')

function MetisLibRedirect({ path }: { path: string }) {
  window.location.href = `https://metislib.org${path}`
  return null
}

export default function IndieRoutes(): React.ReactElement {
  return (
    <Routes>
      {/* Patron-facing catalog (backed by MetisLib proxy) */}
      <Route index element={<IndieCatalogPage />} />
      <Route path="discover" element={<IndieDiscoverPage />} />
      <Route path="book/:slug" element={<IndieBookDetailPage />} />
      <Route path="author/browse" element={<IndieAuthorBrowsePage />} />
      <Route path="author/:slug" element={<IndieAuthorProfilePage />} />
      <Route path="genre/:genre" element={<IndieGenrePage />} />
      <Route path="collection/:slug" element={<IndieCollectionPage />} />
      <Route path="my-borrows" element={<RequireAuth><IndieMyBorrowsPage /></RequireAuth>} />
      <Route path="read/:ebookId" element={<RequireAuth><ReaderPage /></RequireAuth>} />
      <Route path="saved" element={<RequireAuth><IndieSavedBooksPage /></RequireAuth>} />

      {/* Author portal redirects to MetisLib */}
      <Route path="author/register" element={<MetisLibRedirect path="/author/register" />} />
      <Route path="dashboard" element={<MetisLibRedirect path="/author/dashboard" />} />
      <Route path="earnings" element={<MetisLibRedirect path="/author/earnings" />} />
      <Route path="analytics" element={<MetisLibRedirect path="/author/analytics" />} />
      <Route path="tax" element={<MetisLibRedirect path="/author/tax" />} />
      <Route path="book/new" element={<MetisLibRedirect path="/author/books/new" />} />
      <Route path="book/edit/:id" element={<MetisLibRedirect path="/author/books" />} />
      <Route path="author/edit" element={<MetisLibRedirect path="/author/profile" />} />

      {/* Reading lists */}
      <Route path="lists" element={<RequireAuth><IndieReadingListsPage /></RequireAuth>} />
      <Route path="lists/shared/:token" element={<IndiePublicListPage />} />
      <Route path="lists/:id" element={<RequireAuth><IndieReadingListDetailPage /></RequireAuth>} />

      {/* Indie Vault access card (tiers public; purchase gated in-page) */}
      <Route path="vault/subscribe" element={<IndieVaultSubscribePage />} />

      {/* Catch-all for removed pages */}
      <Route path="*" element={<Navigate to="/indie" replace />} />
    </Routes>
  )
}
