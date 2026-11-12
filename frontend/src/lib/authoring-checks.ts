/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Single source of truth for the "what's missing" checks consumed by both
 * the per-lesson pill on LessonCard (Wave 2 / W2-B) and the side panel on
 * AdminCourseFormPage (Wave 3). When you add a check here, BOTH surfaces
 * pick it up automatically.
 */

export interface AuthoringLesson {
  id?: number
  title: string
  lesson_type: 'article' | 'video' | 'quiz' | 'sandbox' | 'lab'
  content: Record<string, unknown>
  sort_order: number
}

export interface AuthoringModule {
  id?: number
  title: string
  sort_order: number
  lessons: AuthoringLesson[]
}

export interface AuthoringCourse {
  title: string
  thumbnail_url?: string
  access_level: string
  difficulty: string
}

export type IssueScope =
  | { kind: 'course' }
  | { kind: 'module'; moduleId: number | undefined }
  | { kind: 'lesson'; lessonId: number | undefined }

export interface AuthoringIssue {
  code: string
  message: string
  scope: IssueScope
  fieldId?: string
}

export function parseMissingAltImages(body: unknown): string[] {
  if (typeof body !== 'string' || !body) return []
  const missing: string[] = []
  const re = /(?<!\\)!\[([^\]]*)\]\(([^)]+)\)/g
  let m: RegExpExecArray | null
  while ((m = re.exec(body)) !== null) {
    const alt = (m[1] ?? '').trim()
    const url = (m[2] ?? '').trim()
    if (!alt && url) missing.push(url)
  }
  return missing
}

export function checkLesson(lesson: AuthoringLesson): AuthoringIssue[] {
  const issues: AuthoringIssue[] = []
  const scope: IssueScope = { kind: 'lesson', lessonId: lesson.id }
  const title = lesson.title.trim() || 'untitled'

  if (lesson.lesson_type === 'article') {
    const body = typeof lesson.content?.body === 'string' ? (lesson.content.body as string) : ''
    if (!body.trim()) {
      issues.push({
        code: 'lesson_empty_body',
        message: `Lesson "${title}" has empty body`,
        scope,
        fieldId: lesson.id ? `lesson-${lesson.id}-body` : undefined,
      })
    } else {
      const missingAlt = parseMissingAltImages(body)
      if (missingAlt.length > 0) {
        issues.push({
          code: 'lesson_image_missing_alt',
          message: `Lesson "${title}" has ${missingAlt.length} image(s) without alt text`,
          scope,
          fieldId: lesson.id ? `lesson-${lesson.id}-body` : undefined,
        })
      }
    }
  }

  if (lesson.lesson_type === 'video') {
    const url = typeof lesson.content?.video_url === 'string' ? (lesson.content.video_url as string) : ''
    if (!url.trim()) {
      issues.push({
        code: 'lesson_missing_video_url',
        message: `Video lesson "${title}" is missing video URL`,
        scope,
        fieldId: lesson.id ? `lesson-${lesson.id}-video-url` : undefined,
      })
    }
    const transcript = typeof lesson.content?.transcript === 'string' ? (lesson.content.transcript as string) : ''
    if (!transcript.trim()) {
      issues.push({
        code: 'lesson_missing_transcript',
        message: `Video lesson "${title}" needs a transcript`,
        scope,
        fieldId: lesson.id ? `lesson-${lesson.id}-transcript` : undefined,
      })
    }
  }

  if (lesson.lesson_type === 'quiz') {
    const qs = Array.isArray(lesson.content?.questions) ? (lesson.content.questions as unknown[]) : []
    if (qs.length === 0) {
      issues.push({
        code: 'lesson_no_quiz_questions',
        message: `Quiz "${title}" has no questions`,
        scope,
      })
    }
  }

  return issues
}

export function checkCourse(
  course: AuthoringCourse,
  modules: AuthoringModule[],
): AuthoringIssue[] {
  const issues: AuthoringIssue[] = []

  if (!course.thumbnail_url?.trim()) {
    issues.push({
      code: 'course_missing_thumbnail',
      message: 'Course has no thumbnail image',
      scope: { kind: 'course' },
      fieldId: 'thumbnail_url',
    })
  }

  if (modules.length === 0) {
    issues.push({
      code: 'course_no_modules',
      message: 'Course has no modules yet',
      scope: { kind: 'course' },
    })
  }

  for (const m of modules) {
    if (m.lessons.length === 0) {
      issues.push({
        code: 'module_no_lessons',
        message: `Module "${m.title.trim() || 'untitled'}" has no lessons`,
        scope: { kind: 'module', moduleId: m.id },
      })
    }
  }

  return issues
}

export function collectAllIssues(
  course: AuthoringCourse,
  modules: AuthoringModule[],
): AuthoringIssue[] {
  return [
    ...checkCourse(course, modules),
    ...modules.flatMap(m => m.lessons.flatMap(checkLesson)),
  ]
}

export interface GroupedIssues {
  course: AuthoringIssue[]
  byLesson: Record<number, AuthoringIssue[]>
}

/**
 * Groups all issues by target: course-scoped and module-scoped issues go into
 * `course`; lesson-scoped issues with a known lessonId go into `byLesson`.
 * Lesson issues without an id also fall into `course` since they can't be
 * attributed to a specific lesson row in the rail.
 */
export function groupIssuesByTarget(
  course: AuthoringCourse,
  modules: AuthoringModule[],
): GroupedIssues {
  const all = collectAllIssues(course, modules)
  const result: GroupedIssues = { course: [], byLesson: {} }

  for (const issue of all) {
    if (issue.scope.kind === 'lesson' && issue.scope.lessonId !== undefined) {
      const lid = issue.scope.lessonId
      if (!result.byLesson[lid]) result.byLesson[lid] = []
      result.byLesson[lid].push(issue)
    } else {
      result.course.push(issue)
    }
  }

  return result
}

/**
 * Returns the set of issue codes the user has dismissed (skipped) for a given
 * course. Uses the same localStorage key and shape as WhatsMissingPanel so
 * both surfaces stay in sync without duplicating the persistence logic.
 *
 * Safe to call in non-browser environments (SSR / tests without localStorage):
 * returns an empty Set on any error.
 */
export function getDismissedIssueKeys(courseId: number | string): Set<string> {
  try {
    const raw = localStorage.getItem(`lsc_authoring_dismissed_${courseId}`)
    if (!raw) return new Set()
    const map: Record<string, unknown> = JSON.parse(raw)
    return new Set(Object.keys(map))
  } catch {
    return new Set()
  }
}
