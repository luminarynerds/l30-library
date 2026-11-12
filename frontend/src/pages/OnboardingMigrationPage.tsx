/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Library-admin first-run data-migration entry point (NOT patron onboarding).
 *
 * Despite the `Onboarding*` filename and the `/onboarding/migration` route, this
 * page is a welcome-framed wrapper around the library-admin MigrationWizardPage
 * used to import legacy library data on first deploy. The patron onboarding flow
 * lives at /onboarding/welcome -> /onboarding/preferences -> /onboarding/branch ->
 * /onboarding/tour -> /onboarding/complete (see frontend/src/routes/public.tsx).
 *
 * A rename to AdminInitialMigrationPage + route /admin/initial-migration would
 * be clearer but has non-trivial blast radius (hardcoded redirect in
 * AdminMigrationWizardPage.tsx:60, any external bookmarks/emails). Deferred.
 */
import { Library } from 'lucide-react'
import MigrationWizardPage from './MigrationWizardPage'
import { useTranslation } from '@/i18n'

export default function OnboardingMigrationPage() {
  const { t } = useTranslation()
  return (
    <div className="min-h-screen bg-gradient-to-b from-lsc-rose/10 to-lsc-cream dark:from-gray-800 dark:to-gray-900">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-lsc-rose to-orange-600 text-white py-12 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <Library className="w-12 h-12 mx-auto mb-4 opacity-90" />
          <h1 className="font-serif text-4xl font-bold mb-3">{t('onboardingMigration.welcomeToLibrary')}</h1>
          <p className="text-lg opacity-90 mb-2">
            Let's import your library's data from your previous system
          </p>
          <p className="text-sm opacity-75">
            This wizard will guide you through a quick and easy migration process
          </p>
        </div>
      </div>

      {/* Wizard Content */}
      <div className="py-8">
        <MigrationWizardPage />
      </div>

      {/* Footer Help */}
      <div className="bg-lsc-cream dark:bg-earth-800 border-t border-lsc-border dark:border-earth-700 py-8 px-4 mt-12">
        <div className="max-w-2xl mx-auto text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <p>
            Need help? Check out our{' '}
            <a href="/help" className="text-lsc-rose hover:underline">
              migration guide
            </a>{' '}
            or contact support.
          </p>
        </div>
      </div>
    </div>
  )
}
