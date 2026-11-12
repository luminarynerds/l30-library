/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo, useCallback, useRef, useEffect } from 'react'
import {
  Plus, ChevronUp, ChevronDown, Menu, FileText, Video, HelpCircle,
  Code, Beaker, AlertTriangle, Check, BookOpen, Trash2, GripVertical, Pencil, Copy,
} from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { Module, Lesson } from './training-types'

// ── Types ──────────────────────────────────────────────────────────────────

export interface CourseOutlineRailProps {
  courseTitle: string
  modules: Module[]
  selectedLessonId: number | null
  onSelectCourse: () => void
  onSelectLesson: (lessonId: number) => void
  onAddModule: () => void
  onAddLesson: (moduleId: number) => void
  onMoveModule: (index: number, direction: 'up' | 'down') => void
  onMoveLesson: (moduleIndex: number, lessonIndex: number, direction: 'up' | 'down') => void
  onDeleteModule: (moduleIndex: number) => void
  onDeleteLesson: (moduleIndex: number, lessonIndex: number) => void
  onDuplicateLesson?: (moduleIndex: number, lessonIndex: number) => void
  onUpdateModuleTitle?: (actualModuleIndex: number, title: string) => Promise<void>
  issuesByLesson: Record<number, number>
  pendingSwitch?: {
    lessonTitle: string
    onSave: () => Promise<void>
    onDiscard: () => void
  } | null
}

// ── Lesson-type icon map ───────────────────────────────────────────────────

const LESSON_TYPE_META: Record<
  Lesson['lesson_type'],
  { Icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean | 'true' | 'false' }>; label: string }
> = {
  article: { Icon: FileText,   label: 'Article' },
  video:   { Icon: Video,      label: 'Video'   },
  quiz:    { Icon: HelpCircle, label: 'Quiz'    },
  sandbox: { Icon: Code,       label: 'Sandbox' },
  lab:     { Icon: Beaker,     label: 'Lab'     },
}

// ── Sub-components ─────────────────────────────────────────────────────────

function LessonTypeGlyph({ type }: { type: Lesson['lesson_type'] }) {
  const meta = LESSON_TYPE_META[type] ?? LESSON_TYPE_META.article
  const { Icon, label } = meta
  return (
    // role="img" is required for aria-label on a span (axe aria-prohibited-attr)
    <span role="img" aria-label={label} className="inline-flex items-center shrink-0">
      <Icon className="w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50" aria-hidden="true" />
    </span>
  )
}

