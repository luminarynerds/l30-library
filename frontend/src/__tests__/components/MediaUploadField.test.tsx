/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="@testing-library/jest-dom/vitest" />
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import MediaUploadField from '@/components/training/MediaUploadField'

// MediaUploadField calls getAccessToken; stub it out
vi.mock('../../utils/tokenStore', () => ({
  getAccessToken: vi.fn(() => 'test-token'),
}))

describe('MediaUploadField', () => {
  it('disables upload and shows the hint when getUploadUrl returns null', () => {
    render(
      <MediaUploadField
        label="Thumbnail"
        value=""
        onChange={vi.fn()}
        getUploadUrl={() => null}
        accept="image/*"
        disabledHint="Save the course first"
      />
    )
    expect(screen.getByText('Save the course first')).toBeInTheDocument()
  })

  it('enables upload when getUploadUrl returns a URL', () => {
    render(
      <MediaUploadField
        label="Thumbnail"
        value=""
        onChange={vi.fn()}
        getUploadUrl={() => '/api/v1/learning/courses/1/media?media_type=thumbnail'}
        accept="image/*"
      />
    )
    expect(screen.queryByText(/save the course first/i)).not.toBeInTheDocument()
  })
})
