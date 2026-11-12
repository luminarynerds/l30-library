/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { useBranding } from '@/contexts/BrandingContext'
import { useTranslation } from '../../i18n/I18nContext'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'

export function FooterDemoNotice() {
  const branding = useBranding()
  const { t } = useTranslation()
  const { isFeatureEnabled } = useOrganizationFeatures()

  if (!branding.is_demo) return null

  const showPatronLink = isFeatureEnabled('collection_management_enabled')

  return (
    <div className="border-t border-earth-800 pt-4 pb-4">
      <p className="text-xs text-earth-300">
        {t('footer.demoNotice')}{' '}
        {showPatronLink && (
          <Link to="/catalog" className="text-earth-300 hover:text-white transition-colors underline">
            {t('footer.exploreAsPatron')}
          </Link>
        )}
        {showPatronLink && ' · '}
        <Link to="/demo/dashboard" className="text-earth-300 hover:text-white transition-colors underline">
          {t('footer.imADirector')}
        </Link>
      </p>
    </div>
  )
}
