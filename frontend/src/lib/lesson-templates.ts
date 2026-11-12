// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later

export interface LessonTemplate {
  id: string
  label: string
  defaultContent: Record<string, unknown>
  lessonType: 'article' | 'video' | 'quiz' | 'sandbox' | 'lab'
}

export const LESSON_TEMPLATES: LessonTemplate[] = [
  {
    id: 'blank',
    label: 'Blank',
    lessonType: 'article',
    defaultContent: { body: '' },
  },
  {
    id: 'article-with-intro',
    label: 'Article with intro',
    lessonType: 'article',
    defaultContent: {
      body: '<h2>Introduction</h2><p>Write your introduction here.</p><h2>Main content</h2><p>Add your main content here.</p><h2>Key takeaways</h2><ul><li>First takeaway</li><li>Second takeaway</li></ul>',
    },
  },
  {
    id: 'video-with-transcript',
    label: 'Video with transcript',
    lessonType: 'video',
    defaultContent: {
      video_url: '',
      transcript: 'Add your video transcript here.',
    },
  },
  {
    id: 'quiz-3-questions',
    label: 'Quiz (3 seed questions)',
    lessonType: 'quiz',
    defaultContent: { body: '' },
  },
  {
    id: 'lab-standard',
    label: 'Lab',
    lessonType: 'lab',
    defaultContent: {
      body: '<h2>Overview</h2><p>Describe what learners will do in this lab.</p><h2>Instructions</h2><ol><li>Step one</li><li>Step two</li><li>Step three</li></ol>',
      instructions: '',
      starter_code: '',
      solution: '',
    },
  },
]
