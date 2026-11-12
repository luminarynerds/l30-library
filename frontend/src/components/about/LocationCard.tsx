/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { MapPin, Phone, Clock, Accessibility, Route as RouteIcon } from 'lucide-react'
import { Link } from 'react-router-dom'

export interface LocationCardProps {
  name: string
  address?: string | null
  phone?: string | null
  hours?: string
  accessibility?: string
  mapImageSrc?: string | null
  mapAlt?: string
  /** Slug used to look up a fallback static map image at /images/maps/{slug}.webp */
  slug?: string
  /** When true, the card renders as a bookmobile: no address, route link instead */
  isBookmobile?: boolean
  /** Route link target for bookmobile cards (defaults to /locations) */
  bookmobileHref?: string
  /** Marks placeholder address/phone so they render with a TODO marker comment */
  isPlaceholder?: boolean
}

export default function LocationCard({
  name,
  address,
  phone,
  hours = 'See main branch hours',
  accessibility = 'Accessible entrance, parking on-site',
  mapImageSrc,
  mapAlt,
  slug,
  isBookmobile = false,
  bookmobileHref = '/locations',
  isPlaceholder = false,
}: LocationCardProps) {
  // TODO(sam): replace placeholder map image once real static maps are dropped in /public/images/maps/
  const resolvedMapSrc = mapImageSrc || (slug ? `/images/maps/${slug}.webp` : null)

  return (
    <article
      className="bg-lsc-cream dark:bg-earth-700 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden flex flex-col"
      aria-label={name}
    >
      {/* Map / route visual — 16:9 */}
      <div className="relative w-full aspect-video bg-sage-50 dark:bg-earth-800 overflow-hidden">
        {isBookmobile ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
            <RouteIcon className="w-10 h-10 text-sage-600 dark:text-sage-400" aria-hidden="true" />
            <span className="text-sm font-medium">Routes vary — see schedule</span>
          </div>
        ) : resolvedMapSrc ? (
          <img
            src={resolvedMapSrc}
            alt={mapAlt || `Map showing the location of ${name}`}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div
            className="absolute inset-0 flex items-center justify-center text-lsc-dark/40 dark:text-lsc-cream/40"
            aria-label={`Map placeholder for ${name}`}
            role="img"
          >
            <MapPin className="w-10 h-10" aria-hidden="true" />
          </div>
        )}
      </div>

      <div className="p-5 flex-1 flex flex-col gap-3">
        <h3 className="font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream">{name}</h3>

        {isBookmobile ? (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-start gap-2">
            <RouteIcon className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
            <span>
              Routes vary —{' '}
              <Link to={bookmobileHref} className="text-lsc-rose hover:underline">
                see schedule
              </Link>
            </span>
          </p>
        ) : (
          <>
            {address && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-start gap-2">
                <MapPin className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
                {/* TODO(sam): replace placeholder address */}
                <span>{address}</span>
              </p>
            )}
            {phone && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-start gap-2">
                <Phone className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
                {/* TODO(sam): replace placeholder phone */}
                <a href={`tel:${phone.replace(/\D/g, '')}`} className="hover:text-lsc-rose hover:underline">
                  {phone}
                </a>
              </p>
            )}
          </>
        )}

        {!isBookmobile && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-start gap-2">
            <Clock className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
            <span>{hours}</span>
          </p>
        )}

        <p
          className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-start gap-2 mt-auto"
          aria-label={`Accessibility: ${accessibility}`}
        >
          <Accessibility className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
          <span>{accessibility}</span>
        </p>

        {isPlaceholder && (
          <p className="sr-only">Placeholder location information — real details coming soon.</p>
        )}
      </div>
    </article>
  )
}
