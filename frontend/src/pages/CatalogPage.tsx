/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CatalogPageContent } from './catalog/components'
import { usePageTitle } from '@/hooks/usePageTitle'

export default function CatalogPage(): React.ReactElement {
  usePageTitle('Browse the Catalog')
  return <CatalogPageContent />
}
