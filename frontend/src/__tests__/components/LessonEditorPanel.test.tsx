/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom/vitest" />
import type { ForwardedRef } from 'react'
import { render, screen, act, waitFor, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { axe } from 'jest-axe'

vi.mock('@/lib/sentry-lazy', () => ({
  init: vi.fn(),
  captureException: vi.fn(),
  captureMessage: vi.fn(),
  addBreadcrumb: vi.fn(),
}))

const { stableI18n } = vi.hoisted(() => {
  const t = (key: string, fallback?: string | Record<string, unknown>) =>
    typeof fallback === 'string' ? fallback : key
  return {
    stableI18n: { t, language: 'en', setLanguage: () => {}, isRTL: false },
  }
})
vi.mock('@/i18n', () => ({
  useTranslation: () => stableI18n,
}))

vi.mock('@/components/training/MediaUploadField', () => ({
  default: () => <div data-testid="media-upload-stub" />,
}))
vi.mock('../../components/training/MediaUploadField', () => ({
  default: () => <div data-testid="media-upload-stub" />,
}))

vi.mock('@/components/AutoSaveIndicator', () => ({
  default: () => <div data-testid="auto-save-indicator-stub" />,
}))
vi.mock('../../components/AutoSaveIndicator', () => ({
  default: () => <div data-testid="auto-save-indicator-stub" />,
}))

vi.mock('@/components/ConfirmDialog', () => ({
  default: () => <div data-testid="confirm-dialog-stub" />,
}))
vi.mock('../../components/ConfirmDialog', () => ({
  default: () => <div data-testid="confirm-dialog-stub" />,
}))

// Mock RichTextEditor (imperative ref, jsdom won't render TipTap)
// RichTextEditor uses forwardRef; mock must too so imperative setContent calls
// don't crash. Factory is self-contained (vi.mock hoists, no outer var refs).
vi.mock('@/components/editor/RichTextEditor', async () => {
  const { forwardRef, useImperativeHandle } = await import('react')
  const { vi: _vi } = await import('vitest')
  const Mock = forwardRef((_props: unknown, ref: ForwardedRef<{ setContent: () => void }>) => {
    useImperativeHandle(ref, () => ({ setContent: _vi.fn() }))
    return <div data-testid="rich-text-editor" />
  })
  return { default: Mock }
})
vi.mock('../../components/editor/RichTextEditor', async () => {
  const { forwardRef, useImperativeHandle } = await import('react')
  const { vi: _vi } = await import('vitest')
  const Mock = forwardRef((_props: unknown, ref: ForwardedRef<{ setContent: () => void }>) => {
    useImperativeHandle(ref, () => ({ setContent: _vi.fn() }))
    return <div data-testid="rich-text-editor" />
  })
  return { default: Mock }
})

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}))

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))
vi.mock('@/api/api', () => ({
  default: apiMock,
  api: apiMock,
}))
vi.mock('../../api/api', () => ({
  default: apiMock,
  api: apiMock,
}))

import LessonEditorPanel from '@/components/LessonEditorPanel'

