// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later
/** Trigger a browser download for a fetched Blob, honoring a server filename. */
export function triggerBlobDownload(blob: Blob, fallbackName: string, contentDisposition?: string | null): void {
  let name = fallbackName
  if (contentDisposition) {
    const m = /filename\*?=(?:UTF-8'')"?([^";]+)"?/i.exec(contentDisposition)
    if (m?.[1]) name = decodeURIComponent(m[1])
  }
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
