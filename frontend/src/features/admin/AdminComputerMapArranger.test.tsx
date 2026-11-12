/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { createEvent, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

import AdminComputerMapArranger from './AdminComputerMapArranger'

const { update } = vi.hoisted(() => ({ update: vi.fn().mockResolvedValue({}) }))
vi.mock('@/api/domains/admin/admin-computers-api', () => ({
  getAdminComputers: vi.fn().mockResolvedValue({
    total: 1, skip: 0, limit: 50,
    items: [
      { id: 7, name: 'PC-7', computer_number: 'PC-7', computer_type: 'adult',
        status: 'available', is_active: true,
        map_x: null, map_y: null, map_floor: null,
        description: null, branch_id: null, branch_name: null, location: null,
        os_type: null, has_internet: true, has_print_release: true,
        max_session_minutes: 60, installed_software: [],
        created_at: null, updated_at: null,
      },
    ],
  }),
  updateAdminComputer: update,
}))

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}))

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{node}</QueryClientProvider>
}

// jsdom's DragEvent ignores MouseEvent init (clientX/Y); attach them manually.
function fireDropAt(node: Element, clientX: number, clientY: number, getData: (k: string) => string) {
  const ev = createEvent.drop(node, { dataTransfer: { getData } } as unknown as Event)
  Object.defineProperty(ev, 'clientX', { value: clientX })
  Object.defineProperty(ev, 'clientY', { value: clientY })
  fireEvent(node, ev)
}

describe('AdminComputerMapArranger', () => {
  it('renders an unplaced station in the tray', async () => {
    render(wrap(<AdminComputerMapArranger />))
    expect(await screen.findByText('PC-7')).toBeInTheDocument()
    const tray = screen.getByTestId('tray')
    expect(tray).toContainElement(screen.getByText('PC-7'))
  })

  it('calls updateAdminComputer with normalized coords on drop into the canvas', async () => {
    update.mockClear()
    render(wrap(<AdminComputerMapArranger />))
    const card = await screen.findByText('PC-7')
    const canvas = screen.getByTestId('arranger-canvas')
    Object.defineProperty(canvas, 'getBoundingClientRect', {
      value: () => ({ left: 0, top: 0, width: 200, height: 100, right: 200, bottom: 100, x: 0, y: 0, toJSON: () => ({}) }),
    })
    fireEvent.dragStart(card, { dataTransfer: { setData: vi.fn(), effectAllowed: '' } })
    fireEvent.dragOver(canvas, { clientX: 100, clientY: 50, dataTransfer: { dropEffect: '' } })
    fireDropAt(canvas, 100, 50, () => '7')
    expect(update).toHaveBeenCalledWith(7, expect.objectContaining({ map_x: 0.5, map_y: 0.5 }))
  })
})
