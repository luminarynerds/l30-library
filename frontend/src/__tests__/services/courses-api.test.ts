/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Courses API Service Tests
 *
 * Tests for admin course management API functions including:
 * - Course CRUD operations
 * - Module management
 * - Lesson management
 * - Content reordering
 * - Publishing workflows
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as tokenStore from '@/utils/tokenStore'

// Import the API functions to test
import {
  getCourses,
  getAllCoursesAdmin,
  getCourse,
  createCourse,
  updateCourse,
  deleteCourse,
  transitionCourseStage,
  createModule,
  updateModule,
  deleteModule,
  reorderModules,
  getLesson,
  createLesson,
  updateLesson,
  deleteLesson,
  reorderLessons,
  createQuizQuestion,
  updateQuizQuestion,
  deleteQuizQuestion,
  createLessonResource,
  deleteLessonResource,
  importCourse,
  importCoursesFromJson,
} from '@/api/courses-api'

// Mock tokenStore
vi.mock('@/utils/tokenStore', () => ({
  getAccessToken: vi.fn(),
}))

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('Courses API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // Helper to create mock Response
  const mockResponse = (data: unknown, status = 200) => ({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
  })

  const mockErrorResponse = (detail: string, status = 400) => ({
    ok: false,
    status,
    json: () => Promise.resolve({ detail }),
  })

  // ==================== Course CRUD Tests ====================

  describe('getCourses', () => {
    it('should fetch courses successfully', async () => {
      const mockCourses = [
        {
          id: 1,
          title: 'Course 1',
          description: 'Description 1',
          is_published: true,
          access_level: 'patron',
          difficulty: 'beginner',
          module_count: 3,
          lesson_count: 10,
        },
        {
          id: 2,
          title: 'Course 2',
          description: 'Description 2',
          is_published: true,
          access_level: 'staff',
          difficulty: 'intermediate',
          module_count: 5,
          lesson_count: 15,
        },
      ]
      mockFetch.mockResolvedValue(mockResponse(mockCourses))

      const result = await getCourses()

      expect(result).toEqual(mockCourses)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/courses'),
        expect.any(Object)
      )
    })

    it('should support access_level filter', async () => {
      mockFetch.mockResolvedValue(mockResponse([]))

      await getCourses({ access_level: 'staff' })

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('access_level=staff'),
        expect.any(Object)
      )
    })


    it('should throw error on failure', async () => {
      mockFetch.mockResolvedValue(mockErrorResponse('Server error', 500))

      await expect(getCourses()).rejects.toThrow()
    })
  })

  describe('getAllCoursesAdmin', () => {
    it('should fetch all courses including unpublished', async () => {
      const mockCourses = [
        { id: 1, title: 'Published Course', is_published: true },
        { id: 2, title: 'Draft Course', is_published: false },
      ]
      mockFetch.mockResolvedValue(mockResponse(mockCourses))

      const result = await getAllCoursesAdmin()

      expect(result).toEqual(mockCourses)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/admin/courses'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      )
    })

    it('should include auth token', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('admin-token')
      mockFetch.mockResolvedValue(mockResponse([]))

      await getAllCoursesAdmin()

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer admin-token',
          }),
        })
      )
    })
  })

  describe('getCourse', () => {
    it('should fetch course with modules and lessons', async () => {
      const mockCourse = {
        id: 1,
        title: 'Test Course',
        description: 'A test course',
        is_published: true,
        modules: [
          {
            id: 1,
            title: 'Module 1',
            sort_order: 0,
            lessons: [
              { id: 1, title: 'Lesson 1', lesson_type: 'article', sort_order: 0 },
            ],
          },
        ],
      }
      mockFetch.mockResolvedValue(mockResponse(mockCourse))

      const result = await getCourse(1)

      expect(result).toEqual(mockCourse)
      expect(result.modules).toHaveLength(1)
      expect(result.modules[0]!.lessons).toHaveLength(1)
    })

    it('should throw error for non-existent course', async () => {
      mockFetch.mockResolvedValue(mockErrorResponse('Course not found', 404))

      await expect(getCourse(999)).rejects.toThrow('Course not found')
    })
  })

  describe('createCourse', () => {
    it('should create course successfully', async () => {
      const newCourse = {
        title: 'New Course',
        description: 'A new course',
        access_level: 'patron' as const,
        difficulty: 'beginner' as const,
        estimated_minutes: 60,
      }
      const mockCreatedCourse = {
        id: 1,
        ...newCourse,
        is_published: false,
        created_at: '2024-01-01T00:00:00Z',
      }
      mockFetch.mockResolvedValue(mockResponse(mockCreatedCourse, 201))

      const result = await createCourse(newCourse)

      expect(result).toEqual(mockCreatedCourse)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/courses'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newCourse),
        })
      )
    })

    it('should require authentication', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue('admin-token')
      mockFetch.mockResolvedValue(mockResponse({ id: 1 }, 201))

      await createCourse({ title: 'Test', description: 'Test' })

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer admin-token',
          }),
        })
      )
    })

    it('should throw error when creation fails', async () => {
      mockFetch.mockResolvedValue(mockErrorResponse('Only admins can create courses', 403))

      await expect(createCourse({ title: 'Test' })).rejects.toThrow(
        'Only admins can create courses'
      )
    })
  })

  describe('updateCourse', () => {
    it('should update course successfully', async () => {
      const updateData = {
        title: 'Updated Title',
        description: 'Updated description',
      }
      const mockUpdatedCourse = {
        id: 1,
        ...updateData,
        is_published: false,
      }
      mockFetch.mockResolvedValue(mockResponse(mockUpdatedCourse))

      const result = await updateCourse(1, updateData)

      expect(result).toEqual(mockUpdatedCourse)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/courses/1'),
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify(updateData),
        })
      )
    })

    it('should support partial updates', async () => {
      mockFetch.mockResolvedValue(mockResponse({ id: 1, title: 'New Title' }))

      await updateCourse(1, { title: 'New Title' })

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify({ title: 'New Title' }),
        })
      )
    })

    it('should throw error for non-existent course', async () => {
      mockFetch.mockResolvedValue(mockErrorResponse('Course not found', 404))

      await expect(updateCourse(999, { title: 'Test' })).rejects.toThrow('Course not found')
    })
  })

  describe('deleteCourse', () => {
    it('should delete course successfully', async () => {
      mockFetch.mockResolvedValue({ ok: true, status: 204 })

      await deleteCourse(1)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/courses/1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })

    it('should throw error for non-existent course', async () => {
      mockFetch.mockResolvedValue(mockErrorResponse('Course not found', 404))

      await expect(deleteCourse(999)).rejects.toThrow('Course not found')
    })
  })

  // ==================== Module Management Tests ====================

  describe('createModule', () => {
    it('should create module successfully', async () => {
      const moduleData = {
        course_id: 1,
        title: 'New Module',
        description: 'Module description',
        sort_order: 0,
      }
      const mockCreatedModule = {
        id: 1,
        ...moduleData,
        lessons: [],
      }
      mockFetch.mockResolvedValue(mockResponse(mockCreatedModule, 201))

      const result = await createModule(moduleData)

      expect(result).toEqual(mockCreatedModule)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/courses/1/modules'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(moduleData),
        })
      )
    })

    it('should throw error for non-existent course', async () => {
      mockFetch.mockResolvedValue(mockErrorResponse('Course not found', 404))

      await expect(createModule({ course_id: 999, title: 'Test' })).rejects.toThrow(
        'Course not found'
      )
    })
  })

  describe('updateModule', () => {
    it('should update module successfully', async () => {
      const updateData = {
        title: 'Updated Module Title',
        sort_order: 2,
      }
      mockFetch.mockResolvedValue(mockResponse({ id: 1, ...updateData }))

      const result = await updateModule(1, updateData)

      expect(result.title).toBe('Updated Module Title')
      expect(result.sort_order).toBe(2)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/modules/1'),
        expect.objectContaining({
          method: 'PUT',
        })
      )
    })
  })

  describe('deleteModule', () => {
    it('should delete module successfully', async () => {
      mockFetch.mockResolvedValue({ ok: true, status: 204 })

      await deleteModule(1)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/modules/1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })
  })

  describe('reorderModules', () => {
    it('should reorder modules successfully', async () => {
      mockFetch.mockResolvedValue({ ok: true, status: 204 })

      await reorderModules(1, [3, 1, 2])

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/courses/1/modules/reorder'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ module_ids: [3, 1, 2] }),
        })
      )
    })
  })

  // ==================== Lesson Management Tests ====================

  describe('getLesson', () => {
    it('should fetch lesson with quiz questions', async () => {
      const mockLesson = {
        id: 1,
        title: 'Quiz Lesson',
        lesson_type: 'quiz',
        content: { instructions: 'Answer the questions' },
        quiz_questions: [
          {
            id: 1,
            question_text: 'What is 2+2?',
            options: [
              { text: '3', is_correct: false },
              { text: '4', is_correct: true },
            ],
          },
        ],
      }
      mockFetch.mockResolvedValue(mockResponse(mockLesson))

      const result = await getLesson(1)

      expect(result).toEqual(mockLesson)
      expect(result.quiz_questions).toHaveLength(1)
    })
  })

  describe('createLesson', () => {
    it('should create article lesson successfully', async () => {
      const lessonData = {
        module_id: 1,
        title: 'New Article Lesson',
        lesson_type: 'article' as const,
        content: { text: 'Article content here' },
        estimated_minutes: 10,
        sort_order: 0,
      }
      const mockCreatedLesson = {
        id: 1,
        ...lessonData,
      }
      mockFetch.mockResolvedValue(mockResponse(mockCreatedLesson, 201))

      const result = await createLesson(lessonData)

      expect(result).toEqual(mockCreatedLesson)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/modules/1/lessons'),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })

    it('should create video lesson successfully', async () => {
      const lessonData = {
        module_id: 1,
        title: 'Video Lesson',
        lesson_type: 'video' as const,
        content: { video_url: 'https://example.com/video.mp4' },
        estimated_minutes: 15,
      }
      mockFetch.mockResolvedValue(mockResponse({ id: 1, ...lessonData }, 201))

      const result = await createLesson(lessonData)

      expect(result.lesson_type).toBe('video')
    })

    it('should create quiz lesson successfully', async () => {
      const lessonData = {
        module_id: 1,
        title: 'Quiz Lesson',
        lesson_type: 'quiz' as const,
        content: { instructions: 'Test your knowledge' },
        estimated_minutes: 20,
      }
      mockFetch.mockResolvedValue(mockResponse({ id: 1, ...lessonData }, 201))

      const result = await createLesson(lessonData)

      expect(result.lesson_type).toBe('quiz')
    })
  })

  describe('updateLesson', () => {
    it('should update lesson successfully', async () => {
      const updateData = {
        title: 'Updated Lesson Title',
        content: { text: 'Updated content' },
      }
      mockFetch.mockResolvedValue(mockResponse({ id: 1, ...updateData }))

      const result = await updateLesson(1, updateData)

      expect(result.title).toBe('Updated Lesson Title')
    })

    it('should update lesson sort order for reordering', async () => {
      mockFetch.mockResolvedValue(mockResponse({ id: 1, sort_order: 5 }))

      const result = await updateLesson(1, { sort_order: 5 })

      expect(result.sort_order).toBe(5)
    })

    it('should update lesson accessibility fields', async () => {
      const updateData = {
        sensory_notes: 'Contains flashing images',
        summary: 'Brief summary of the lesson',
      }
      mockFetch.mockResolvedValue(mockResponse({ id: 1, ...updateData }))

      const result = await updateLesson(1, updateData)

      expect(result.sensory_notes).toBe('Contains flashing images')
    })
  })

  describe('deleteLesson', () => {
    it('should delete lesson successfully', async () => {
      mockFetch.mockResolvedValue({ ok: true, status: 204 })

      await deleteLesson(1)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/lessons/1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })
  })

  describe('reorderLessons', () => {
    it('should reorder lessons successfully', async () => {
      mockFetch.mockResolvedValue({ ok: true, status: 204 })

      await reorderLessons(1, [3, 1, 2])

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/modules/1/lessons/reorder'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ lesson_ids: [3, 1, 2] }),
        })
      )
    })
  })

  // ==================== Quiz Questions Tests ====================

  describe('createQuizQuestion', () => {
    it('should create quiz question successfully', async () => {
      const questionData = {
        lesson_id: 1,
        question_text: 'What is the capital of France?',
        question_type: 'multiple_choice',
        options: [
          { text: 'London', is_correct: false },
          { text: 'Paris', is_correct: true },
          { text: 'Berlin', is_correct: false },
        ],
        explanation: 'Paris is the capital city of France.',
        sort_order: 0,
      }
      mockFetch.mockResolvedValue(mockResponse({ id: 1, ...questionData }, 201))

      const result = await createQuizQuestion(questionData)

      expect(result.question_text).toBe('What is the capital of France?')
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/lessons/1/questions'),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })
  })

  describe('updateQuizQuestion', () => {
    it('should update quiz question successfully', async () => {
      const updateData = {
        question_text: 'Updated question?',
        explanation: 'Updated explanation',
      }
      mockFetch.mockResolvedValue(mockResponse({ id: 1, ...updateData }))

      const result = await updateQuizQuestion(1, updateData)

      expect(result.question_text).toBe('Updated question?')
    })
  })

  describe('deleteQuizQuestion', () => {
    it('should delete quiz question successfully', async () => {
      mockFetch.mockResolvedValue({ ok: true, status: 204 })

      await deleteQuizQuestion(1)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/questions/1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })
  })

  // ==================== Lesson Resources Tests ====================

  describe('createLessonResource', () => {
    it('should create lesson resource successfully', async () => {
      const resourceData = {
        lesson_id: 1,
        title: 'Additional Reading',
        description: 'Extra materials for deeper learning',
        resource_type: 'pdf' as const,
        url: 'https://example.com/resource.pdf',
        sort_order: 0,
      }
      mockFetch.mockResolvedValue(mockResponse({ id: 1, ...resourceData }, 201))

      const result = await createLessonResource(resourceData)

      expect(result.title).toBe('Additional Reading')
      expect(result.resource_type).toBe('pdf')
    })
  })

  describe('deleteLessonResource', () => {
    it('should delete lesson resource successfully', async () => {
      mockFetch.mockResolvedValue({ ok: true, status: 204 })

      await deleteLessonResource(1)

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/learning/resources/1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })
  })

  // ==================== Bulk Import Tests ====================

  describe('importCourse', () => {
    it('should import course with modules and lessons', async () => {
      const importData = {
        title: 'Imported Course',
        description: 'Imported via bulk import',
        access_level: 'patron',
        difficulty: 'beginner',
        estimated_minutes: 120,
        modules: [
          {
            title: 'Module 1',
            description: 'First module',
            lessons: [
              {
                title: 'Lesson 1',
                lesson_type: 'article',
                content: { text: 'Content here' },
                estimated_minutes: 10,
              },
            ],
          },
        ],
      }
      const mockImportedCourse = {
        id: 1,
        ...importData,
        is_published: false,
        created_at: '2024-01-01T00:00:00Z',
      }
      mockFetch.mockResolvedValue(mockResponse(mockImportedCourse, 201))

      const result = await importCourse(importData)

      expect(result).toEqual(mockImportedCourse)
    })
  })

  describe('importCoursesFromJson', () => {
    it('should import multiple courses successfully', async () => {
      const courses = [
        {
          title: 'Course 1',
          modules: [{ title: 'Module', lessons: [] }],
        },
        {
          title: 'Course 2',
          modules: [{ title: 'Module', lessons: [] }],
        },
      ]
      const mockResult = {
        imported: 2,
        errors: [],
      }
      mockFetch.mockResolvedValue(mockResponse(mockResult))

      const result = await importCoursesFromJson(courses)

      expect(result.imported).toBe(2)
      expect(result.errors).toHaveLength(0)
    })

    it('should return partial success with errors', async () => {
      const courses = [
        { title: 'Valid Course', modules: [] },
        { title: '', modules: [] }, // Invalid - missing title
      ]
      const mockResult = {
        imported: 1,
        errors: ['Course 2: Title is required'],
      }
      mockFetch.mockResolvedValue(mockResponse(mockResult))

      const result = await importCoursesFromJson(courses)

      expect(result.imported).toBe(1)
      expect(result.errors).toHaveLength(1)
    })
  })

  // ==================== Full Workflow Integration Tests ====================

  describe('Full Course Creation Workflow', () => {
    it('should create a complete course with modules, lessons, and quiz questions', async () => {
      // Step 1: Create course
      const courseData = {
        title: 'Complete Course',
        description: 'Full course with all content',
        access_level: 'patron' as const,
        difficulty: 'beginner' as const,
      }
      mockFetch.mockResolvedValueOnce(mockResponse({ id: 1, ...courseData, is_published: false }, 201))

      const course = await createCourse(courseData)
      expect(course.id).toBe(1)

      // Step 2: Create module
      const moduleData = {
        course_id: 1,
        title: 'Introduction Module',
        sort_order: 0,
      }
      mockFetch.mockResolvedValueOnce(mockResponse({ id: 1, ...moduleData, lessons: [] }, 201))

      const module = await createModule(moduleData)
      expect(module.id).toBe(1)

      // Step 3: Create article lesson
      const articleLessonData = {
        module_id: 1,
        title: 'Welcome Article',
        lesson_type: 'article' as const,
        content: { text: 'Welcome to the course!' },
        estimated_minutes: 5,
        sort_order: 0,
      }
      mockFetch.mockResolvedValueOnce(mockResponse({ id: 1, ...articleLessonData }, 201))

      const articleLesson = await createLesson(articleLessonData)
      expect(articleLesson.lesson_type).toBe('article')

      // Step 4: Create quiz lesson
      const quizLessonData = {
        module_id: 1,
        title: 'Knowledge Check',
        lesson_type: 'quiz' as const,
        content: { instructions: 'Test your understanding' },
        estimated_minutes: 10,
        sort_order: 1,
      }
      mockFetch.mockResolvedValueOnce(mockResponse({ id: 2, ...quizLessonData }, 201))

      const quizLesson = await createLesson(quizLessonData)
      expect(quizLesson.lesson_type).toBe('quiz')

      // Step 5: Add quiz question
      const questionData = {
        lesson_id: 2,
        question_text: 'Did you learn something?',
        options: [
          { text: 'Yes', is_correct: true },
          { text: 'No', is_correct: false },
        ],
      }
      mockFetch.mockResolvedValueOnce(mockResponse({ id: 1, ...questionData }, 201))

      const question = await createQuizQuestion(questionData)
      expect(question.question_text).toBe('Did you learn something?')

      // Step 6: Publish the course via the lifecycle transition endpoint
      // (is_published is no longer a writable field — lifecycle_stage is
      // the source of truth; the API still returns a derived is_published).
      mockFetch.mockResolvedValueOnce(
        mockResponse({ id: 1, lifecycle_stage: 'published', is_published: true })
      )

      const publishedCourse = await transitionCourseStage(1, { to_stage: 'published' })
      expect(publishedCourse.is_published).toBe(true)
      expect(publishedCourse.lifecycle_stage).toBe('published')
    })
  })

  describe('Content Reordering Workflow', () => {
    it('should reorder modules and lessons via sort_order updates', async () => {
      // Reorder modules by updating sort_order
      mockFetch.mockResolvedValueOnce(mockResponse({ id: 3, sort_order: 0 }))
      const movedModule = await updateModule(3, { sort_order: 0 })
      expect(movedModule.sort_order).toBe(0)

      // Reorder lessons by updating sort_order
      mockFetch.mockResolvedValueOnce(mockResponse({ id: 5, sort_order: 1 }))
      const movedLesson = await updateLesson(5, { sort_order: 1 })
      expect(movedLesson.sort_order).toBe(1)
    })
  })

})