function StatusGlyph({
  issueCount,
  isDraft,
}: {
  issueCount: number
  isDraft?: boolean
}) {
  if (issueCount > 0) {
    return (
      <span
        role="img"
        aria-label="needs attention"
        className="inline-flex items-center gap-0.5 text-status-warning-600 dark:text-status-warning-400 shrink-0"
      >
        <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
      </span>
    )
  }
  if (!isDraft) {
    return (
      <span
        role="img"
        aria-label="published"
        className="inline-flex items-center shrink-0 text-status-success-600 dark:text-status-success-400"
      >
        <Check className="w-3.5 h-3.5" aria-hidden="true" />
      </span>
    )
  }
  return (
    <span className="text-xs font-medium text-lsc-dark/50 dark:text-lsc-cream/50 shrink-0 uppercase tracking-wide">
      draft
    </span>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function CourseOutlineRail({
  courseTitle,
  modules,
  selectedLessonId,
  onSelectCourse,
  onSelectLesson,
  onAddModule,
  onAddLesson,
  onMoveModule,
  onMoveLesson,
  onDeleteModule,
  onDeleteLesson,
  onDuplicateLesson,
  onUpdateModuleTitle,
  issuesByLesson,
  pendingSwitch,
}: CourseOutlineRailProps) {
  const { t } = useTranslation()
  const visibleModules = modules.filter((m) => !m.isDeleted)
  const [railOpen, setRailOpen] = useState(false)

  // ── Stats ────────────────────────────────────────────────────────────────
  const totalLessons = useMemo(
    () => visibleModules.reduce((sum, m) => sum + m.lessons.filter((l) => !l.isDeleted).length, 0),
    [visibleModules],
  )
  const lessonsWithIssues = useMemo(
    () => Object.keys(issuesByLesson).filter((id) => (issuesByLesson[Number(id)] ?? 0) > 0).length,
    [issuesByLesson],
  )

  // ── Per-module collapse ──────────────────────────────────────────────────
  const initialCollapsed = useMemo(() => {
    const set = new Set<string | number>()
    visibleModules.forEach((m, mIdx) => {
      const key = m.id ?? `new-${mIdx}`
      const hasSelected = m.lessons.some((l) => !l.isDeleted && l.id === selectedLessonId)
      if (!hasSelected) set.add(key)
    })
    return set
    // only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const [collapsedModules, setCollapsedModules] = useState<Set<string | number>>(initialCollapsed)

  const toggleModule = useCallback((key: string | number) => {
    setCollapsedModules((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])

  // ── Keyboard tree navigation ─────────────────────────────────────────────
  const [focusedKey, setFocusedKey] = useState<string | null>(() => {
    if (selectedLessonId !== null) return `lesson-${selectedLessonId}`
    const first = visibleModules[0]
    if (!first) return null
    return String(first.id ?? 'new-0')
  })

  const treeItems = useMemo(() => {
    const items: Array<{
      key: string
      type: 'module' | 'lesson'
      moduleKey: string | number
      lessonId?: number
      actualModuleIndex: number
      actualLessonIndex?: number
    }> = []
    visibleModules.forEach((m) => {
      const actualMIdx = modules.findIndex((mod) => mod === m)
      const mKey = m.id ?? `new-${actualMIdx}`
      items.push({ key: String(mKey), type: 'module', moduleKey: mKey, actualModuleIndex: actualMIdx })
      if (!collapsedModules.has(mKey)) {
        m.lessons.filter((l) => !l.isDeleted).forEach((l) => {
          const actualLIdx = m.lessons.findIndex((lesson) => lesson === l)
          items.push({
            key: `lesson-${l.id ?? actualLIdx}`,
            type: 'lesson',
            moduleKey: mKey,
            lessonId: l.id,
            actualModuleIndex: actualMIdx,
            actualLessonIndex: actualLIdx,
          })
        })
      }
    })
    return items
  }, [visibleModules, collapsedModules, modules])

  const handleTreeKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const currentIdx = treeItems.findIndex((item) => item.key === focusedKey)
      const currentItem = currentIdx >= 0 ? treeItems[currentIdx] : null

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        const next = treeItems[currentIdx + 1]
        if (next) { setFocusedKey(next.key); document.getElementById(`treeitem-${next.key}`)?.focus() }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        const prev = treeItems[currentIdx - 1]
        if (prev) { setFocusedKey(prev.key); document.getElementById(`treeitem-${prev.key}`)?.focus() }
      } else if (e.key === 'ArrowRight' && currentItem?.type === 'module') {
        e.preventDefault()
        if (collapsedModules.has(currentItem.moduleKey)) {
          toggleModule(currentItem.moduleKey)
        } else {
          const firstChild = treeItems[currentIdx + 1]
          if (firstChild?.type === 'lesson') { setFocusedKey(firstChild.key); document.getElementById(`treeitem-${firstChild.key}`)?.focus() }
        }
      } else if (e.key === 'ArrowLeft' && currentItem) {
        e.preventDefault()
        if (currentItem.type === 'module' && !collapsedModules.has(currentItem.moduleKey)) {
          toggleModule(currentItem.moduleKey)
        } else if (currentItem.type === 'lesson') {
          const parent = treeItems.find((i) => i.type === 'module' && i.moduleKey === currentItem.moduleKey)
          if (parent) { setFocusedKey(parent.key); document.getElementById(`treeitem-${parent.key}`)?.focus() }
        }
      } else if ((e.key === 'Enter' || e.key === ' ') && currentItem) {
        e.preventDefault()
        if (currentItem.type === 'lesson' && currentItem.lessonId !== undefined) onSelectLesson(currentItem.lessonId)
        else if (currentItem.type === 'module') toggleModule(currentItem.moduleKey)
      }
    },
    [treeItems, focusedKey, collapsedModules, toggleModule, onSelectLesson],
  )

  // ── Inline module title editing ───────────────────────────────────────────
  const [editingModuleKey, setEditingModuleKey] = useState<string | number | null>(null)
  const [editingTitle, setEditingTitle] = useState('')
  const editInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editingModuleKey !== null) {
      editInputRef.current?.focus()
      editInputRef.current?.select()
    }
  }, [editingModuleKey])

  // ── DnD drag-to-reorder ───────────────────────────────────────────────────
  const [draggingKey, setDraggingKey] = useState<string | null>(null)
  const [dragOverKey, setDragOverKey] = useState<string | null>(null)
  const [dndAnnounce, setDndAnnounce] = useState('')

  const handleLessonDragStart = useCallback((e: React.DragEvent, key: string) => {
    setDraggingKey(key)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', key)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent, key: string) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverKey(key)
  }, [])

  const handleDragEnd = useCallback(() => {
    setDraggingKey(null)
    setDragOverKey(null)
  }, [])

  const handleLessonDrop = useCallback(
    (e: React.DragEvent, targetModuleIndex: number, targetLessonIndex: number) => {
      e.preventDefault()
      const draggedKey = e.dataTransfer.getData('text/plain')
      if (!draggedKey) return

      let draggedModuleIndex = -1
      let draggedLessonIndex = -1
      modules.forEach((m, mi) => {
        m.lessons.forEach((l, li) => {
          if (`lesson-${l.id}` === draggedKey) { draggedModuleIndex = mi; draggedLessonIndex = li }
        })
      })
      if (draggedModuleIndex < 0) return

      if (draggedModuleIndex !== targetModuleIndex) {
        setDndAnnounce('Cross-module reordering is not supported. Use the arrow buttons.')
        setDraggingKey(null); setDragOverKey(null)
        return
      }

      if (draggedLessonIndex < targetLessonIndex) {
        for (let i = draggedLessonIndex; i < targetLessonIndex; i++) onMoveLesson(draggedModuleIndex, i, 'down')
      } else if (draggedLessonIndex > targetLessonIndex) {
        for (let i = draggedLessonIndex; i > targetLessonIndex; i--) onMoveLesson(draggedModuleIndex, i, 'up')
      }

      setDndAnnounce(`Lesson moved to position ${targetLessonIndex + 1}.`)
      setDraggingKey(null); setDragOverKey(null)
    },
    [modules, onMoveLesson],
  )

  const handleModuleDrop = useCallback(
    (e: React.DragEvent, targetModuleIndex: number) => {
      e.preventDefault()
      const draggedKey = e.dataTransfer.getData('text/plain')
      let draggedModuleIndex = -1
      modules.forEach((m, mi) => { if (`module-${m.id}` === draggedKey) draggedModuleIndex = mi })
      if (draggedModuleIndex < 0 || draggedModuleIndex === targetModuleIndex) return

      if (draggedModuleIndex < targetModuleIndex) {
        for (let i = draggedModuleIndex; i < targetModuleIndex; i++) onMoveModule(i, 'down')
      } else {
        for (let i = draggedModuleIndex; i > targetModuleIndex; i--) onMoveModule(i, 'up')
      }
      setDndAnnounce(`Module moved to position ${targetModuleIndex + 1}.`)
      setDraggingKey(null); setDragOverKey(null)
    },
    [modules, onMoveModule],
  )

  return (
    <nav
      aria-label="Course outline"
      className="
        bg-lsc-white dark:bg-earth-800
        border border-lsc-border dark:border-earth-700
        rounded-xl
        flex flex-col
        text-sm
        lg:sticky lg:top-6 lg:self-start
        lg:max-h-[calc(100vh-3rem)]
      "
    >
      {/* ── Narrow-screen disclosure: visible below lg, hides rail body ── */}
      <button
        type="button"
        onClick={() => setRailOpen((o) => !o)}
        aria-expanded={railOpen}
        aria-controls="course-outline-body"
        className="
          lg:hidden flex items-center gap-2 px-4 py-3 w-full text-left
          text-sm font-medium text-lsc-dark dark:text-lsc-cream
          border-b border-lsc-border dark:border-earth-700
          hover:bg-lsc-cream dark:hover:bg-earth-700
          focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-inset
          rounded-t-xl
        "
      >
        <Menu className="w-4 h-4 shrink-0" aria-hidden="true" />
        Jump to lesson
        <ChevronDown
          className={["w-4 h-4 shrink-0 ml-auto motion-safe:transition-transform", railOpen ? "rotate-180" : ""].join(" ")}
          aria-hidden="true"
        />
      </button>

      {/* ── Outline body: always visible on lg+, toggled on narrow ── */}
      <div
        id="course-outline-body"
        className={["flex flex-col lg:overflow-y-auto", railOpen ? "" : "hidden lg:flex"].join(" ")}
      >
        {/* ── Unsaved-changes banner ── */}
        {pendingSwitch && (
          <div
            role="alert"
            className="mx-3 mt-3 mb-1 p-3 rounded-lg bg-status-warning-100 dark:bg-status-warning-900/30 border border-status-warning-300 dark:border-status-warning-700 text-xs text-status-warning-900 dark:text-status-warning-100"
          >
            <p className="font-medium mb-2">Unsaved changes in &quot;{pendingSwitch.lessonTitle}&quot;</p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void pendingSwitch.onSave()}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-status-warning-600 text-white hover:bg-status-warning-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose min-h-[36px]"
              >
                Save
              </button>
              <button
                type="button"
                onClick={pendingSwitch.onDiscard}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-status-warning-700 dark:text-status-warning-300 hover:bg-status-warning-200 dark:hover:bg-status-warning-800/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose min-h-[36px]"
              >
                Discard
              </button>
            </div>
          </div>
        )}

        {/* ── aria-live region for DnD announcements ── */}
        <div aria-live="assertive" aria-atomic="true" className="sr-only">{dndAnnounce}</div>

        {/* ── Course title row (root selection) ── */}
        <div className="px-4 pt-4 pb-3">
          <h2
            className="
              text-xs font-semibold uppercase tracking-wider
              text-lsc-dark/60 dark:text-lsc-cream/60
              mb-2
            "
          >
            Course outline
          </h2>

          {/* Stats strip */}
          <div
            aria-label="Course stats"
            className="flex flex-wrap gap-x-3 gap-y-0.5 mb-3 text-xs text-lsc-dark/60 dark:text-lsc-cream/60"
          >
            <span>{t('admin.courseOutlineRail.moduleCount', { count: visibleModules.length })}</span>
            <span>{t('admin.courseOutlineRail.lessonCount', { count: totalLessons })}</span>
            {lessonsWithIssues > 0 && (
              <span className="text-status-warning-600 dark:text-status-warning-400">
                {t('admin.courseOutlineRail.issueCount', { count: lessonsWithIssues })}
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={onSelectCourse}
            aria-current={selectedLessonId === null ? 'true' : undefined}
            className={[
              'w-full flex items-center gap-2.5 px-3 py-2.5 text-left rounded-lg min-h-[44px]',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose',
              'hover:bg-lsc-cream dark:hover:bg-earth-700 motion-safe:transition-colors',
              selectedLessonId === null
                ? 'border-l-4 border-lsc-rose bg-lsc-cream/60 dark:bg-earth-700/60 font-semibold text-lsc-dark dark:text-lsc-cream'
                : 'border-l-4 border-transparent text-lsc-dark/75 dark:text-lsc-cream/75',
            ].join(' ')}
          >
            <BookOpen className="w-4 h-4 shrink-0 text-lsc-rose" aria-hidden="true" />
            <span className="truncate text-sm">{courseTitle}</span>
            <span className="sr-only"> — {t('admin.courseOutlineRail.courseSettings')}</span>
          </button>
        </div>

        {/* ── Module + lesson list ── */}
        <div className="flex flex-col px-3 pb-4 gap-3">
          <div
            role="tree"
            aria-label="Course modules and lessons"
            className="flex flex-col gap-2"
            onKeyDown={handleTreeKeyDown}
          >
            {visibleModules.length === 0 ? (
              <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60 py-3 px-2 text-center">
                {t('admin.courseOutlineRail.noModules')}
              </p>
            ) : (
              visibleModules.map((module, mIndex) => {
                const actualModuleIndex = modules.findIndex((m) => m === module)
                const visibleLessons = module.lessons.filter((l) => !l.isDeleted)
                const moduleLabel = module.title || `Module ${mIndex + 1}`
                const moduleKey = module.id ?? `new-${mIndex}`
                const isExpanded = !collapsedModules.has(moduleKey)
                const lessonListId = `module-lessons-${moduleKey}`

                return (
                  <div
                    role="treeitem"
                    aria-expanded={isExpanded}
                    aria-level={1}
                    aria-selected={false}
                    id={`treeitem-${String(moduleKey)}`}
                    tabIndex={focusedKey === String(moduleKey) ? 0 : -1}
                    onFocus={() => setFocusedKey(String(moduleKey))}
                    key={module.id ?? `new-${mIndex}`}
                    draggable={true}
                    onDragStart={(e) => {
                      setDraggingKey(`module-${module.id}`)
                      e.dataTransfer.effectAllowed = 'move'
                      e.dataTransfer.setData('text/plain', `module-${module.id}`)
                    }}
                    onDragOver={(e) => handleDragOver(e, `module-${module.id ?? mIndex}`)}
                    onDrop={(e) => handleModuleDrop(e, actualModuleIndex)}
                    onDragEnd={handleDragEnd}
                    className={
                      dragOverKey === `module-${module.id ?? mIndex}` && draggingKey !== `module-${module.id}`
                        ? 'ring-2 ring-lsc-rose rounded-lg'
                        : undefined
                    }
                  >
                    {/* Module header */}
                    <div className="flex items-center gap-1 mb-1 px-1">
                      {/* Module toggle / inline edit */}
                      {editingModuleKey === moduleKey ? (
                        <form
                          className="flex-1 flex items-center gap-1"
                          onSubmit={async (e) => {
                            e.preventDefault()
                            const trimmed = editingTitle.trim()
                            if (trimmed && onUpdateModuleTitle) await onUpdateModuleTitle(actualModuleIndex, trimmed)
                            setEditingModuleKey(null)
                          }}
                        >
                          <input
                            ref={editInputRef}
                            type="text"
                            value={editingTitle}
                            onChange={(e) => setEditingTitle(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Escape') setEditingModuleKey(null) }}
                            onBlur={async () => {
                              const trimmed = editingTitle.trim()
                              if (trimmed && trimmed !== moduleLabel && onUpdateModuleTitle) {
                                await onUpdateModuleTitle(actualModuleIndex, trimmed)
                              }
                              setEditingModuleKey(null)
                            }}
                            aria-label={`Module ${mIndex + 1} title`}
                            className="flex-1 text-sm font-semibold px-2 py-1 rounded-lg border border-lsc-rose bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
                          />
                        </form>
                      ) : (
                        <button
                          type="button"
                          tabIndex={-1}
                          onClick={() => toggleModule(moduleKey)}
                          onDoubleClick={() => { setEditingModuleKey(moduleKey); setEditingTitle(moduleLabel) }}
                          className="flex-1 flex items-center gap-1.5 px-1.5 py-1 text-left rounded-lg text-xs font-semibold uppercase tracking-wider text-lsc-dark/60 dark:text-lsc-cream/60 hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus-visible:ring-1 focus-visible:ring-lsc-rose motion-safe:transition-colors"
                        >
                          <ChevronDown
                            className={["w-3.5 h-3.5 shrink-0 motion-safe:transition-transform", isExpanded ? "" : "-rotate-90"].join(" ")}
                            aria-hidden="true"
                          />
                          {mIndex + 1}. {moduleLabel}
                        </button>
                      )}

                      <div className="flex items-center gap-0.5 shrink-0">
                        {/* Edit title button */}
                        {onUpdateModuleTitle && (
                          <button
                            type="button"
                            onClick={() => { setEditingModuleKey(moduleKey); setEditingTitle(moduleLabel) }}
                            aria-label={`Edit title of module ${mIndex + 1}: ${moduleLabel}`}
                            className="p-1.5 rounded-lg text-lsc-dark/50 dark:text-lsc-cream/50 hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus-visible:ring-1 focus-visible:ring-lsc-rose min-w-[32px] min-h-[32px] flex items-center justify-center"
                          >
                            <Pencil className="w-3.5 h-3.5" aria-hidden="true" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => onMoveModule(actualModuleIndex, 'up')}
                          disabled={mIndex === 0}
                          aria-label={`Move module ${mIndex + 1} up`}
                          className="
                            p-1.5 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70
                            hover:bg-lsc-cream dark:hover:bg-earth-700
                            disabled:opacity-30 disabled:cursor-not-allowed
                            focus:outline-none focus-visible:ring-1 focus-visible:ring-lsc-rose
                            min-w-[32px] min-h-[32px] flex items-center justify-center
                          "
                        >
                          <ChevronUp className="w-3.5 h-3.5" aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          onClick={() => onMoveModule(actualModuleIndex, 'down')}
                          disabled={mIndex === visibleModules.length - 1}
                          aria-label={`Move module ${mIndex + 1} down`}
                          className="
                            p-1.5 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70
                            hover:bg-lsc-cream dark:hover:bg-earth-700
                            disabled:opacity-30 disabled:cursor-not-allowed
                            focus:outline-none focus-visible:ring-1 focus-visible:ring-lsc-rose
                            min-w-[32px] min-h-[32px] flex items-center justify-center
                          "
                        >
                          <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
                        </button>
                        <button
                          type="button"
                          onClick={() => onDeleteModule(actualModuleIndex)}
                          aria-label={`Delete module: ${moduleLabel}`}
                          className="
                            p-1.5 rounded-lg text-status-danger-600 dark:text-status-danger-400
                            hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30
                            focus:outline-none focus-visible:ring-1 focus-visible:ring-status-danger-600
                            min-w-[32px] min-h-[32px] flex items-center justify-center
                          "
                        >
                          <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                        </button>
                      </div>
                    </div>

                    {/* Lesson rows — collapsed when module is collapsed */}
                    {isExpanded && (
                      <>
                        {visibleLessons.length > 0 ? (
                          <ul
                            id={lessonListId}
                            role="group"
                            className="space-y-0.5 ml-2 border-l-2 border-lsc-border/60 dark:border-earth-600/60 pl-2"
                          >
                            {visibleLessons.map((lesson, lIndex) => {
                              const actualLessonIndex = module.lessons.findIndex((l) => l === lesson)
                              const isSelected = lesson.id !== undefined && lesson.id === selectedLessonId
                              const issueCount = lesson.id !== undefined ? (issuesByLesson[lesson.id] ?? 0) : 0
                              const lessonLabel = lesson.title || 'Untitled lesson'
                              const lessonKey = `lesson-${lesson.id ?? lIndex}`

                              return (
                                <li
                                  role="none"
                                  key={lesson.id ?? `new-lesson-${lIndex}`}
                                  draggable={true}
                                  onDragStart={(e) => handleLessonDragStart(e, `lesson-${lesson.id}`)}
                                  onDragOver={(e) => handleDragOver(e, lessonKey)}
                                  onDrop={(e) => handleLessonDrop(e, actualModuleIndex, actualLessonIndex)}
                                  onDragEnd={handleDragEnd}
                                  className={
                                    dragOverKey === lessonKey && draggingKey !== `lesson-${lesson.id}`
                                      ? 'ring-2 ring-lsc-rose rounded-lg'
                                      : undefined
                                  }
                                >
                                  <div className="flex items-center gap-1">
                                    {/* Grip handle */}
                                    <button
                                      type="button"
                                      aria-label={`Drag to reorder: ${lessonLabel}`}
                                      className="shrink-0 p-1 cursor-grab text-lsc-dark/30 dark:text-lsc-cream/30 hover:text-lsc-dark/60 dark:hover:text-lsc-cream/60 focus:outline-none focus-visible:ring-1 focus-visible:ring-lsc-rose rounded-lg min-w-[28px] min-h-[44px] flex items-center justify-center"
                                      tabIndex={-1}
                                    >
                                      <GripVertical className="w-3.5 h-3.5" aria-hidden="true" />
                                    </button>

                                    {/* Lesson select button */}
                                    <button
                                      type="button"
                                      role="treeitem"
                                      aria-selected={isSelected}
                                      id={`treeitem-${lessonKey}`}
                                      tabIndex={focusedKey === lessonKey ? 0 : -1}
                                      onClick={() => {
                                        if (lesson.id !== undefined) onSelectLesson(lesson.id)
                                      }}
                                      onFocus={() => setFocusedKey(lessonKey)}
                                      aria-current={isSelected ? 'true' : undefined}
                                      className={[
                                        'flex-1 flex items-center gap-2 px-2.5 py-2 text-left rounded-lg min-h-[44px]',
                                        'focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose',
                                        'hover:bg-lsc-cream dark:hover:bg-earth-700 motion-safe:transition-colors',
                                        isSelected
                                          ? 'border-l-4 border-lsc-rose bg-lsc-cream/60 dark:bg-earth-700/60 font-semibold text-lsc-dark dark:text-lsc-cream'
                                          : 'border-l-4 border-transparent text-lsc-dark/75 dark:text-lsc-cream/75',
                                      ].join(' ')}
                                    >
                                      <LessonTypeGlyph type={lesson.lesson_type} />
                                      <span className="truncate text-sm flex-1">{lessonLabel}</span>
                                      {lesson.estimated_minutes != null && (
                                        <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 shrink-0">
                                          {lesson.estimated_minutes}m
                                        </span>
                                      )}
                                      <StatusGlyph issueCount={issueCount} isDraft={lesson.is_published !== true} />
                                    </button>

                                    {/* Reorder controls */}
                                    <div className="flex flex-col shrink-0 gap-0.5">
                                      <button
                                        type="button"
                                        onClick={() => onMoveLesson(actualModuleIndex, actualLessonIndex, 'up')}
                                        disabled={lIndex === 0}
                                        aria-label={`Move lesson ${lIndex + 1} up`}
                                        className="
                                          p-0.5 rounded text-lsc-dark/40 dark:text-lsc-cream/40
                                          hover:bg-lsc-cream dark:hover:bg-earth-700
                                          disabled:opacity-20 disabled:cursor-not-allowed
                                          focus:outline-none focus-visible:ring-1 focus-visible:ring-lsc-rose
                                          min-w-[20px] min-h-[20px] flex items-center justify-center
                                        "
                                      >
                                        <ChevronUp className="w-3 h-3" aria-hidden="true" />
                                      </button>
                                      <button
                                        type="button"
                                        onClick={() => onMoveLesson(actualModuleIndex, actualLessonIndex, 'down')}
                                        disabled={lIndex === visibleLessons.length - 1}
                                        aria-label={`Move lesson ${lIndex + 1} down`}
                                        className="
                                          p-0.5 rounded text-lsc-dark/40 dark:text-lsc-cream/40
                                          hover:bg-lsc-cream dark:hover:bg-earth-700
                                          disabled:opacity-20 disabled:cursor-not-allowed
                                          focus:outline-none focus-visible:ring-1 focus-visible:ring-lsc-rose
                                          min-w-[20px] min-h-[20px] flex items-center justify-center
                                        "
                                      >
                                        <ChevronDown className="w-3 h-3" aria-hidden="true" />
                                      </button>
                                    </div>

                                    {/* Duplicate lesson */}
                                    {onDuplicateLesson && (
                                      <button
                                        type="button"
                                        onClick={() => onDuplicateLesson(actualModuleIndex, actualLessonIndex)}
                                        aria-label={`Duplicate lesson: ${lessonLabel}`}
                                        className="
                                          shrink-0 p-1 rounded-lg text-lsc-dark/50 dark:text-lsc-cream/50
                                          hover:bg-lsc-cream dark:hover:bg-earth-700
                                          focus:outline-none focus-visible:ring-1 focus-visible:ring-lsc-rose
                                          min-w-[28px] min-h-[44px] flex items-center justify-center
                                        "
                                      >
                                        <Copy className="w-3.5 h-3.5" aria-hidden="true" />
                                      </button>
                                    )}
                                    {/* Delete lesson control */}
                                    <button
                                      type="button"
                                      onClick={() => onDeleteLesson(actualModuleIndex, actualLessonIndex)}
                                      aria-label={`Delete lesson: ${lessonLabel}`}
                                      className="
                                        shrink-0 p-1 rounded-lg text-status-danger-600 dark:text-status-danger-400
                                        hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30
                                        focus:outline-none focus-visible:ring-1 focus-visible:ring-status-danger-600
                                        min-w-[28px] min-h-[44px] flex items-center justify-center
                                      "
                                    >
                                      <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                                    </button>
                                  </div>
                                </li>
                              )
                            })}
                          </ul>
                        ) : (
                          <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50 py-2 px-3 ml-2 italic">
                            {t('admin.courseOutlineRail.noLessons')}
                          </p>
                        )}

                        {/* Add lesson button */}
                        {module.id !== undefined && (
                          <button
                            type="button"
                            onClick={() => onAddLesson(module.id as number)}
                            className="
                              w-full flex items-center gap-1.5 px-3 py-2 ml-2 mt-1 text-left rounded-lg
                              text-sm text-lsc-dark/60 dark:text-lsc-cream/60
                              hover:bg-lsc-cream dark:hover:bg-earth-700
                              hover:text-lsc-rose dark:hover:text-lsc-rose
                              focus:outline-none focus-visible:ring-1 focus-visible:ring-lsc-rose
                              motion-safe:transition-colors
                              min-h-[44px]
                            "
                            aria-label={`Add lesson to ${moduleLabel}`}
                          >
                            <Plus className="w-3.5 h-3.5" aria-hidden="true" />
                            Add lesson
                          </button>
                        )}
                      </>
                    )}
                  </div>
                )
              })
            )}

          </div>{/* end role=tree */}

          {/* Add module button */}
          <button
            type="button"
            onClick={onAddModule}
            className="
              w-full flex items-center gap-2 px-3 py-2.5 rounded-lg
              text-sm text-lsc-dark/60 dark:text-lsc-cream/60
              border border-dashed border-lsc-border dark:border-earth-600
              hover:border-lsc-rose hover:text-lsc-rose
              focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose
              motion-safe:transition-colors
              min-h-[44px]
            "
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            Add module
          </button>
        </div>{/* end scroll wrapper */}
      </div>{/* end course-outline-body */}
    </nav>
  )
}
