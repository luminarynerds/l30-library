/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Shared content rating mapping — backend values to display labels + colors.
 *
 * Backend enum (ContentRating): g, pg, pg13, r, nc17, e, e10, t, m
 * Frontend consumes these via the `content_rating` field on ebook responses.
 */
import type { ContentRating } from '@/api/indie-catalog-api'

export interface RatingInfo {
  label: string
  description: string
  color: string
}

export const CONTENT_RATING_MAP: Record<ContentRating, RatingInfo> = {
  g:    { label: 'All Ages',  description: 'Content rating: All Ages',                        color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  e:    { label: 'Everyone',  description: 'Content rating: Everyone',                        color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  e10:  { label: '10+',       description: 'Content rating: Everyone 10+',                    color: 'bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-200' },
  pg:   { label: 'PG',        description: 'Content rating: Parental Guidance suggested',     color: 'bg-status-info-100 text-status-info-700 dark:bg-status-info-900 dark:text-status-info-200' },
  pg13: { label: 'PG-13',     description: 'Content rating: Parents strongly cautioned (13+)', color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  t:    { label: 'Teen',      description: 'Content rating: Teen (13+)',                      color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  r:    { label: 'R',         description: 'Content rating: Restricted (17+)',                color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  m:    { label: 'Mature',    description: 'Content rating: Mature (18+)',                    color: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' },
  nc17: { label: 'NC-17',     description: 'Content rating: Adults only (18+)',               color: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' },
  general: { label: 'All Ages', description: 'Content rating: All Ages',                      color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  teen:    { label: 'Teen',     description: 'Content rating: Teen (13+)',                    color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  mature:  { label: 'Mature',   description: 'Content rating: Mature (18+)',                  color: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' },
  ao:      { label: 'Adults Only', description: 'Content rating: Adults Only (18+)',            color: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' },
  explicit: { label: 'Explicit', description: 'Content rating: Explicit',                       color: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' },
  clean:   { label: 'Clean',    description: 'Content rating: Clean',                           color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  unrated: { label: 'Unrated',  description: 'Content rating: Unrated',                         color: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300' },
  not_rated: { label: 'Not Rated', description: 'Content rating: Not Rated',                    color: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300' },
}

export const UNRATED: RatingInfo = {
  label: 'Unrated',
  description: 'Content rating: Unrated',
  color: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300',
}

export function getRatingInfo(rating: string | undefined | null): RatingInfo {
  if (!rating) return UNRATED
  return CONTENT_RATING_MAP[rating as ContentRating] ?? UNRATED
}
