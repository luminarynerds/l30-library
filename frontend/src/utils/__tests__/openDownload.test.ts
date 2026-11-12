import { afterEach, describe, expect, it, vi } from 'vitest'
import { openDownloadInNewTab } from '../openDownload'

describe('openDownloadInNewTab', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    document.body.replaceChildren()
  })

  it('opens downloads in a safe new tab and removes the temporary link', () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    openDownloadInNewTab('/files/board-packet.pdf', 'board-packet.pdf')

    expect(click).toHaveBeenCalledOnce()
    const link = click.mock.instances[0] as HTMLAnchorElement
    expect(link).toHaveAttribute('href', '/files/board-packet.pdf')
    expect(link).toHaveAttribute('download', 'board-packet.pdf')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(document.body).not.toContainElement(link)
  })

  it('refuses script URLs instead of clicking them', () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    expect(() => openDownloadInNewTab('javascript:alert(1)', 'x.pdf')).toThrow(/unsafe/)
    expect(() => openDownloadInNewTab(' JavaScript:alert(1)')).toThrow(/unsafe/)

    expect(click).not.toHaveBeenCalled()
    expect(document.body.querySelector('a')).toBeNull()
  })

  it('still opens data: exports', () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    openDownloadInNewTab('data:text/plain;charset=utf-8,minutes', 'minutes.txt')

    expect(click).toHaveBeenCalledOnce()
  })
})
