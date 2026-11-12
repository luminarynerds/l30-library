/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { render, screen, within } from '../../utils/test-utils'
import ExternalResourcesSection from '@/components/tech-support/ExternalResourcesSection'
import type { QuickAccessSection } from '@/api/tech-support-api'

describe('ExternalResourcesSection', () => {
  it('renders nothing when sections list is empty', () => {
    const { container } = render(<ExternalResourcesSection sections={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders each section heading and its links', () => {
    // section.icon stored kebab-case in tech_quick_links.section_icon.
    const sections: QuickAccessSection[] = [
      {
        title: 'Internet & WiFi',
        icon: 'wifi',
        links: [{ name: 'Example ISP', url: 'https://example.com' }],
      },
    ]
    render(<ExternalResourcesSection sections={sections} />)
    expect(screen.getByText('Internet & WiFi')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /Example ISP \(opens in a new tab\)/i }),
    ).toHaveAttribute('href', 'https://example.com')
  })

  // I4 — external links carry a clear "opens in a new tab" accessible
  // name so SR users aren't ambushed by a target=_blank.
  it('exposes "(opens in a new tab)" in each link\'s accessible name', () => {
    const sections: QuickAccessSection[] = [
      {
        title: 'Devices',
        icon: 'laptop',
        links: [
          { name: 'Vendor A', url: 'https://a.example' },
          { name: 'Vendor B', url: 'https://b.example' },
        ],
      },
    ]
    render(<ExternalResourcesSection sections={sections} />)
    const linkA = screen.getByRole('link', { name: /Vendor A \(opens in a new tab\)/i })
    const linkB = screen.getByRole('link', { name: /Vendor B \(opens in a new tab\)/i })
    expect(linkA).toHaveAttribute('target', '_blank')
    expect(linkB).toHaveAttribute('target', '_blank')
  })

  // I7 — section icon glyph is selected by `section.icon` (stable
  // lucide name, kebab-case) NOT `section.title`. A renamed section
  // whose icon is still 'wifi' must keep the wifi glyph; this matters
  // because section titles are i18n-volatile while icon strings are not.
  it('selects the section icon by `section.icon` field, not title', () => {
    const sections: QuickAccessSection[] = [
      {
        title: 'Renamed Connectivity',
        icon: 'wifi',
        links: [{ name: 'Speed Test', url: 'https://speedtest.example' }],
      },
    ]
    const { container } = render(<ExternalResourcesSection sections={sections} />)
    // The wifi lucide icon renders with class `lucide-wifi` — verify
    // an svg with that class is inside the section's heading row, not
    // the default ExternalLink fallback.
    const section = container.querySelector('section')!
    const headingRow = within(section).getByText('Renamed Connectivity').parentElement!
    const svg = headingRow.querySelector('svg')
    expect(svg).not.toBeNull()
    // lucide-react sets a class like "lucide lucide-wifi"
    expect(svg!.getAttribute('class') || '').toMatch(/lucide-wifi/i)
  })

  it('falls back to a default icon when section.icon is missing or unknown', () => {
    const sections: QuickAccessSection[] = [
      {
        title: 'Misc',
        links: [{ name: 'Misc link', url: 'https://misc.example' }],
      },
    ]
    const { container } = render(<ExternalResourcesSection sections={sections} />)
    const section = container.querySelector('section')!
    const headingRow = within(section).getByText('Misc').parentElement!
    const svg = headingRow.querySelector('svg')
    expect(svg).not.toBeNull()
    // Default fallback is the ExternalLink icon — lucide class hint.
    expect(svg!.getAttribute('class') || '').toMatch(/lucide-external-link/i)
  })
})
