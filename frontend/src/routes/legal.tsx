/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Route } from 'react-router-dom'
import { withAuth, withFeature } from './routeGuards'
import { lazyWithRetry } from '../utils/lazyWithRetry'

const LegalResourcesPage = lazyWithRetry(() => import('../pages/LegalResourcesPage'), 'legal-legal-resources-page')
const LegalCalculatorsPage = lazyWithRetry(() => import('../pages/LegalCalculatorsPage'), 'legal-legal-calculators-page')
const LegalDocumentWizardPage = lazyWithRetry(() => import('../pages/LegalDocumentWizardPage'), 'legal-legal-document-wizard-page')
const BannedBooksPage = lazyWithRetry(() => import('../pages/BannedBooksPage'), 'banned-books-page')
const PublicBanTrackerPage = lazyWithRetry(() => import('../pages/PublicBanTrackerPage'), 'public-ban-tracker-page')
const AdvocacyPage = lazyWithRetry(() => import('../pages/AdvocacyPage'), 'advocacy-page')
const BankruptcyFilingsPage = lazyWithRetry(() => import('../pages/BankruptcyFilingsPage'), 'legal-bankruptcy-filings-page')

export const legalRoutes: React.ReactElement = (
  <>
      <Route path="legal" element={withFeature('legal_services_enabled', <LegalResourcesPage />)} />
      <Route path="legal/calculators" element={withFeature('legal_services_enabled', <LegalCalculatorsPage />)} />
      <Route path="legal/wizard" element={withFeature('legal_services_enabled', withAuth(<LegalDocumentWizardPage />))} />
      <Route path="legal/bankruptcy" element={withFeature('legal_services_enabled', <BankruptcyFilingsPage />)} />
      <Route
        path="banned-books"
        element={withFeature('banned_books_tracking_enabled', <BannedBooksPage />)}
      />
      <Route
        path="intellectual-freedom"
        element={withFeature('banned_books_tracking_enabled', <BannedBooksPage />)}
      />
      <Route path="ban-tracker" element={<PublicBanTrackerPage />} />
      <Route path="advocacy" element={<AdvocacyPage />} />
  </>
)
