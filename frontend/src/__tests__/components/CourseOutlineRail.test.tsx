/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="@testing-library/jest-dom/vitest" />
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import { describe, it, expect, vi } from 'vitest'
import CourseOutlineRail from '@/components/training/CourseOutlineRail'
import type { Module } from '@/components/training/training-types'

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) =>
      params ? `${key}:${JSON.stringify(params)}` : key,
  }),
}))

const modules: Module[] = [
  {
    id: 1,
    title: 'Foundations',
    sort_order: 0,
    lessons: [
      {
        id: 7,
        title: 'Intro',
        lesson_type: 'video',
        sort_order: 0,
        content: {},
      },
    ],
  },
]

function setup(extra: Partial<Parameters<typeof CourseOutlineRail>[0]> = {}) {
  return render(
    <CourseOutlineRail
      courseTitle="AI Course"
      modules={modules}
      selectedLessonId={7}
      onSelectCourse={vi.fn()}
      onSelectLesson={vi.fn()}
      onAddModule={vi.fn()}
      onAddLesson={vi.fn()}
      onMoveModule={vi.fn()}
      onMoveLesson={vi.fn()}
      onDeleteModule={vi.fn()}
      onDeleteLesson={vi.fn()}
      onUpdateModuleTitle={vi.fn().mockResolvedValue(undefined)}
      issuesByLesson={{ 7: 2 }}
      {...extra}
    />,
  )
}

describe('CourseOutlineRail', () => {
  it('labels the lesson type glyph (not aria-hidden)', () => {
    setup()
    expect(screen.getByLabelText(/video/i)).toBeInTheDocument()
  })

  it('marks the selected lesson with aria-current', () => {
    setup()
    // The lesson treeitem has aria-current since it's selected
    const treeitems = screen.getAllByRole('treeitem')
    const selectBtn = treeitems.find((b) => b.getAttribute('aria-current') === 'true')
    expect(selectBtn).toBeDefined()
    expect(selectBtn).toHaveAttribute('aria-current', 'true')
  })

  it('shows a text status, not color alone, when a lesson has issues', () => {
    setup()
    expect(screen.getByLabelText(/needs attention/i)).toBeInTheDocument()
  })

  it('has no axe violations', async () => {
    const { container } = setup()
    expect(await axe(container)).toHaveNoViolations()
  })

  it('course-root button has aria-current when no lesson is selected', () => {
    setup({ selectedLessonId: null })
    expect(screen.getByRole('button', { name: /AI Course/i })).toHaveAttribute('aria-current', 'true')
  })

  it('delete module button calls onDeleteModule with correct module index', async () => {
    const onDeleteModule = vi.fn()
    setup({ onDeleteModule })
    const deleteBtn = screen.getByLabelText(/delete module: foundations/i)
    await userEvent.click(deleteBtn)
    expect(onDeleteModule).toHaveBeenCalledWith(0)
  })

  it('delete lesson button calls onDeleteLesson with correct indices', async () => {
    const onDeleteLesson = vi.fn()
    setup({ onDeleteLesson })
    const deleteBtn = screen.getByLabelText(/delete lesson: intro/i)
    await userEvent.click(deleteBtn)
    expect(onDeleteLesson).toHaveBeenCalledWith(0, 0)
  })

  it('shows draft badge when lesson is not published and has no issues', () => {
    const draftModules: Module[] = [
      {
        id: 2,
        title: 'Draft Module',
        sort_order: 0,
        lessons: [
          {
            id: 8,
            title: 'Draft Lesson',
            lesson_type: 'article',
            sort_order: 0,
            content: {},
            is_published: false,
          },
        ],
      },
    ]
    render(
      <CourseOutlineRail
        courseTitle="Test"
        modules={draftModules}
        selectedLessonId={8}
        onSelectCourse={vi.fn()}
        onSelectLesson={vi.fn()}
        onAddModule={vi.fn()}
        onAddLesson={vi.fn()}
        onMoveModule={vi.fn()}
        onMoveLesson={vi.fn()}
        onDeleteModule={vi.fn()}
        onDeleteLesson={vi.fn()}
        onUpdateModuleTitle={vi.fn().mockResolvedValue(undefined)}
        issuesByLesson={{}}
      />,
    )
    expect(screen.getByText('draft')).toBeInTheDocument()
  })

  it('shows course stats header', () => {
    setup()
    expect(screen.getByLabelText('Course stats')).toBeInTheDocument()
  })

  it('module containing selected lesson starts expanded', () => {
    setup()
    // Module toggle button has role="treeitem" with aria-expanded
    const moduleItem = screen.getByRole('treeitem', { name: /1\. foundations/i })
    expect(moduleItem).toHaveAttribute('aria-expanded', 'true')
  })

  it('clicking module header toggles collapse', async () => {
    setup()
    const toggleBtn = screen.getByRole('button', { name: /1\. foundations/i })
    const moduleItem = screen.getByRole('treeitem', { name: /1\. foundations/i })
    await userEvent.click(toggleBtn)
    expect(moduleItem).toHaveAttribute('aria-expanded', 'false')
  })

  it('tree container has role=tree', () => {
    setup()
    expect(screen.getByRole('tree')).toBeInTheDocument()
  })

  it('selected lesson has aria-selected=true', () => {
    setup()
    const lessonItems = screen.getAllByRole('treeitem')
    const selected = lessonItems.find((el) => el.getAttribute('aria-selected') === 'true')
    expect(selected).toBeDefined()
  })

  it('shows unsaved-changes banner when pendingSwitch prop is set', () => {
    setup({
      pendingSwitch: {
        lessonTitle: 'Intro',
        onSave: vi.fn().mockResolvedValue(undefined),
        onDiscard: vi.fn(),
      },
    })
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/unsaved changes/i)).toBeInTheDocument()
  })

  it('clicking edit button puts module title into edit mode', async () => {
    const onUpdateModuleTitle = vi.fn().mockResolvedValue(undefined)
    setup({ onUpdateModuleTitle })
    const editBtn = screen.getByLabelText(/edit title of module 1/i)
    await userEvent.click(editBtn)
    expect(screen.getByRole('textbox', { name: /module 1 title/i })).toBeInTheDocument()
  })

  it('submitting module title edit calls onUpdateModuleTitle', async () => {
    const onUpdateModuleTitle = vi.fn().mockResolvedValue(undefined)
    setup({ onUpdateModuleTitle })
    const editBtn = screen.getByLabelText(/edit title of module 1/i)
    await userEvent.click(editBtn)
    const input = screen.getByRole('textbox', { name: /module 1 title/i })
    fireEvent.change(input, { target: { value: 'New Title' } })
    fireEvent.submit(input.closest('form')!)
    expect(onUpdateModuleTitle).toHaveBeenCalledWith(0, 'New Title')
  })

  it('each lesson row has a grip handle', () => {
    setup()
    expect(screen.getByLabelText(/drag to reorder.*intro/i)).toBeInTheDocument()
  })
})
