/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useLibraryContact } from '@/hooks/useLibraryContact'
import { useBranding } from '@/contexts/BrandingContext'

export function JsonLdLibrary() {
  const branding = useBranding()
  const contact = useLibraryContact()

  const jsonLd = (() => {
    const sameAs = [branding.bluesky_url, branding.mastodon_url].filter(Boolean)
    const hasAddress = contact.address_line1 || contact.city
    return {
      '@context': 'https://schema.org',
      '@type': 'Library',
      name: branding.library_name,
      ...(branding.domain ? { url: branding.domain } : {}),
      ...(contact.phone ? { telephone: contact.phone } : {}),
      ...(branding.contact_email ? { email: branding.contact_email } : {}),
      ...(hasAddress
        ? {
            address: {
              '@type': 'PostalAddress',
              ...(contact.address_line1 ? { streetAddress: contact.address_line1 } : {}),
              ...(contact.city ? { addressLocality: contact.city } : {}),
              ...(contact.state ? { addressRegion: contact.state } : {}),
              ...(contact.zip_code ? { postalCode: contact.zip_code } : {}),
            },
          }
        : {}),
      ...(sameAs.length ? { sameAs } : {}),
    }
  })()

  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
}
