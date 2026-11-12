/**
 * Opens a downloadable resource in a separate browsing context while
 * preventing the opened page from gaining access to the opener.
 */
const SAFE_PROTOCOLS = new Set(['http:', 'https:', 'blob:', 'data:'])

export function openDownloadInNewTab(href: string, filename?: string): void {
  // Board document paths are staff-entered free text; never click a script URL.
  const { protocol } = new URL(href.trim(), window.location.href)
  if (!SAFE_PROTOCOLS.has(protocol)) {
    throw new Error(`Refusing to open download with unsafe URL scheme: ${protocol}`)
  }

  const link = document.createElement('a')
  link.href = href
  link.target = '_blank'
  link.rel = 'noopener noreferrer'

  if (filename) link.download = filename

  document.body.appendChild(link)
  link.click()
  link.remove()
}
