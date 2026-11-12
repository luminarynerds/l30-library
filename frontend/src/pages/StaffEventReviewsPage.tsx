/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ReviewModerationQueue } from "@/components/ReviewModerationQueue"
import PageContainer from '@/components/layout/PageContainer'

export default function StaffEventReviewsPage(): React.ReactElement {
  return (
    <PageContainer className="py-6">
      <header className="mb-6">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Event Reviews
        </h1>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          Patron reviews of library events. Approved reviews are public; hide any that violate community guidelines.
        </p>
      </header>
      <ReviewModerationQueue />
    </PageContainer>
  )
}
