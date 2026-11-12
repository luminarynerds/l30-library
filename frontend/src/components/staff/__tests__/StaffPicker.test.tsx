/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

const getMock = vi.fn()
vi.mock('@/lib/api-client', () => ({
  api: {
    get: (url: string) => getMock(url),
  },
}))

import { StaffPicker } from '../StaffPicker'

beforeEach(() => {
  getMock.mockReset()
})

function setup(initialValue: number | null = null) {
  const onChange = vi.fn()
  let currentValue = initialValue
  const utils = render(
    <StaffPicker
      id='manager_id'
      label='Manager'
      value={currentValue}
      onChange={(v) => {
        currentValue = v
        onChange(v)
      }}
    />,
  )
  return { onChange, ...utils }
}

describe('StaffPicker', () => {
  it('does not query until the user types 2+ characters', async () => {
    const user = userEvent.setup()
    setup()
    const input = screen.getByLabelText(/Manager/i)
    await user.type(input, 'a')
    // 250ms debounce -> give it some time then assert no call
    await new Promise((r) => setTimeout(r, 350))
    expect(getMock).not.toHaveBeenCalled()
  })

  it('queries the users endpoint with the debounced search term and a role filter', async () => {
    const user = userEvent.setup()
    // api.get<T> resolves to the unwrapped body (dcbc1ae6f), not an axios-style
    // { data } envelope.
    getMock.mockResolvedValue({ users: [], total: 0, page: 1, limit: 10 })
    setup()
    const input = screen.getByLabelText(/Manager/i)
    await user.type(input, 'jo')
    await waitFor(
      () => {
        expect(getMock).toHaveBeenCalled()
      },
      { timeout: 2000 },
    )
    const urls = getMock.mock.calls.map((c) => c[0] as string)
    // Search term forwarded as the `search=` param.
    expect(urls.every((u) => u.includes('search=jo'))).toBe(true)
    // At least one request per allowed staff role; defaults to four.
    expect(urls.some((u) => u.includes('role=staff'))).toBe(true)
    expect(urls.some((u) => u.includes('role=admin'))).toBe(true)
  })

  it('stamps the selected user id (not free-typed text) when a result is clicked', async () => {
    const user = userEvent.setup()
    // api.get<T> resolves to the unwrapped body (dcbc1ae6f), not an axios-style
    // { data } envelope.
    getMock.mockResolvedValue({
      users: [
        {
          id: 42,
          email: 'jo@library.org',
          first_name: 'Jo',
          last_name: 'Lin',
          role: 'staff',
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
    })
    const onChange = vi.fn()
    render(
      <StaffPicker id='manager_id' label='Manager' value={null} onChange={onChange} />,
    )
    const input = screen.getByLabelText(/Manager/i)
    await user.type(input, 'jo')
    const option = await screen.findByRole('option', { name: /Jo Lin/i })
    await user.click(option)
    expect(onChange).toHaveBeenCalledWith(42)
    // onChange receives the id, not a parsed integer of free-typed text.
    const calls = onChange.mock.calls
    const arg = calls[calls.length - 1]?.[0]
    expect(typeof arg).toBe('number')
    expect(arg).toBe(42)
  })

  it('selects the active option via ArrowDown + Enter (keyboard-only)', async () => {
    const user = userEvent.setup()
    getMock.mockResolvedValue({
      users: [
        {
          id: 42,
          email: 'jo@library.org',
          first_name: 'Jo',
          last_name: 'Lin',
          role: 'staff',
        },
        {
          id: 43,
          email: 'sam@library.org',
          first_name: 'Sam',
          last_name: 'Reyes',
          role: 'staff',
        },
      ],
      total: 2,
      page: 1,
      limit: 10,
    })
    const onChange = vi.fn()
    render(
      <StaffPicker id='manager_id' label='Manager' value={null} onChange={onChange} />,
    )
    const input = screen.getByLabelText(/Manager/i)
    await user.type(input, 'jo')
    await screen.findByRole('option', { name: /Jo Lin/i })

    await user.keyboard('{ArrowDown}')
    await user.keyboard('{Enter}')

    expect(onChange).toHaveBeenCalledWith(42)
  })

  it('Escape closes the listbox without selecting', async () => {
    const user = userEvent.setup()
    getMock.mockResolvedValue({
      users: [
        {
          id: 42,
          email: 'jo@library.org',
          first_name: 'Jo',
          last_name: 'Lin',
          role: 'staff',
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
    })
    const onChange = vi.fn()
    render(
      <StaffPicker id='manager_id' label='Manager' value={null} onChange={onChange} />,
    )
    const input = screen.getByLabelText(/Manager/i)
    await user.type(input, 'jo')
    await screen.findByRole('option', { name: /Jo Lin/i })

    await user.keyboard('{Escape}')

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    expect(onChange).not.toHaveBeenCalled()
  })

  it('clears aria-activedescendant once the listbox unmounts after the query shrinks below 2 chars', async () => {
    const user = userEvent.setup()
    getMock.mockResolvedValue({
      users: [
        {
          id: 42,
          email: 'jo@library.org',
          first_name: 'Jo',
          last_name: 'Lin',
          role: 'staff',
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
    })
    render(
      <StaffPicker id='manager_id' label='Manager' value={null} onChange={vi.fn()} />,
    )
    const input = screen.getByLabelText(/Manager/i)
    await user.type(input, 'jo')
    await screen.findByRole('option', { name: /Jo Lin/i })

    await user.keyboard('{ArrowDown}')
    expect(input).toHaveAttribute('aria-activedescendant', 'manager_id-opt-0')

    // Shrinking below the 2-char query threshold unmounts the listbox but
    // (pre-fix) left activeIndex/results stale, so aria-activedescendant
    // kept pointing at an id no longer in the DOM.
    await user.keyboard('{Backspace}')
    await waitFor(() => {
      expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    })
    expect(input).not.toHaveAttribute('aria-activedescendant')
  })

  it('namespaces option ids per instance so multiple pickers on one page never collide', async () => {
    const user = userEvent.setup()
    getMock.mockResolvedValue({
      users: [
        {
          id: 42,
          email: 'jo@library.org',
          first_name: 'Jo',
          last_name: 'Lin',
          role: 'staff',
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
    })
    render(
      <>
        <StaffPicker id='manager_id' label='Manager' value={null} onChange={vi.fn()} />
        <StaffPicker id='director_id' label='Director' value={null} onChange={vi.fn()} />
      </>,
    )

    const managerInput = screen.getByLabelText(/Manager/i)
    const directorInput = screen.getByLabelText(/Director/i)
    await user.type(managerInput, 'jo')
    await user.type(directorInput, 'jo')

    await waitFor(() => {
      expect(screen.getAllByRole('option', { name: /Jo Lin/i })).toHaveLength(2)
    })

    const idElements = document.querySelectorAll('[id]')
    const ids = Array.from(idElements).map((el) => el.id)
    expect(new Set(ids).size).toBe(ids.length)
  })
})
