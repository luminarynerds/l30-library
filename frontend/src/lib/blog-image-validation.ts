/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

export interface BlogBodyImageValidation {
  valid: boolean
  totalImages: number
  failingImages: number
}

export function validateBlogBodyImages(html: string): BlogBodyImageValidation {
  if (!html || typeof html !== "string" || !html.includes("<img")) {
    return { valid: true, totalImages: 0, failingImages: 0 }
  }

  // happy-dom, jsdom, and real browsers all expose DOMParser.
  const parser = new DOMParser()
  const doc = parser.parseFromString(`<!doctype html><body>${html}</body>`, "text/html")
  const imgs = Array.from(doc.querySelectorAll("img"))

  let failing = 0
  for (const img of imgs) {
    const hasAltAttr = img.hasAttribute("alt")
    const altVal = (img.getAttribute("alt") ?? "").trim()
    const role = (img.getAttribute("role") ?? "").trim().toLowerCase()
    const isDecorative = role === "presentation" || role === "none"

    if (!hasAltAttr) {
      failing += 1
      continue
    }
    if (altVal.length > 0) {
      // Non-empty alt -- accessible.
      continue
    }
    // Empty alt
    if (isDecorative) {
      continue
    }
    failing += 1
  }

  return {
    valid: failing === 0,
    totalImages: imgs.length,
    failingImages: failing,
  }
}
