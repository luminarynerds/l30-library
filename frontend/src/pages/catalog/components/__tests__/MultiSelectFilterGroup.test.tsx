// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MultiSelectFilterGroup } from '../MultiSelectFilterGroup'

const FACETS = [
  { value: 'Fiction', count: 12 },
  { value: 'History', count: 7 },
  { value: 'Science', count: 4 },
]

describe('MultiSelectFilterGroup', () => {
  it('renders nothing when facets is empty', () => {
    const { container } = render(
      <MultiSelectFilterGroup
        label="Subjects"
        facets={[]}
        selectedValues={[]}
        onChange={() => {}}
      />,
    )
    expect(container.firstChild).toBeNull()
    expect(screen.queryByRole('group')).not.toBeInTheDocument()
  })

  it('renders a role=group with aria-labelledby resolving to the visible heading', () => {
    render(
      <MultiSelectFilterGroup
        label="Subjects"
        facets={FACETS}
        selectedValues={[]}
        onChange={() => {}}
      />,
    )
    const group = screen.getByRole('group', { name: 'Subjects' })
    expect(group).toBeInTheDocument()
  })

  it('reflects selected values as checked checkboxes', () => {
    render(
      <MultiSelectFilterGroup
        label="Subjects"
        facets={FACETS}
        selectedValues={['Fiction']}
        onChange={() => {}}
      />,
    )
    expect(screen.getByRole('checkbox', { name: /Fiction/ })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: /History/ })).not.toBeChecked()
  })

  it('calls onChange with next array when toggling on', () => {
    const onChange = vi.fn()
    render(
      <MultiSelectFilterGroup
        label="Subjects"
        facets={FACETS}
        selectedValues={['Fiction']}
        onChange={onChange}
      />,
    )
    fireEvent.click(screen.getByRole('checkbox', { name: /History/ }))
    expect(onChange).toHaveBeenCalledWith(['Fiction', 'History'])
  })

  it('calls onChange with removed value when toggling off', () => {
    const onChange = vi.fn()
    render(
      <MultiSelectFilterGroup
        label="Subjects"
        facets={FACETS}
        selectedValues={['Fiction', 'History']}
        onChange={onChange}
      />,
    )
    fireEvent.click(screen.getByRole('checkbox', { name: /Fiction/ }))
    expect(onChange).toHaveBeenCalledWith(['History'])
  })

  it('renders count adjacent to each facet label', () => {
    render(
      <MultiSelectFilterGroup
        label="Subjects"
        facets={FACETS}
        selectedValues={[]}
        onChange={() => {}}
      />,
    )
    expect(screen.getByText('(12)')).toBeInTheDocument()
    expect(screen.getByText('(7)')).toBeInTheDocument()
  })

  it('hides facets beyond showMoreThreshold until "Show more" pressed', () => {
    const many = Array.from({ length: 30 }, (_, i) => ({
      value: `S${i}`,
      count: 30 - i,
    }))
    render(
      <MultiSelectFilterGroup
        label="Subjects"
        facets={many}
        selectedValues={[]}
        onChange={() => {}}
        showMoreThreshold={10}
      />,
    )
    expect(screen.queryByRole('checkbox', { name: /S20/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Show .* more/i }))
    expect(screen.getByRole('checkbox', { name: /S20/ })).toBeInTheDocument()
  })

  it('announces selection changes via the injected announcer', () => {
    const announce = vi.fn()
    const onChange = vi.fn()
    render(
      <MultiSelectFilterGroup
        label="Subjects"
        facets={FACETS}
        selectedValues={[]}
        onChange={onChange}
        announceToScreenReader={announce}
      />,
    )
    fireEvent.click(screen.getByRole('checkbox', { name: /Fiction/ }))
    expect(announce).toHaveBeenCalledWith(
      expect.stringContaining('Subjects'),
    )
    expect(announce).toHaveBeenCalledWith(
      expect.stringContaining('Fiction'),
    )
  })
  it('does not violate rules of hooks when facets transitions from empty to populated', () => {
    const { rerender, container } = render(
      <MultiSelectFilterGroup
        label="Subjects"
        facets={[]}
        selectedValues={[]}
        onChange={() => {}}
      />,
    )
    expect(container.firstChild).toBeNull()
    // This rerender would throw "Rendered more hooks than during the previous render"
    // if the early null-return came BEFORE the hooks.
    expect(() =>
      rerender(
        <MultiSelectFilterGroup
          label="Subjects"
          facets={FACETS}
          selectedValues={[]}
          onChange={() => {}}
        />,
      ),
    ).not.toThrow()
    // After populated, the group renders
    expect(screen.getByRole('group', { name: 'Subjects' })).toBeInTheDocument()
  })

  it('shows "Show more" button when facets transitions empty -> long list', () => {
    const long = Array.from({ length: 30 }, (_, i) => ({ value: `S${i}`, count: 30 - i }))
    const { rerender } = render(
      <MultiSelectFilterGroup
        label="Subjects"
        facets={[]}
        selectedValues={[]}
        onChange={() => {}}
        showMoreThreshold={10}
      />,
    )
    // initial: nothing renders
    expect(screen.queryByRole('group')).not.toBeInTheDocument()
    // rerender with 30 facets, threshold 10 -> "Show more" appears
    rerender(
      <MultiSelectFilterGroup
        label="Subjects"
        facets={long}
        selectedValues={[]}
        onChange={() => {}}
        showMoreThreshold={10}
      />,
    )
    expect(screen.getByRole('button', { name: /Show .* more/i })).toBeInTheDocument()
    // S20 still hidden until clicked
    expect(screen.queryByRole('checkbox', { name: /S20/ })).not.toBeInTheDocument()
  })
})
