/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useEffect } from 'react'
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom'
import RouteAnnouncer from '../RouteAnnouncer'

vi.mock('@/contexts/BrandingContext', () => ({
  useBranding: () => ({ library_name: 'Little Schitt Creek Library' }),
}))

function Nav() {
  const navigate = useNavigate()
  return (
    <>
      <button type="button" onClick={() => navigate('/second')}>
        go
      </button>
      <button type="button" onClick={() => navigate('/owns-title')}>
        go-owned
      </button>
    </>
  )
}

function OwnsTitlePage() {
  useEffect(() => {
    document.title = 'Discover Indie Books | Local Authors'
  }, [])
  return <div>Indie</div>
}

function Harness() {
  return (
    <>
      <main id="main-content" tabIndex={-1}>
        <Routes>
          <Route path="/" element={<Nav />} />
          <Route path="/second" element={<div>Second page</div>} />
          <Route path="/owns-title" element={<OwnsTitlePage />} />
        </Routes>
      </main>
      <RouteAnnouncer />
    </>
  )
}

describe('RouteAnnouncer main-content focus', () => {
  beforeEach(() => {
    document.title = ''
  })

  it('does not steal focus on initial mount', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Harness />
      </MemoryRouter>,
    )
    const main = document.getElementById('main-content')
    expect(document.activeElement).not.toBe(main)
  })

  it('focuses #main-content on SPA route change', async () => {
    const { getByText } = render(
      <MemoryRouter initialEntries={['/']}>
        <Harness />
      </MemoryRouter>,
    )
    const user = userEvent.setup()
    await user.click(getByText('go'))
    const main = document.getElementById('main-content')
    await waitFor(() => expect(document.activeElement).toBe(main))
  })
})

// WCAG 2.4.2: document.title was stuck on the index.html default
// ("Library") for every route because nothing route-level ever set it.
describe('RouteAnnouncer document.title', () => {
  beforeEach(() => {
    document.title = 'Library'
  })

  it('sets a descriptive title on the initial route without announcing', async () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/']}>
        <Harness />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(document.title).toBe('Little Schitt Creek Library'),
    )
    expect(container.querySelector('[role="status"]')?.textContent).toBe('')
  })

  it('titles a navigated route from its path when it has no h1 or own title', async () => {
    const { getByText } = render(
      <MemoryRouter initialEntries={['/']}>
        <Harness />
      </MemoryRouter>,
    )
    const user = userEvent.setup()
    await user.click(getByText('go'))
    await waitFor(() =>
      expect(document.title).toBe('Second - Little Schitt Creek Library'),
    )
  })

  it('leaves a page-owned title alone', async () => {
    const { getByText } = render(
      <MemoryRouter initialEntries={['/']}>
        <Harness />
      </MemoryRouter>,
    )
    const user = userEvent.setup()
    await user.click(getByText('go-owned'))
    await waitFor(() =>
      expect(document.title).toBe('Discover Indie Books | Local Authors'),
    )
    // and it stays owned (announcer must not rewrite it on its 100ms tick)
    await new Promise((r) => setTimeout(r, 250))
    expect(document.title).toBe('Discover Indie Books | Local Authors')
  })

  it('does not mistake its own previous auto-title for a page-owned one', async () => {
    const { getByText } = render(
      <MemoryRouter initialEntries={['/second']}>
        <MemoryHarnessBack />
      </MemoryRouter>,
    )
    await waitFor(() =>
      expect(document.title).toBe('Second - Little Schitt Creek Library'),
    )
    const user = userEvent.setup()
    await user.click(getByText('back-home'))
    await waitFor(() =>
      expect(document.title).toBe('Little Schitt Creek Library'),
    )
  })
})

function BackNav() {
  const navigate = useNavigate()
  return (
    <button type="button" onClick={() => navigate('/')}>
      back-home
    </button>
  )
}

function MemoryHarnessBack() {
  return (
    <>
      <main id="main-content" tabIndex={-1}>
        <Routes>
          <Route path="/" element={<div>Home</div>} />
          <Route path="/second" element={<BackNav />} />
        </Routes>
      </main>
      <RouteAnnouncer />
    </>
  )
}
