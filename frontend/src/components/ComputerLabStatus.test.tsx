/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import ComputerLabStatus from './ComputerLabStatus'
import { getLabMap } from '@/api/computer-lab-map-api'

vi.mock('@/api/computer-lab-map-api', () => ({
  getLabMap: vi.fn(),
}))

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (k: string, p?: Record<string, string>) =>
      p ? `${k}::${JSON.stringify(p)}` : k,
  }),
}))

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>
  )
}

function station(overrides: Partial<{
  status: string; available_at: string | null; computer_number: string
}>) {
  return {
    id: Math.floor(Math.random() * 1e6),
    name: overrides.computer_number ?? 'PC',
    computer_number: overrides.computer_number ?? 'PC',
    location: null, computer_type: 'adult',
    status: overrides.status ?? 'available',
    map_x: null, map_y: null, map_floor: null,
    available_at: overrides.available_at ?? null,
  }
}

describe('ComputerLabStatus', () => {
  it('renders mixed (some free, some busy) with next-free time', async () => {
    ;(getLabMap as ReturnType<typeof vi.fn>).mockResolvedValue({
      stations: [
        station({ status: 'available', computer_number: 'PC-1' }),
        station({ status: 'available', computer_number: 'PC-2' }),
        station({
          status: 'in_use',
          computer_number: 'PC-3',
          available_at: new Date(Date.now() + 12 * 60_000).toISOString(),
        }),
      ],
      generated_at: new Date().toISOString(),
    })
    render(wrap(<ComputerLabStatus />))
    expect(await screen.findByText(/computerLab\.available/)).toBeInTheDocument()
    expect(await screen.findByText(/computerLab\.wait/)).toBeInTheDocument()
  })

  it('renders all-free state without subtitle', async () => {
    ;(getLabMap as ReturnType<typeof vi.fn>).mockResolvedValue({
      stations: [
        station({ status: 'available', computer_number: 'PC-1' }),
        station({ status: 'available', computer_number: 'PC-2' }),
      ],
      generated_at: new Date().toISOString(),
    })
    render(wrap(<ComputerLabStatus />))
    expect(await screen.findByText(/computerLab\.available/)).toBeInTheDocument()
    expect(screen.queryByText(/computerLab\.wait/)).not.toBeInTheDocument()
  })

  it('renders all-busy state with next-free time', async () => {
    ;(getLabMap as ReturnType<typeof vi.fn>).mockResolvedValue({
      stations: [
        station({
          status: 'in_use',
          computer_number: 'PC-1',
          available_at: new Date(Date.now() + 8 * 60_000).toISOString(),
        }),
      ],
      generated_at: new Date().toISOString(),
    })
    render(wrap(<ComputerLabStatus />))
    expect(await screen.findByText(/computerLab\.available/)).toBeInTheDocument()
    expect(await screen.findByText(/computerLab\.wait/)).toBeInTheDocument()
  })

  it('renders all-out-of-service state instead of null', async () => {
    ;(getLabMap as ReturnType<typeof vi.fn>).mockResolvedValue({
      stations: [
        station({ status: 'maintenance', computer_number: 'PC-M' }),
        station({ status: 'offline', computer_number: 'PC-O' }),
      ],
      generated_at: new Date().toISOString(),
    })
    render(wrap(<ComputerLabStatus />))
    expect(await screen.findByText(/computerLab\.allOutOfService/)).toBeInTheDocument()
    expect(await screen.findByText(/computerLab\.outOfService/)).toBeInTheDocument()
  })

  it('shows out-of-service line when any station is in maintenance', async () => {
    ;(getLabMap as ReturnType<typeof vi.fn>).mockResolvedValue({
      stations: [
        station({ status: 'available', computer_number: 'PC-1' }),
        station({ status: 'available', computer_number: 'PC-2' }),
        station({
          status: 'in_use',
          computer_number: 'PC-3',
          available_at: new Date(Date.now() + 12 * 60_000).toISOString(),
        }),
        station({ status: 'maintenance', computer_number: 'PC-M' }),
      ],
      generated_at: new Date().toISOString(),
    })
    render(wrap(<ComputerLabStatus />))
    expect(await screen.findByText(/computerLab\.available/)).toBeInTheDocument()
    expect(await screen.findByText(/computerLab\.wait/)).toBeInTheDocument()
    expect(await screen.findByText(/computerLab\.outOfService/)).toBeInTheDocument()
  })

  it('denominator is full fleet, not in-service count (so out-of-service is not hidden)', async () => {
    // 7 available + 1 maintenance => headline must read "7 of 8", not "7 of 7"
    ;(getLabMap as ReturnType<typeof vi.fn>).mockResolvedValue({
      stations: [
        station({ status: 'available', computer_number: 'PC-1' }),
        station({ status: 'available', computer_number: 'PC-2' }),
        station({ status: 'available', computer_number: 'PC-3' }),
        station({ status: 'available', computer_number: 'PC-4' }),
        station({ status: 'available', computer_number: 'KIDS-1' }),
        station({ status: 'available', computer_number: 'KIDS-2' }),
        station({ status: 'available', computer_number: 'TEEN-1' }),
        station({ status: 'maintenance', computer_number: 'ADA-1' }),
      ],
      generated_at: new Date().toISOString(),
    })
    render(wrap(<ComputerLabStatus />))
    const headline = await screen.findByText(/computerLab\.available/)
    expect(headline.textContent).toContain('"free":"7"')
    expect(headline.textContent).toContain('"total":"8"')
    expect(await screen.findByText(/computerLab\.outOfService/)).toBeInTheDocument()
  })
})
