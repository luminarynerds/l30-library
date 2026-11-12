/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { MarkdownContent } from '../MarkdownContent'
import { SandboxPlayer } from '../SandboxPlayer'
import { LessonQuiz } from './LessonQuiz'
import type {
  ArticleContent,
  Lesson,
  QuizResult,
  SandboxContent,
  VideoContent,
} from '../lesson-types'

interface Props {
  lesson: Lesson
  content: ArticleContent | VideoContent | SandboxContent | null
  quizAnswers: Record<number, number>
  quizSubmitted: boolean
  quizResult: QuizResult | null
  onAnswer: (questionId: number, optionIndex: number) => void
  onQuizSubmit: () => void
  onQuizRetry: () => void
  onComplete: () => void
}

export function LessonBody({
  lesson,
  content,
  quizAnswers,
  quizSubmitted,
  quizResult,
  onAnswer,
  onQuizSubmit,
  onQuizRetry,
  onComplete,
}: Props) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
      {lesson.lesson_type === 'article' && <ArticleBody content={content as ArticleContent | null} />}
      {lesson.lesson_type === 'video' && (
        <VideoBody content={content as VideoContent | null} title={lesson.title} />
      )}
      {lesson.lesson_type === 'quiz' && (
        <LessonQuiz
          questions={lesson.quiz_questions}
          answers={quizAnswers}
          submitted={quizSubmitted}
          result={quizResult}
          onAnswer={onAnswer}
          onSubmit={onQuizSubmit}
          onRetry={onQuizRetry}
        />
      )}
      {lesson.lesson_type === 'sandbox' && (
        <SandboxPlayer content={content as SandboxContent | null} onComplete={onComplete} />
      )}
      {lesson.lesson_type === 'lab' && <LabBody content={content as ArticleContent | null} />}
    </div>
  )
}

function ArticleBody({ content }: { content: ArticleContent | null }) {
  return (
    <div className="p-6 md:p-8 prose dark:prose-invert max-w-none">
      {content?.body ? (
        <MarkdownContent content={content.body} />
      ) : content?.text ? (
        <div className="whitespace-pre-wrap">{content.text}</div>
      ) : (
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No content available.</p>
      )}
    </div>
  )
}

function VideoBody({ content, title }: { content: VideoContent | null; title: string }) {
  return (
    <div className="p-6 md:p-8">
      {content?.video_url ? (
        <div className="aspect-video bg-black rounded-xl overflow-hidden">
          <iframe
            src={content.video_url}
            className="w-full h-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            title={`Video: ${title || 'Lesson video'}`}
          />
        </div>
      ) : (
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Video not available.</p>
      )}
      {content?.transcript && (
        <details className="mt-6">
          <summary className="cursor-pointer text-lsc-rose dark:text-lsc-rose-light font-medium">
            View Transcript
          </summary>
          <div className="mt-4 p-4 bg-lsc-cream dark:bg-lsc-dark rounded-xl text-sm whitespace-pre-wrap">
            {content.transcript}
          </div>
        </details>
      )}
    </div>
  )
}

function LabBody({ content }: { content: ArticleContent | null }) {
  return (
    <div className="p-6 md:p-8">
      <div className="mb-4 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose-light/10 text-lsc-rose dark:text-lsc-rose-light text-xs font-semibold uppercase tracking-wide">
        Hands-on Lab
      </div>
      <div className="prose dark:prose-invert max-w-none">
        {content?.body ? (
          <MarkdownContent content={content.body} />
        ) : content?.text ? (
          <div className="whitespace-pre-wrap">{content.text}</div>
        ) : (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No content available.</p>
        )}
      </div>
    </div>
  )
}
