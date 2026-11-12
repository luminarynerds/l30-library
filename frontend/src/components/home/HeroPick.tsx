/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Patron-facing "hero pick" block.
 *
 * Renders the editor-curated Hero Pick returned by GET /home/page (PR #670).
 * Markdown is restricted to inline emphasis + paragraphs — the editor in
 * PR #671 enforces the same constraint, so we trust the payload here and
 * lean on react-markdown's default sanitization.
 */
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import type { HeroPickRead } from '@/api/home'
import { coverProxyUrl, buildCoverAlt } from '@/pages/catalog/utils/catalogHelpers'
import CatalogItemThumbnail from '@/pages/catalog/components/CatalogItemThumbnail'
import { useTranslation } from '@/i18n/I18nContext'

interface HeroPickProps {
  hero: HeroPickRead
}

export default function HeroPick({ hero }: HeroPickProps): React.ReactElement {
  const { t } = useTranslation()
  const { item, annotation_md, cta_label, cta_href } = hero
  const href = cta_href && cta_href.trim().length > 0 ? cta_href : `/catalog/${item.id}`
  const alt = buildCoverAlt(item.title, item.author, item.item_type)
  const isHoldCta = /hold/i.test(cta_label)
  // The cover proxy 404s for items without a cover; fall back to the
  // generative thumbnail instead of leaving a broken image.
  const [imageError, setImageError] = useState(false)

  return (
    <article className="rounded-xl bg-lsc-white dark:bg-earth-800/40 border border-lsc-border dark:border-earth-700 overflow-hidden">
      <div className="grid grid-cols-1 gap-5 p-5 sm:grid-cols-[minmax(0,12rem)_minmax(0,1fr)] sm:gap-6 md:p-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] lg:gap-8">
        <div className="flex justify-start">
          <div className="w-full max-w-[10rem] sm:max-w-none aspect-[2/3] rounded-xl overflow-hidden bg-lsc-cream dark:bg-earth-700 border border-lsc-border dark:border-earth-700 shadow-sm lg:max-w-[18rem]">
            {imageError ? (
              <CatalogItemThumbnail
                title={item.title}
                {...(item.item_type ? { itemType: item.item_type } : {})}
                size="lg"
                className="w-full"
              />
            ) : (
              <img
                src={coverProxyUrl(item.id)}
                alt={alt}
                loading="lazy"
                className="w-full h-full object-cover"
                onError={() => setImageError(true)}
              />
            )}
          </div>
        </div>
        <div className="flex min-w-0 flex-col justify-center gap-3 md:gap-4">
          <h2 className="font-serif text-2xl md:text-4xl text-lsc-dark dark:text-lsc-cream leading-tight [overflow-wrap:anywhere]">
            {item.title}
          </h2>
          {item.author && (
            <p className="text-base text-earth-700 dark:text-earth-300">{item.author}</p>
          )}
          <div className="prose prose-earth dark:prose-invert max-w-none text-sm md:text-base text-earth-700 dark:text-earth-200">
            <ReactMarkdown>{annotation_md}</ReactMarkdown>
          </div>
          <div className="pt-1 space-y-2">
            <Link
              to={href}
              className="inline-flex min-h-[44px] items-center gap-2 px-5 py-3 rounded-full bg-lsc-rose text-white font-semibold text-sm hover:bg-lsc-rose/90 motion-safe:hover:scale-[1.02] motion-safe:transition-transform focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
            >
              {cta_label}
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
            {isHoldCta && (
              <p className="text-sm text-earth-600 dark:text-earth-400">
                {t('home.heroPick.holdHint', 'Choose pickup details on the next page.')}
              </p>
            )}
          </div>
        </div>
      </div>
    </article>
  )
}
