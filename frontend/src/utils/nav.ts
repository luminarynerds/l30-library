/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

export interface IsActiveOptions {
  exact?: boolean
  /** Other paths in the same nav surface — used for longest-prefix tie-breaking. */
  knownPaths?: readonly string[]
}

export function isActive(
  currentPath: string,
  linkPath: string,
  options: IsActiveOptions = {},
): boolean {
  const { exact = false, knownPaths } = options

  if (exact) return currentPath === linkPath

  // Exact match always wins.
  if (currentPath === linkPath) return true

  // Must be a path-segment prefix, not a substring prefix
  // (so `/staff` does not match `/staff-only-page`).
  if (!currentPath.startsWith(linkPath + '/')) return false

  // If a more-specific known path also matches, defer to it.
  if (knownPaths) {
    const moreSpecific = knownPaths.some(
      (p) =>
        p !== linkPath &&
        p.length > linkPath.length &&
        (currentPath === p || currentPath.startsWith(p + '/')),
    )
    if (moreSpecific) return false
  }

  return true
}
