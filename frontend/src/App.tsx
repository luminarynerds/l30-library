/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { lazy, Suspense } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { BrandingProvider } from './contexts/BrandingContext'
import { EssentialsModeProvider } from './contexts/EssentialsModeContext'
import { PreferencesProvider } from './contexts/PreferencesContext'
import { OrganizationFeaturesProvider } from './contexts/OrganizationFeaturesContext'
import { OnboardingProvider } from './contexts/OnboardingContext'
import { UnifiedAccessibilityProvider } from './features/accessibility'
import { I18nProvider, LanguagePreferenceSync } from './i18n/I18nContext'
import { PanicAlertProvider } from './contexts/PanicAlertContext'
import { ToastProvider } from './hooks/useToast'
import PanicAlertOverlay from "./components/PanicAlertOverlay"
import { AdvancedSearchProvider } from './contexts/AdvancedSearchContext'
import AppRoutes from './components/AppRoutes'

// AccessibilityOverlay renders nothing until the user opens the a11y panel,
// so its tree (plus focus-trap / tabbable / radix-menu) doesn't need to be
// in the entry chunk. Suspense fallback is null because there is no visible
// surface to placeholder during the brief chunk fetch.
const AccessibilityOverlay = lazy(() =>
  import('./features/accessibility/components/AccessibilityOverlay').then((m) => ({
    default: m.AccessibilityOverlay,
  })),
)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes default
      gcTime: 1000 * 60 * 30, // 30 minutes - extended cache for offline-first support
      retry: (failureCount: number, error: Error) => {
        // Don't retry auth errors or 404s
        if (error && typeof error === 'object' && 'status' in error) {
          const status = (error as { status: number }).status
          if (status === 401 || status === 403 || status === 404 || status === 429) return false
        }
        return failureCount < 2
      },
      refetchOnWindowFocus: false, // Polling handles freshness; tab-switch refetches waste bandwidth
      refetchOnReconnect: true, // Only refetch stale data on reconnect
      networkMode: 'offlineFirst', // Serve cached data immediately, revalidate in background
    },
    mutations: {
      retry: 1,
      networkMode: 'offlineFirst',
    },
  },
})

// Bridges auth state (only visible below AuthProvider) to the account-language
// restore in I18nContext (mounted above it).
function AuthLanguageSync(): React.ReactElement {
  const { isAuthenticated } = useAuth()
  return <LanguagePreferenceSync isAuthenticated={isAuthenticated} />
}

export default function App(): React.ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <BrandingProvider>
      <I18nProvider>
        <AuthProvider>
          <AuthLanguageSync />
          <EssentialsModeProvider>
            <PanicAlertProvider>
              <OnboardingProvider>
                <OrganizationFeaturesProvider>
                <UnifiedAccessibilityProvider enableLegacyMigration={true}>
                  <ToastProvider>
                  <PreferencesProvider>
                    <AdvancedSearchProvider>
                      <PanicAlertOverlay />
                      <AppRoutes />
                      <Suspense fallback={null}>
                        <AccessibilityOverlay />
                      </Suspense>
                    </AdvancedSearchProvider>
                  </PreferencesProvider>
                  </ToastProvider>
                </UnifiedAccessibilityProvider>
              </OrganizationFeaturesProvider>
            </OnboardingProvider>
          </PanicAlertProvider>
          </EssentialsModeProvider>
        </AuthProvider>
      </I18nProvider>
      </BrandingProvider>
    </QueryClientProvider>
  )
}
