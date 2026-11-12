/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SandboxPlayer } from './SandboxPlayer'
import type { SandboxContent } from './lesson-types'

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

describe('SandboxPlayer', () => {
  describe('article-shaped fallback', () => {
    // Mirrors the actual prod content stored for lesson 15 ("Reading & Editing
    // MARC Records"): no sandbox_type, no expected_output, no
    // discriminator -- just body + key_points + exercise_steps + sample_records.
    // Before the fix, "".includes("") was true and the lesson silently
    // auto-passed without any user input.
    const articleShaped: SandboxContent = {
      instructions: 'Practice reading MARC records.',
      body: 'In this hands-on exercise, you will work with **real** MARC records.',
      key_points: [
        'The 1XX fields contain the main entry',
        'The 245 field holds the title',
      ],
      exercise_steps: [
        'Open the MARC editor sandbox',
        'Identify fields 100, 245, 264, and 300',
      ],
      sample_records: ['978-0-06-112008-4', '978-0-13-468599-1'],
    }

    it('renders the read-only fallback notice', () => {
      render(<SandboxPlayer content={articleShaped} onComplete={() => {}} />)
      expect(
        screen.getByText(/Hands-on sandbox lesson .* interactive component coming soon/i)
      ).toBeTruthy()
    })

    it('renders body, key points, exercise steps, and sample records', () => {
      render(<SandboxPlayer content={articleShaped} onComplete={() => {}} />)
      expect(screen.getByText('Instructions')).toBeTruthy()
      expect(screen.getByText('Key points')).toBeTruthy()
      expect(screen.getByText('Exercise steps')).toBeTruthy()
      expect(screen.getByText('Sample records')).toBeTruthy()
      expect(
        screen.getByText(/The 1XX fields contain the main entry/)
      ).toBeTruthy()
      expect(
        screen.getByText(/Identify fields 100, 245, 264, and 300/)
      ).toBeTruthy()
      expect(screen.getByText('978-0-06-112008-4')).toBeTruthy()
    })

    it('does NOT show the Check Answer button (no silent auto-pass)', () => {
      render(<SandboxPlayer content={articleShaped} onComplete={() => {}} />)
      expect(screen.queryByText('Check Answer')).toBeNull()
    })

    it('does NOT call onComplete on mount', () => {
      const onComplete = vi.fn()
      render(<SandboxPlayer content={articleShaped} onComplete={onComplete} />)
      expect(onComplete).not.toHaveBeenCalled()
    })

    it('calls onComplete only when Mark as reviewed is clicked', () => {
      const onComplete = vi.fn()
      render(<SandboxPlayer content={articleShaped} onComplete={onComplete} />)
      fireEvent.click(screen.getByText('Mark as reviewed'))
      expect(onComplete).toHaveBeenCalledTimes(1)
    })
  })

  describe('regular sandbox content still uses the interactive variant', () => {
    it('renders the code editor when sandbox_type=code', () => {
      const codeContent: SandboxContent = {
        sandbox_type: 'code',
        instructions: 'Write a function.',
        initial_code: '// start here',
        expected_output: '42',
      }
      render(<SandboxPlayer content={codeContent} onComplete={() => {}} />)
      // Code path keeps the Check Answer button.
      expect(screen.getByText('Check Answer')).toBeTruthy()
      // Fallback notice must not appear.
      expect(
        screen.queryByText(/interactive component coming soon/i)
      ).toBeNull()
    })

    it('treats content with expected_output but no sandbox_type as code (no fallback)', () => {
      // sandbox_type defaults to 'code' when expected_output is present; this
      // exists today for at least one prod lesson and must not regress.
      const content: SandboxContent = {
        instructions: 'Output should equal 42.',
        expected_output: '42',
      }
      render(<SandboxPlayer content={content} onComplete={() => {}} />)
      expect(screen.getByText('Check Answer')).toBeTruthy()
      expect(
        screen.queryByText(/interactive component coming soon/i)
      ).toBeNull()
    })
  })
})
