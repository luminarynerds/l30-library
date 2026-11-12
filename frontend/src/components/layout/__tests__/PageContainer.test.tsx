/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import '@testing-library/jest-dom'
import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

import PageContainer from '../PageContainer'
import { PAGE_WIDTH } from '../page-width'

describe('PageContainer', () => {
  it('defaults to the content width tier', () => {
    const { container } = render(<PageContainer>hello</PageContainer>)
    const root = container.firstElementChild as HTMLElement
    expect(root).toHaveClass(PAGE_WIDTH.content)
    expect(root).toHaveClass('mx-auto')
    expect(root).toHaveClass('px-4')
  })

  it('applies the requested width tier', () => {
    const { container } = render(<PageContainer width="read">x</PageContainer>)
    expect(container.firstElementChild).toHaveClass(PAGE_WIDTH.read)
  })

  it('merges an extra className', () => {
    const { container } = render(<PageContainer className="custom-x">x</PageContainer>)
    expect(container.firstElementChild).toHaveClass('custom-x')
  })
})
