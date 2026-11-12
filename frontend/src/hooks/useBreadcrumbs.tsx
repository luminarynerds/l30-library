/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useLocation, useParams } from 'react-router-dom'
import { useMemo } from 'react'
import { useTranslation } from '@/i18n'

export interface Breadcrumb {
  label: string
  path: string
  isCurrentPage?: boolean
}

export function useBreadcrumbs(): Breadcrumb[] {
  const location = useLocation()
  const params = useParams()
  const { t } = useTranslation()

  // eslint-disable-next-line complexity
  return useMemo(() => {
    const pathSegments = location.pathname.split('/').filter(Boolean)
    const breadcrumbs: Breadcrumb[] = [
      { label: t('navigation.home', 'Home'), path: '/' }
    ]

    // Build breadcrumbs based on route structure
    let currentPath = ''

    for (let i = 0; i < pathSegments.length; i++) {
      const segment = pathSegments[i]
      if (!segment) continue

      currentPath += `/${segment}`
      const isLast = i === pathSegments.length - 1

      // Map routes to readable labels
      const decoded = decodeURIComponent(segment)
      let label = decoded
        ? decoded.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
        : ''

      // Special cases for common routes
      switch (segment) {
        case 'catalog':
          label = t('navigation.catalog', 'Catalog')
          break
        case 'events':
          label = t('navigation.events', 'Events')
          break
        case 'programs':
          label = t('navigation.readingPrograms', 'Reading Programs')
          break
        case 'digital':
          label = t('navigation.digitalResources', 'Digital Resources')
          break
        case 'ai':
          label = t('navigation.aiTools', 'AI Tools')
          break
        case 'indie':
          label = t('breadcrumbs.indie', 'Indie eBooks')
          break
        case 'learn':
          label = t('navigation.learn', 'Learn')
          break
        case 'account':
          label = t('navigation.myAccount', 'My Account')
          break
        case 'staff':
          label = t('breadcrumbs.staff', 'Staff Portal')
          break
        case 'admin':
          label = t('breadcrumbs.admin', 'Admin Panel')
          break
        case 'board':
          label = t('breadcrumbs.board', 'Board Portal')
          break
        case 'accessibility':
          label = t('breadcrumbs.accessibility', 'Accessibility')
          break
        case 'faq':
          label = t('navigation.faq', 'FAQ')
          break
        case 'blog':
          label = t('navigation.blog', 'Field Notes')
          break
        case 'ask-librarian':
          label = t('navigation.askALibrarian', 'Ask a Librarian')
          break
        case 'public-reading-lists':
          label = t('navigation.publicReadingLists', 'Public Reading Lists')
          break
        case 'banned-books':
          label = t('navigation.intellectualFreedom', 'Intellectual Freedom')
          break
        case 'ban-tracker':
          label = t('breadcrumbs.banTracker', 'Ban Tracker')
          break
        case 'advocacy':
          label = t('breadcrumbs.advocacy', 'Advocacy Hub')
          break
        case 'about-us':
          label = t('breadcrumbs.aboutUs', 'About Us')
          break
        case 'our-story':
          label = t('breadcrumbs.ourStory', 'Our Story')
          break
        case 'donate':
          label = t('breadcrumbs.donate', 'Donate')
          break
        case 'discover':
          label = t('breadcrumbs.discover', 'Discover')
          break
        case 'privacy':
          label = t('breadcrumbs.privacy', 'Privacy Policy')
          break
        case 'terms':
          label = t('breadcrumbs.terms', 'Terms of Service')
          break
        case 'dmca':
          label = t('breadcrumbs.dmca', 'DMCA Notice')
          break
        case 'tech-support':
          label = t('navigation.techSupport', 'Tech Support')
          break
        case 'my-books':
          label = t('navigation.myBooks', 'My Books')
          break
        case 'my-shelf':
          label = t('navigation.myShelf', 'My Shelf')
          break
        case 'book-clubs':
          label = t('navigation.bookClubs', 'Book Clubs')
          break
        case 'learning-paths':
          label = t('breadcrumbs.learningPaths', 'Learning Paths')
          break
        case 'interlibrary-loan':
          label = t('breadcrumbs.interlibraryLoan', 'Interlibrary Loan')
          break
        case 'card-application':
        case 'apply-for-card':
          label = t('breadcrumbs.cardApplication', 'Library Card Application')
          break
        case 'course':
          // 'course' is an intermediate path segment (/learn/course/:id) with no
          // page of its own. When an id follows, skip it so the id terminal below
          // carries the "Course Details" label instead of producing a dead crumb.
          if (!isLast) {
            continue
          }
          label = t('breadcrumbs.courses', 'Courses')
          break
        case 'lesson':
          label = t('breadcrumbs.lesson', 'Lesson')
          break
        case 'item':
          label = t('breadcrumbs.itemDetails', 'Item Details')
          break
        case 'event':
          label = t('breadcrumbs.eventDetails', 'Event Details')
          break
        case 'reading-review':
          label = t('breadcrumbs.readingReview', 'Reading Review')
          break
        case 'indie-review':
          label = t('breadcrumbs.indieAuthors', 'Indie Authors')
          break
        case 'strategic':
          label = t('breadcrumbs.myGoals', 'My Goals')
          break
        case 'positivity':
          label = t('breadcrumbs.positivityHub', 'Positivity Hub')
          break
        case 'program-planning':
          label = t('breadcrumbs.programPlanning', 'Program Planning')
          break
        case 'cataloging':
          label = t('breadcrumbs.cataloging', 'Cataloging')
          break
        case 'acquisition':
          label = t('navigation.acquisitions', 'Acquisitions')
          break
        case 'inventory':
          label = t('breadcrumbs.inventory', 'Inventory')
          break
        case 'training':
          label = t('breadcrumbs.training', 'Training')
          break
        case 'circulation':
          label = t('navigation.circulation', 'Circulation')
          break
        case 'patrons':
          label = t('breadcrumbs.patrons', 'Patrons')
          break
        case 'reports':
          label = t('breadcrumbs.reports', 'Reports')
          break
      }

      // Skip path-structure segments that don't correspond to real pages
      if (segment === 'book' && pathSegments[i - 1] === 'indie') {
        continue
      }
      if (segment === 'author' && pathSegments[i - 1] === 'indie') {
        continue
      }
      if (segment === 'genre' && pathSegments[i - 1] === 'indie') {
        continue
      }

      // For slug-based detail pages (e.g. /indie/book/my-title-42),
      // strip the trailing numeric ID so breadcrumbs don't expose DB IDs
      const prevSegment = i > 0 ? pathSegments[i - 1] : ''
      if ((prevSegment === 'book' || prevSegment === 'author') && pathSegments[i - 2] === 'indie') {
        label = decoded.replace(/-\d+$/, '').replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
      }

      // Skip numeric IDs unless they're the last segment
      if (!isNaN(Number(segment)) && !isLast) {
        continue
      }

      // For numeric IDs at the end, label by the parent segment so detail pages
      // read as "Course Details" / "Path Details" instead of a bare "Details".
      if (!isNaN(Number(segment)) && isLast) {
        label =
          prevSegment === 'course'
            ? t('breadcrumbs.courseDetails', 'Course Details')
            : prevSegment === 'learning-paths'
              ? t('breadcrumbs.pathDetails', 'Path Details')
              : t('breadcrumbs.details', 'Details')
      }

      breadcrumbs.push({
        label,
        path: currentPath,
        isCurrentPage: isLast
      })
    }

    return breadcrumbs
  }, [location.pathname, params, t])
}
