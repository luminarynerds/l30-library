/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { act } from 'react'
import { render, screen, waitFor } from '../../__tests__/utils/test-utils'
import { TurnstileWidget } from '../TurnstileWidget'

function makeTurnstileMock() {
  return {
    render: vi.fn().mockReturnValue('w1'),
    remove: vi.fn(),
    reset: vi.fn(),
  } as unknown as Window['turnstile']
}

interface RenderOpts {
  callback: (token: string) => void
  'error-callback': () => void
  'expired-callback': () => void
}

// The opts object (callback / error-callback / expired-callback) that the
// component handed to window.turnstile.render, so tests can drive the widget.
function lastRenderOpts(): RenderOpts {
  const mock = window.turnstile!.render as unknown as { mock: { calls: unknown[][] } }
  const calls = mock.mock.calls
  const call = calls[calls.length - 1]
  if (!call) throw new Error('window.turnstile.render was not called')
  return call[1] as RenderOpts
}

describe('TurnstileWidget', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_TURNSTILE_SITE_KEY', 'test-key')
    window.turnstile = makeTurnstileMock()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    delete (window as Window & { turnstile?: Window['turnstile'] }).turnstile
    vi.clearAllMocks()
  })

  it('regression/default: calls ts.render with appearance "interaction-only" when no appearance prop given', async () => {
    const onVerify = vi.fn()
    render(<TurnstileWidget onVerify={onVerify} />)

    await waitFor(() => {
      expect(window.turnstile!.render).toHaveBeenCalled()
    })

    expect(window.turnstile!.render).toHaveBeenCalledWith(
      expect.any(HTMLElement),
      expect.objectContaining({ appearance: 'interaction-only' }),
    )
  })

  it('interaction-only forwarded: calls ts.render with appearance "interaction-only" when prop given', async () => {
    const onVerify = vi.fn()
    render(<TurnstileWidget onVerify={onVerify} appearance="interaction-only" />)

    await waitFor(() => {
      expect(window.turnstile!.render).toHaveBeenCalled()
    })

    expect(window.turnstile!.render).toHaveBeenCalledWith(
      expect.any(HTMLElement),
      expect.objectContaining({ appearance: 'interaction-only' }),
    )
  })

  it('self-host bypass: site key "disabled" short-circuits to onVerify("dev-bypass") and never renders the widget', async () => {
    vi.stubEnv('VITE_TURNSTILE_SITE_KEY', 'disabled')
    const onVerify = vi.fn()
    render(<TurnstileWidget onVerify={onVerify} />)

    await waitFor(() => {
      expect(onVerify).toHaveBeenCalledWith('dev-bypass')
    })

    expect(window.turnstile!.render).not.toHaveBeenCalled()
  })

  it('self-host bypass: "disabled" is matched case-insensitively', async () => {
    vi.stubEnv('VITE_TURNSTILE_SITE_KEY', 'DISABLED')
    const onVerify = vi.fn()
    render(<TurnstileWidget onVerify={onVerify} />)

    await waitFor(() => {
      expect(onVerify).toHaveBeenCalledWith('dev-bypass')
    })

    expect(window.turnstile!.render).not.toHaveBeenCalled()
  })

  it('self-host bypass: verified immediately, so no status hint is shown', async () => {
    vi.stubEnv('VITE_TURNSTILE_SITE_KEY', 'disabled')
    const onVerify = vi.fn()
    render(<TurnstileWidget onVerify={onVerify} />)

    await waitFor(() => {
      expect(onVerify).toHaveBeenCalledWith('dev-bypass')
    })
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('accessibility: surfaces a recoverable error in a live region when Turnstile errors out', async () => {
    const onVerify = vi.fn()
    render(<TurnstileWidget onVerify={onVerify} />)

    await waitFor(() => {
      expect(window.turnstile!.render).toHaveBeenCalled()
    })

    act(() => {
      lastRenderOpts()['error-callback']()
    })

    const region = await screen.findByRole('status')
    expect(region.getAttribute('aria-live')).toBe('polite')
    expect(region.textContent).toMatch(/verify your browser/i)
    // Token cleared so the consuming submit button stays disabled.
    expect(onVerify).toHaveBeenLastCalledWith('')
  })

  it('reports the token and hides the status hint once verified', async () => {
    const onVerify = vi.fn()
    render(<TurnstileWidget onVerify={onVerify} />)

    await waitFor(() => {
      expect(window.turnstile!.render).toHaveBeenCalled()
    })

    act(() => {
      lastRenderOpts().callback('tok-123')
    })

    await waitFor(() => {
      expect(onVerify).toHaveBeenLastCalledWith('tok-123')
    })
    // Verified => no leftover status/error text.
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('resets to recover a fresh token when the current one expires', async () => {
    const onVerify = vi.fn()
    render(<TurnstileWidget onVerify={onVerify} />)

    await waitFor(() => {
      expect(window.turnstile!.render).toHaveBeenCalled()
    })

    act(() => {
      lastRenderOpts()['expired-callback']()
    })

    expect(onVerify).toHaveBeenLastCalledWith('')
    expect(window.turnstile!.reset).toHaveBeenCalledWith('w1')
  })
})