describe('LessonEditorPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.get.mockResolvedValue({
      id: 7,
      module_id: 1,
      title: 'Intro',
      lesson_type: 'article',
      content: { body: '<p>Body text</p>' },
      quiz_questions: [],
      estimated_minutes: 10,
      sensory_notes: '',
      facilitator_notes: '',
      xp_reward: 10,
      summary: '',
      visual_aid_url: '',
      audio_narration_url: '',
    })
    apiMock.put.mockResolvedValue({})
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('loads lesson and shows title', async () => {
    render(<LessonEditorPanel lessonId={7} onClose={vi.fn()} />)
    const titleInput = await screen.findByDisplayValue('Intro')
    expect(titleInput).toBeInTheDocument()
    expect(screen.getByTestId('rich-text-editor')).toBeInTheDocument()
  })

  it('renders facilitator notes only once', async () => {
    render(<LessonEditorPanel lessonId={7} onClose={vi.fn()} />)
    await screen.findByDisplayValue('Intro')
    const labels = screen.getAllByText(/facilitator notes/i)
    expect(labels).toHaveLength(1)
  })

  it('has no accessibility violations', async () => {
    const { container } = render(<LessonEditorPanel lessonId={7} onClose={vi.fn()} />)
    await screen.findByDisplayValue('Intro')
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  // Real bug vector: a NEW quiz question (isNew: true, no id) must be POSTed
  // exactly once even if the autosave debounce fires a second time before the
  // state write from the first save has settled. Pre-fix: the second debounce
  // would see isNew still true (stale closure) and POST again, creating a dupe.
  // Post-fix: saveQuizQuestionsFor writes the server id back via setQuizQuestions,
  // so the second debounce's snapshot has id set and calls PUT instead.
  it('calls POST exactly once for a new question across two debounce cycles', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })

    apiMock.get.mockResolvedValue({
      id: 7,
      module_id: 1,
      title: 'Quiz lesson',
      lesson_type: 'quiz',
      content: {},
      quiz_questions: [],
      estimated_minutes: 10,
      sensory_notes: '',
      facilitator_notes: '',
      xp_reward: 10,
      summary: '',
      visual_aid_url: '',
      audio_narration_url: '',
    })
    apiMock.put.mockResolvedValue({})
    // POST returns the server-assigned id — triggers setQuizQuestions write-back.
    apiMock.post.mockResolvedValue({ id: 55 })

    const { rerender } = render(<LessonEditorPanel lessonId={7} onClose={vi.fn()} />)

    // Wait for load; lesson title is non-blank so autosave becomes enabled.
    await waitFor(() => expect(screen.getByDisplayValue('Quiz lesson')).toBeInTheDocument())

    // Simulate adding a new question by re-rendering with the panel's internal
    // addQuizQuestion state. We drive this by clicking the "Add Question" button.
    const addBtn = screen.getByRole('button', { name: /add question/i })
    await act(async () => {
      addBtn.click()
    })

    // First debounce cycle -- should POST the new question.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })
    // Let the post-save state write (setQuizQuestions) propagate.
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledTimes(1))

    // Second debounce cycle -- the state write-back set isNew=false + id=55,
    // so this pass must PUT (update), not POST again.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })
    await act(async () => { await Promise.resolve() })

    // POST must still be exactly 1 -- the second debounce took the PUT path.
    expect(apiMock.post).toHaveBeenCalledTimes(1)
    // And PUT was called (lesson fields + the now-existing question).
    expect(apiMock.put).toHaveBeenCalled()

    void rerender
  })

  // Fix 1 regression: quiz question with an existing id must never call the
  // create (POST) endpoint -- only PUT (update). This guards the inverse of the
  // duplicate-create bug without needing full fake-timer autosave plumbing.
  it('does not call POST create when autosaving a question that already has an id', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })

    apiMock.get.mockResolvedValue({
      id: 7,
      module_id: 1,
      title: 'Quiz lesson',
      lesson_type: 'quiz',
      content: {},
      quiz_questions: [
        {
          id: 42,
          question_text: 'What is a library?',
          question_type: 'multiple_choice',
          options: [{ text: 'A place with books', is_correct: true }],
          explanation: '',
          sort_order: 0,
        },
      ],
      estimated_minutes: 10,
      sensory_notes: '',
      facilitator_notes: '',
      xp_reward: 10,
      summary: '',
      visual_aid_url: '',
      audio_narration_url: '',
    })
    apiMock.put.mockResolvedValue({})
    apiMock.post.mockResolvedValue({ id: 99 })

    render(<LessonEditorPanel lessonId={7} onClose={vi.fn()} />)

    // Wait for load to complete.
    await waitFor(() => expect(screen.getByDisplayValue('Quiz lesson')).toBeInTheDocument())

    // Advance past the 2s autosave debounce.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2500)
    })

    // PUT (update) is expected; POST (create) must never be called for an existing question.
    expect(apiMock.post).not.toHaveBeenCalled()
  })

  // Fix 2 regression: lab/sandbox lessons store their patron-facing text in
  // content.body (LabBody renders it). The editor now uses RichTextEditor
  // instead of a raw textarea -- verify the WYSIWYG editor is shown.
  it('lab lesson shows WYSIWYG editor and edits content.body', async () => {
    apiMock.get.mockResolvedValue({
      id: 12,
      module_id: 1,
      title: 'Sticky Note Lab',
      lesson_type: 'lab',
      content: { body: '# Sticky Note\n\nDo the thing.' },
      quiz_questions: [],
      estimated_minutes: 15,
      sensory_notes: '',
      facilitator_notes: '',
      xp_reward: 15,
      summary: '',
      visual_aid_url: '',
      audio_narration_url: '',
    })

    render(<LessonEditorPanel lessonId={12} onClose={vi.fn()} />)
    await screen.findByDisplayValue('Sticky Note Lab')

    // Should show the shared RichTextEditor, not a raw textarea
    expect(screen.getByTestId('rich-text-editor')).toBeInTheDocument()
    // The dead, never-rendered fields are gone.
    expect(screen.queryByText('Starter Code / Template')).not.toBeInTheDocument()
    expect(screen.queryByText(/Expected Solution/)).not.toBeInTheDocument()
  })

  // Fix 1 regression (data-loss incident 2026-06-19): switching lessons must
  // NOT write the outgoing lesson's content to the incoming lesson id. With no
  // edits the switch-flush must not PUT at all (dirty-gated), and it must never
  // target the new id carrying the old body.
  it('does not flush outgoing lesson content onto the incoming lesson id', async () => {
    apiMock.get.mockImplementation((url: string) => {
      if (url.endsWith('/lessons/10')) {
        return Promise.resolve({
          id: 10, module_id: 1, title: 'Lesson Ten', lesson_type: 'lab',
          content: { body: 'TEN BODY' }, quiz_questions: [],
          estimated_minutes: 10, sensory_notes: '', facilitator_notes: '',
          xp_reward: 10, summary: '', visual_aid_url: '', audio_narration_url: '',
        })
      }
      return Promise.resolve({
        id: 20, module_id: 1, title: 'Lesson Twenty', lesson_type: 'lab',
        content: { body: 'TWENTY BODY' }, quiz_questions: [],
        estimated_minutes: 10, sensory_notes: '', facilitator_notes: '',
        xp_reward: 10, summary: '', visual_aid_url: '', audio_narration_url: '',
      })
    })

    const { rerender } = render(<LessonEditorPanel lessonId={10} onClose={vi.fn()} />)
    await screen.findByDisplayValue('Lesson Ten')

    // Switch lessons with no edits.
    rerender(<LessonEditorPanel lessonId={20} onClose={vi.fn()} />)
    await screen.findByDisplayValue('Lesson Twenty')

    const corrupting = apiMock.put.mock.calls.find(
      ([url, payload]) =>
        url.endsWith('/lessons/20') && payload?.content?.body === 'TEN BODY',
    )
    expect(corrupting).toBeUndefined()

    const anyPutTo20 = apiMock.put.mock.calls.some(([url]) =>
      url.endsWith('/lessons/20'),
    )
    expect(anyPutTo20).toBe(false)
  })

  // Fix: merely opening/loading a lesson must NOT autosave. The debounce treated
  // the initial->loaded data change as an edit and PUT the lesson back (which
  // round-tripped article bodies to HTML just from viewing). Only real edits save.
  it('does not autosave when a lesson is merely opened (no edits)', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })

    render(<LessonEditorPanel lessonId={7} onClose={vi.fn()} />)
    await waitFor(() => expect(screen.getByDisplayValue('Intro')).toBeInTheDocument())

    // Well past the 2s debounce: opening alone must not have saved.
    await act(async () => { await vi.advanceTimersByTimeAsync(2500) })
    expect(apiMock.put).not.toHaveBeenCalled()

    // A real edit still autosaves.
    await act(async () => {
      fireEvent.change(screen.getByDisplayValue('Intro'), { target: { value: 'Intro edited' } })
    })
    await act(async () => { await vi.advanceTimersByTimeAsync(2500) })
    await waitFor(() => expect(apiMock.put).toHaveBeenCalled())
  })

  it('forceSave handle calls putLessonSnapshot with current data', async () => {
    const ref = { current: null as { forceSave: () => Promise<void>; cancelEdits: () => void } | null }
    render(<LessonEditorPanel lessonId={7} onClose={vi.fn()} ref={ref} />)
    await screen.findByDisplayValue('Intro')

    apiMock.put.mockResolvedValue({})
    await act(async () => {
      await ref.current?.forceSave()
    })
    expect(apiMock.put).toHaveBeenCalledWith(
      '/learning/lessons/7',
      expect.objectContaining({ title: 'Intro' })
    )
  })

  it('cancelEdits handle resets lesson state to baseline', async () => {
    const ref = { current: null as { forceSave: () => Promise<void>; cancelEdits: () => void } | null }
    render(<LessonEditorPanel lessonId={7} onClose={vi.fn()} ref={ref} />)
    const titleInput = await screen.findByDisplayValue('Intro')

    fireEvent.change(titleInput, { target: { value: 'Modified' } })
    expect(screen.getByDisplayValue('Modified')).toBeInTheDocument()

    act(() => {
      ref.current?.cancelEdits()
    })
    await waitFor(() => expect(screen.getByDisplayValue('Intro')).toBeInTheDocument())
  })
})
