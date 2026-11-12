/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Mail, Rss } from 'lucide-react'
import { useBranding } from '@/contexts/BrandingContext'
import { useTranslation } from '../../i18n/I18nContext'

const BlueskyIcon = ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 24 24" fill="currentColor" className={className} {...props}>
    <path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.785 2.627 3.601 3.476 6.153 3.13-4.4.647-8.28 2.757-3.6 9.42C7.5 28 17.5 18.5 12 10.8Zm0 0c1.087-2.114 4.046-6.053 6.798-7.995C21.434.944 22.439 1.266 23.098 1.565 23.861 1.908 24 3.08 24 3.768c0 .69-.378 5.65-.624 6.479-.785 2.627-3.601 3.476-6.153 3.13 4.4.647 8.28 2.757 3.6 9.42C16.5 28 6.5 18.5 12 10.8Z" />
  </svg>
)

const MastodonIcon = ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 24 24" fill="currentColor" className={className} {...props}>
    <path d="M23.268 5.313c-.35-2.578-2.617-4.61-5.304-5.004C17.51.242 15.792 0 11.813 0h-.03c-3.98 0-4.835.242-5.288.309C3.882.692 1.496 2.518.917 5.127.64 6.412.61 7.837.661 9.143c.074 1.874.088 3.745.26 5.611.118 1.24.325 2.47.62 3.68.55 2.237 2.777 4.098 4.96 4.857 2.336.792 4.849.923 7.256.38.265-.061.527-.132.786-.213.585-.184 1.27-.39 1.774-.753a.057.057 0 0 0 .023-.043v-1.809a.052.052 0 0 0-.02-.041.053.053 0 0 0-.046-.01 20.282 20.282 0 0 1-4.709.547c-2.73 0-3.463-1.284-3.674-1.818a5.593 5.593 0 0 1-.319-1.433.053.053 0 0 1 .066-.054 19.648 19.648 0 0 0 4.636.536c.562 0 1.124-.012 1.68-.047 2.11-.134 4.356-.413 4.737-3.636.015-.13.032-.263.032-.398 0-.12.048-2.585-.003-3.393ZM19.636 13.19H16.64V7.564c0-1.19-.494-1.793-1.488-1.793-1.097 0-1.646.717-1.646 2.134v2.926h-2.976V7.905c0-1.417-.55-2.134-1.646-2.134-.994 0-1.489.604-1.489 1.793v5.625H4.364V7.362c0-1.19.303-2.135.91-2.834.627-.7 1.447-1.058 2.464-1.058 1.177 0 2.067.45 2.654 1.35L12 6.878l1.608-2.058c.587-.9 1.477-1.35 2.654-1.35 1.017 0 1.837.359 2.464 1.058.607.7.91 1.644.91 2.834v5.828Z" />
  </svg>
)

type SocialLink = { href: string; label: string; icon: React.ComponentType<React.SVGProps<SVGSVGElement>>; verify: boolean }

export function FooterSocialLinks() {
  const branding = useBranding()
  const { t } = useTranslation()

  const links: SocialLink[] = [
    ...(branding.bluesky_url ? [{ href: branding.bluesky_url, label: 'Bluesky', icon: BlueskyIcon, verify: true }] : []),
    ...(branding.mastodon_url ? [{ href: branding.mastodon_url, label: 'Mastodon', icon: MastodonIcon, verify: true }] : []),
    { href: '/api/v1/blog/feed', label: t('footer.rss'), icon: Rss, verify: false },
    ...(branding.contact_email ? [{ href: `mailto:${branding.contact_email}`, label: t('footer.emailUs'), icon: Mail, verify: false }] : []),
  ]

  if (links.length === 0) return null

  return (
    <div className="flex items-center gap-1">
      {links.map(({ href, label, icon: Icon, verify }) => {
        const isMail = href.startsWith('mailto:')
        return (
          <a
            key={href}
            href={href}
            className="p-2 text-earth-300 hover:text-white transition-colors min-w-[44px] min-h-[44px] inline-flex items-center justify-center"
            aria-label={label}
            target={isMail ? undefined : '_blank'}
            rel={isMail ? undefined : (verify ? 'me noopener noreferrer' : 'noopener noreferrer')}
          >
            <Icon aria-hidden="true" className="w-4 h-4" />
          </a>
        )
      })}
    </div>
  )
}
