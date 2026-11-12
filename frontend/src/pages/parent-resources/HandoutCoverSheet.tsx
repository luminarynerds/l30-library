/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'

export function HandoutCoverSheet() {
  const { t } = useTranslation()
  const branding = useBranding()

  const addressLine = [
    branding.address_line1,
    branding.address_line2,
    [branding.city, branding.state].filter(Boolean).join(', '),
    branding.zip_code,
  ]
    .filter(Boolean)
    .join(', ')

  return (
    <div
      className="handout-cover-sheet hidden print:block"
      data-testid="handout-cover-sheet"
    >
      <div className="handout-cover-inner">
        <h1 className="handout-cover-title">
          {t('parentResources.handout.coverSheet.title')}
        </h1>
        {branding.library_name && (
          <p className="handout-cover-library">
            {t('parentResources.handout.coverSheet.libraryLine', {
              libraryName: branding.library_name,
            })}
          </p>
        )}
        <p className="handout-cover-prompt">
          {t('parentResources.handout.coverSheet.contactPrompt')}
        </p>
        <dl className="handout-cover-contact">
          {branding.phone && (
            <>
              <dt>{t('parentResources.handout.coverSheet.phoneLabel')}</dt>
              <dd>{branding.phone}</dd>
            </>
          )}
          {addressLine && (
            <>
              <dt>{t('parentResources.handout.coverSheet.addressLabel')}</dt>
              <dd>{addressLine}</dd>
            </>
          )}
          {branding.contact_email && (
            <>
              <dt>{t('parentResources.handout.coverSheet.emailLabel')}</dt>
              <dd>{branding.contact_email}</dd>
            </>
          )}
        </dl>
      </div>
    </div>
  )
}
