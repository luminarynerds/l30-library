/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render as rtlRender, type RenderOptions } from "@testing-library/react"
import { screen } from "@testing-library/react"
import type { ReactElement, ReactNode } from 'react'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'
import { ClosuresList } from '../ClosuresList'

// ClosuresList calls useTranslation(), which now requires I18nProvider (and
// I18nProvider itself requires BrandingProvider).
function render(ui: ReactElement, options?: RenderOptions) {
  return rtlRender(ui, {
    wrapper: ({ children }: { children: ReactNode }) => (
      <BrandingProvider>
        <I18nProvider>{children}</I18nProvider>
      </BrandingProvider>
    ),
    ...options,
  })
}

const mockClosures = [
  {
    id: 1,
    branch_id: 1,
    start_date: new Date().toISOString().split('T')[0] ?? '',
    end_date: new Date().toISOString().split('T')[0] ?? '',
    reason: 'Emergency Closure',
    description: 'HVAC failure',
    patrons_with_holds_notified: true,
    staff_notified: true,
    partner_organizations_notified: false,
    website_updated: true,
    phone_message_updated: false,
    social_media_updated: true,
    google_maps_updated: false,
    apple_maps_updated: false,
    events_canceled: true,
    programs_rescheduled: false,
    closure_documentation: 'HVAC failure affecting all zones',
    created_at: new Date().toISOString(),
    created_by_id: 1,
  },
]

describe('ClosuresList', () => {
  it('renders no closures message when list is empty', () => {
    render(<ClosuresList closures={[]} />)

    expect(screen.getByText(/no active or upcoming closures/i)).toBeInTheDocument()
  })

  it('renders loading state', () => {
    render(<ClosuresList closures={[]} isLoading={true} />)

    expect(screen.getByText(/loading closures/i)).toBeInTheDocument()
  })

  it('displays active closure alert', () => {
    render(<ClosuresList closures={mockClosures} />)

    expect(screen.getByText(/active closure today/i)).toBeInTheDocument()
    expect(screen.getByText('Emergency Closure')).toBeInTheDocument()
  })

  it('displays closure completion percentage', () => {
    render(<ClosuresList closures={mockClosures} />)

    // Should show completion percentage (4/4 = 100%)
    expect(screen.getByText(/100%/)).toBeInTheDocument()
  })

  it('displays closure status indicators', () => {
    const { container } = render(<ClosuresList closures={mockClosures} />)

    // Completed-item checkmarks are decorative lucide CheckCircle icons with
    // no aria-label, so they correctly have no accessible "img" role (bare
    // <svg> with no role/aria-label is exposed to AT as nothing, which is the
    // right call here — the adjacent text already carries the meaning).
    // Assert on the rendered icon markup instead of a role that doesn't exist.
    const checkCircles = container.querySelectorAll('.lucide-circle-check-big')
    expect(checkCircles.length).toBeGreaterThan(0)
  })

  it('has manage button for active closures', () => {
    render(<ClosuresList closures={mockClosures} />)

    const manageButton = screen.getByRole('button', { name: /manage/i })
    expect(manageButton).toBeInTheDocument()
  })
})
