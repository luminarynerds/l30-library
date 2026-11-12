/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Navigate, Route } from 'react-router-dom'
import { lazyWithRetry } from '../utils/lazyWithRetry'

const DiscoverPage = lazyWithRetry(() => import('../pages/DiscoverPage'), 'catalog-discover-page')
const CatalogPage = lazyWithRetry(() => import('../pages/CatalogPage'), 'catalog-catalog-page')
const BibframeCatalogPage = lazyWithRetry(() => import('../pages/BibframeCatalogPage'), 'catalog-bibframe-catalog-page')
const CatalogItemPage = lazyWithRetry(() => import('../pages/CatalogItemPage'), 'catalog-catalog-item-page')
const SemanticSearchPage = lazyWithRetry(() => import('../pages/SemanticSearchPage'), 'catalog-semantic-search-page')
const SiteSearchPage = lazyWithRetry(() => import('../pages/SiteSearchPage'), 'catalog-site-search-page')
const FederatedSearchPage = lazyWithRetry(() => import('../pages/FederatedSearchPage'), 'catalog-federated-search-page')
const EbooksPage = lazyWithRetry(() => import('../pages/EbooksPage'), 'catalog-ebooks-page')
const EbookDetailPage = lazyWithRetry(() => import('../pages/EbookDetailPage'), 'catalog-ebook-detail-page')
const MyEbooksPage = lazyWithRetry(() => import('../pages/MyEbooksPage'), 'catalog-my-ebooks-page')
const ReadingShelfPage = lazyWithRetry(() => import('../pages/ReadingShelfPage'), 'catalog-reading-shelf-page')
const EbookCollectionsPage = lazyWithRetry(() => import('../pages/EbookCollectionsPage'), 'catalog-ebook-collections-page')
const MoodResultsPage = lazyWithRetry(() => import('../pages/catalog/components/MoodResultsPage'), 'catalog-mood-results-page')
const BrowseSeriesPage = lazyWithRetry(() => import('../pages/catalog/BrowseSeriesPage'), 'catalog-browse-series-page')

export const catalogRoutes: React.ReactElement = (
  <>
      <Route path="discover" element={<DiscoverPage />} />
      <Route path="catalog" element={<CatalogPage />} />
      <Route path="catalog/bibframe" element={<BibframeCatalogPage />} />
      <Route path="catalog/search" element={<SemanticSearchPage />} />
      <Route path="catalog/mood/:slug" element={<MoodResultsPage />} />
      <Route path="catalog/series" element={<BrowseSeriesPage />} />
      <Route path="catalog/partner-search" element={<FederatedSearchPage />} />
      <Route path="catalog/:id" element={<CatalogItemPage />} />
      <Route path="search" element={<SiteSearchPage />} />
      <Route path="my-books" element={<Navigate to="/account?tab=ebooks" replace />} />
      <Route path="my-shelf" element={<ReadingShelfPage />} />
      <Route path="ebooks" element={<EbooksPage />} />
      <Route path="ebooks/collections" element={<EbookCollectionsPage />} />
      <Route path="ebooks/my" element={<MyEbooksPage />} />
      <Route path="ebooks/:id" element={<EbookDetailPage />} />
  </>
)
