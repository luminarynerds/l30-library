/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import {
  checkLesson,
  checkCourse,
  parseMissingAltImages,
} from '../authoring-checks'

describe('checkLesson — per-lesson checks (Wave 3)', () => {
  it('flags article with empty body', () => {
    const issues = checkLesson({
      id: 1, title: 'X', lesson_type: 'article',
      content: { body: '' }, sort_order: 0,
    })
    expect(issues.find(i => i.code === 'lesson_empty_body')).toBeDefined()
  })

  it('flags article with body containing markdown image that lacks alt', () => {
    const issues = checkLesson({
      id: 1, title: 'X', lesson_type: 'article',
      content: { body: 'Intro\n\n![](http://a.test/img.png)\n\nmore' },
      sort_order: 0,
    })
    expect(issues.find(i => i.code === 'lesson_image_missing_alt')).toBeDefined()
  })

  it('does NOT flag image-with-alt', () => {
    const issues = checkLesson({
      id: 1, title: 'X', lesson_type: 'article',
      content: { body: '![A garden](http://a.test/img.png)' },
      sort_order: 0,
    })
    expect(issues.find(i => i.code === 'lesson_image_missing_alt')).toBeUndefined()
  })

  it('flags video lesson with missing URL', () => {
    const issues = checkLesson({
      id: 1, title: 'X', lesson_type: 'video',
      content: {}, sort_order: 0,
    })
    expect(issues.find(i => i.code === 'lesson_missing_video_url')).toBeDefined()
  })

  it('flags video lesson with empty transcript (a11y patron floor)', () => {
    const issues = checkLesson({
      id: 1, title: 'X', lesson_type: 'video',
      content: { video_url: 'https://youtube.com/x', transcript: '' },
      sort_order: 0,
    })
    expect(issues.find(i => i.code === 'lesson_missing_transcript')).toBeDefined()
  })

  it('does NOT flag video with both URL and transcript', () => {
    const issues = checkLesson({
      id: 1, title: 'X', lesson_type: 'video',
      content: { video_url: 'https://youtube.com/x', transcript: 'Full text here.' },
      sort_order: 0,
    })
    expect(issues).toHaveLength(0)
  })

  it('flags quiz lesson with no questions', () => {
    const issues = checkLesson({
      id: 1, title: 'Q', lesson_type: 'quiz',
      content: { questions: [] }, sort_order: 0,
    })
    expect(issues.find(i => i.code === 'lesson_no_quiz_questions')).toBeDefined()
  })

  it('sandbox and lab lessons return no issues (out of scope this round)', () => {
    const sandbox = checkLesson({ id: 1, title: 'S', lesson_type: 'sandbox', content: {}, sort_order: 0 })
    const lab = checkLesson({ id: 2, title: 'L', lesson_type: 'lab', content: {}, sort_order: 0 })
    expect(sandbox).toHaveLength(0)
    expect(lab).toHaveLength(0)
  })
})

describe('checkCourse — course-level checks (Wave 3)', () => {
  it('flags course missing thumbnail_url', () => {
    const issues = checkCourse({
      title: 'C', thumbnail_url: '', access_level: 'patron', difficulty: 'beginner',
    }, [])
    expect(issues.find(i => i.code === 'course_missing_thumbnail')).toBeDefined()
  })

  it('flags course with zero modules', () => {
    const issues = checkCourse({
      title: 'C', thumbnail_url: 'http://x', access_level: 'patron', difficulty: 'beginner',
    }, [])
    expect(issues.find(i => i.code === 'course_no_modules')).toBeDefined()
  })

  it('flags module with zero lessons (per module)', () => {
    const issues = checkCourse({
      title: 'C', thumbnail_url: 'http://x', access_level: 'patron', difficulty: 'beginner',
    }, [{ id: 5, title: 'M1', sort_order: 0, lessons: [] }])
    const issue = issues.find(i => i.code === 'module_no_lessons')
    expect(issue).toBeDefined()
    expect(issue?.scope).toEqual({ kind: 'module', moduleId: 5 })
  })

  it('returns NO issues for a fully-populated course', () => {
    const issues = checkCourse({
      title: 'C', thumbnail_url: 'http://x', access_level: 'patron', difficulty: 'beginner',
    }, [{ id: 5, title: 'M1', sort_order: 0, lessons: [{ id: 1, title: 'L', lesson_type: 'article', content: { body: 'hi' }, sort_order: 0 }] }])
    expect(issues.filter(i => !i.code.startsWith('lesson_'))).toHaveLength(0)
  })
})

describe('parseMissingAltImages — markdown alt-text scanner', () => {
  it('returns image URLs missing alt text', () => {
    const md = 'before\n![](http://a/1.png) ok ![Has alt](http://a/2.png) ![](http://a/3.gif)'
    const missing = parseMissingAltImages(md)
    expect(missing).toEqual(['http://a/1.png', 'http://a/3.gif'])
  })

  it('returns empty array when all images have alt', () => {
    const md = '![Alt one](u1) ![Alt two](u2)'
    expect(parseMissingAltImages(md)).toEqual([])
  })

  it('ignores escaped brackets', () => {
    const md = '\\![](not-an-image)'
    expect(parseMissingAltImages(md)).toEqual([])
  })

  it('returns empty array on non-string input', () => {
    expect(parseMissingAltImages('')).toEqual([])
    expect(parseMissingAltImages(null as any)).toEqual([])
    expect(parseMissingAltImages(undefined as any)).toEqual([])
  })
})
