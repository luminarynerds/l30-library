/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export type QrDestinationKind = 'launchpad' | 'triage' | 'guide' | 'legal'

export interface QrDestinationLike {
  kind: QrDestinationKind
  /** Path appended to the origin to form the target URL (may include a query). */
  path: string
}

export function buildQrSlug(dest: QrDestinationLike): string {
  switch (dest.kind) {
    case 'launchpad':
      return 'tech-launchpad'
    case 'triage': {
      // path is like `/tech?p=printer` -- pull the `p` param.
      const q = dest.path.includes('?') ? dest.path.slice(dest.path.indexOf('?') + 1) : ''
      const params = new URLSearchParams(q)
      const p = params.get('p')
      if (!p) {
        throw new Error(`triage destination missing ?p= param: ${dest.path}`)
      }
      return `tech-p-${p}`
    }
    case 'guide': {
      // path is `/guides/<id>` -- last segment is the id.
      const pathOnly = dest.path.split('?')[0] ?? ''
      const segments = pathOnly.split('/').filter(Boolean)
      const id = segments[segments.length - 1]
      if (!id || segments[0] !== 'guides') {
        throw new Error(`guide destination not under /guides/<id>: ${dest.path}`)
      }
      return `guide-${id}`
    }
    case 'legal': {
      const pathOnly = dest.path.split('?')[0] ?? ''
      if (pathOnly === '/legal') return 'legal-main'
      const segments = pathOnly.split('/').filter(Boolean)
      // /legal/calculators -> legal-calculators
      if (segments[0] === 'legal' && segments.length >= 2) {
        return `legal-${segments.slice(1).join('-')}`
      }
      throw new Error(`unsupported legal destination: ${dest.path}`)
    }
    default: {
      // Exhaustiveness check.
      const _exhaustive: never = dest.kind
      throw new Error(`unknown QR destination kind: ${String(_exhaustive)}`)
    }
  }
}

export function buildQrTargetUrl(origin: string, dest: QrDestinationLike): string {
  const slug = buildQrSlug(dest)
  // Use a placeholder base so `URL` accepts a path-only input; we will splice
  // origin back in below. This avoids depending on `window` in tests.
  const base = origin || 'http://_qr-placeholder.invalid'
  const u = new URL(dest.path, base)
  u.searchParams.set('qr', slug)
  // Re-serialize as origin + path + search + hash so we don't leak the
  // placeholder host when origin is empty (SSR / jsdom).
  const tail = `${u.pathname}${u.search}${u.hash}`
  return `${origin}${tail}`
}
