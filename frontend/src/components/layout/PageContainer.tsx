/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * PageContainer
 *
 * Width + horizontal gutters for a page's content column, pulled from the
 * canonical PAGE_WIDTH tiers. Vertical spacing is owned by the app shell
 * (Layout's main rail), so this adds none.
 *
 * Use this (or StandardPageLayout) instead of hardcoding
 * `max-w-* mx-auto px-4` on a page root.
 *
 * @example
 * <PageContainer>            // width="content" (1296px)
 * <PageContainer width="read">  // prose column
 */
import { type ElementType, type HTMLAttributes, type ReactNode } from 'react'

import { clsx } from '@/utils/helpers'
import { PAGE_WIDTH, type PageWidth } from './page-width'

interface PageContainerProps extends HTMLAttributes<HTMLElement> {
  /** Content-width tier (default: 'content') */
  width?: PageWidth
  /** Element/component to render as (default: 'div'). Use 'main' for the page landmark. */
  as?: ElementType
  children?: ReactNode
}

export default function PageContainer({
  as: Tag = 'div',
  width = 'content',
  className,
  children,
  ...rest
}: PageContainerProps): React.ReactElement {
  return (
    <Tag className={clsx(PAGE_WIDTH[width], 'mx-auto px-4 sm:px-6 lg:px-8', className)} {...rest}>
      {children}
    </Tag>
  )
}
