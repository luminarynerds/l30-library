/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { buildQrSlug, buildQrTargetUrl } from '@/pages/_qrSlug'

describe('buildQrSlug', () => {
  it('returns tech-launchpad for the launchpad', () => {
    expect(buildQrSlug({ kind: 'launchpad', path: '/tech' })).toBe('tech-launchpad')
  })

  it.each([
    ['password', '/tech?p=password', 'tech-p-password'],
    ['login', '/tech?p=login', 'tech-p-login'],
    ['printer', '/tech?p=printer', 'tech-p-printer'],
    ['wifi', '/tech?p=wifi', 'tech-p-wifi'],
  ])('returns tech-p-%s for triage %s', (_p, path, expected) => {
    expect(buildQrSlug({ kind: 'triage', path })).toBe(expected)
  })

  it('does not collide between launchpad and triage on the same base path', () => {
    const lp = buildQrSlug({ kind: 'launchpad', path: '/tech' })
    const tr = buildQrSlug({ kind: 'triage', path: '/tech?p=printer' })
    expect(lp).not.toBe(tr)
  })

  it.each([
    ['/guides/password-reset', 'guide-password-reset'],
    ['/guides/wireless-printing', 'guide-wireless-printing'],
    ['/guides/library-card', 'guide-library-card'],
  ])('returns guide-<id> for %s', (path, expected) => {
    expect(buildQrSlug({ kind: 'guide', path })).toBe(expected)
  })

  it('returns legal-main for /legal', () => {
    expect(buildQrSlug({ kind: 'legal', path: '/legal' })).toBe('legal-main')
  })

  it('returns legal-calculators for /legal/calculators', () => {
    expect(buildQrSlug({ kind: 'legal', path: '/legal/calculators' })).toBe('legal-calculators')
  })

  it('throws on a triage destination missing ?p=', () => {
    expect(() => buildQrSlug({ kind: 'triage', path: '/tech' })).toThrow()
  })

  it('throws on a guide destination not under /guides/', () => {
    expect(() => buildQrSlug({ kind: 'guide', path: '/elsewhere/foo' })).toThrow()
  })
})

describe('buildQrTargetUrl', () => {
  it('appends ?qr=<slug> to a path with no existing query', () => {
    const url = buildQrTargetUrl('https://l30.org', { kind: 'launchpad', path: '/tech' })
    expect(url).toBe('https://l30.org/tech?qr=tech-launchpad')
  })

  it('merges qr= as &qr= when the path already has a query', () => {
    const url = buildQrTargetUrl('https://l30.org', { kind: 'triage', path: '/tech?p=printer' })
    expect(url).toBe('https://l30.org/tech?p=printer&qr=tech-p-printer')
  })

  it('handles guide paths', () => {
    const url = buildQrTargetUrl('https://l30.org', {
      kind: 'guide',
      path: '/guides/wireless-printing',
    })
    expect(url).toBe('https://l30.org/guides/wireless-printing?qr=guide-wireless-printing')
  })

  it('handles legal paths', () => {
    const url = buildQrTargetUrl('https://l30.org', { kind: 'legal', path: '/legal/calculators' })
    expect(url).toBe('https://l30.org/legal/calculators?qr=legal-calculators')
  })

  it('does not leak a placeholder host when origin is empty', () => {
    const url = buildQrTargetUrl('', { kind: 'launchpad', path: '/tech' })
    expect(url).toBe('/tech?qr=tech-launchpad')
    expect(url).not.toContain('placeholder')
    expect(url).not.toContain('invalid')
  })
})
