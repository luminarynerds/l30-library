/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CheckCircle } from 'lucide-react'
import type { QuizQuestion, QuizResult } from '../lesson-types'

interface Props {
  questions: QuizQuestion[]
  answers: Record<number, number>
  submitted: boolean
  result: QuizResult | null
  onAnswer: (questionId: number, optionIndex: number) => void
  onSubmit: () => void
  onRetry: () => void
}

export function LessonQuiz({
  questions,
  answers,
  submitted,
  result,
  onAnswer,
  onSubmit,
  onRetry,
}: Props) {
  return (
    <div className="p-6 md:p-8">
      <div className="space-y-8">
        {questions.map((question, qIndex) => (
          <QuizQuestionRow
            key={question.id}
            question={question}
            index={qIndex}
            selected={answers[question.id]}
            submitted={submitted}
            result={result}
            onAnswer={onAnswer}
          />
        ))}
      </div>

      <div className="mt-8" role="region" aria-live="polite" aria-atomic="true">
        {!submitted ? (
          <button
            onClick={onSubmit}
            disabled={Object.keys(answers).length < questions.length}
            className="w-full md:w-auto bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-400 text-white px-8 py-3 rounded-xl font-medium transition-colors"
          >
            Submit Answers
          </button>
        ) : (
          result && <QuizResultPanel result={result} onRetry={onRetry} />
        )}
      </div>
    </div>
  )
}

interface RowProps {
  question: QuizQuestion
  index: number
  selected: number | undefined
  submitted: boolean
  result: QuizResult | null
  onAnswer: (questionId: number, optionIndex: number) => void
}

function QuizQuestionRow({ question, index, selected, submitted, result, onAnswer }: RowProps) {
  const feedback = result?.feedback?.find(f => f.question_id === question.id)

  return (
    <div className="border-b border-lsc-border dark:border-earth-700 pb-6 last:border-0">
      <p className="font-medium text-lsc-dark dark:text-lsc-cream mb-4">
        {index + 1}. {question.question_text}
      </p>
      <div className="space-y-2">
        {question.options.map((option, oIndex) => {
          const isSelected = selected === oIndex
          const showCorrect = submitted && option.is_correct
          const showWrong = submitted && isSelected && !option.is_correct

          return (
            <button
              key={oIndex}
              onClick={() => onAnswer(question.id, oIndex)}
              disabled={submitted}
              className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-colors ${
                showCorrect
                  ? 'border-status-success-500 bg-status-success-50 dark:bg-status-success-900/20'
                  : showWrong
                  ? 'border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20'
                  : isSelected
                  ? 'border-earth-500 bg-lsc-cream dark:bg-earth-800/20'
                  : 'border-lsc-border dark:border-earth-700 hover:border-lsc-border dark:hover:border-earth-500'
              }`}
            >
              <span className="flex items-center gap-3">
                <span
                  className={`w-6 h-6 rounded-full border-2 flex items-center justify-center text-sm ${
                    isSelected
                      ? 'border-lsc-rose bg-lsc-rose text-white'
                      : 'border-lsc-border dark:border-earth-700'
                  }`}
                >
                  {String.fromCharCode(65 + oIndex)}
                </span>
                <span className="text-lsc-dark dark:text-earth-300">{option.text}</span>
                {showCorrect && (
                  <CheckCircle
                    aria-hidden="true"
                    className="w-5 h-5 text-status-success-500 dark:text-status-success-400 ml-auto"
                  />
                )}
              </span>
            </button>
          )
        })}
      </div>
      {submitted && feedback && question.explanation && (
        <div className="mt-3 p-3 bg-status-info-50 dark:bg-status-info-900/20 rounded-xl text-sm text-status-info-700 dark:text-status-info-300">
          <strong>Explanation:</strong> {question.explanation}
        </div>
      )}
    </div>
  )
}

function QuizResultPanel({ result, onRetry }: { result: QuizResult; onRetry: () => void }) {
  return (
    <div
      className={`p-4 rounded-xl ${
        result.passed ? 'bg-status-success-50 dark:bg-status-success-900/20' : 'bg-lsc-cream dark:bg-lsc-dark/20'
      }`}
    >
      <p
        className={`font-medium ${
          result.passed
            ? 'text-status-success-700 dark:text-status-success-300'
            : 'text-lsc-rose dark:text-lsc-rose-light'
        }`}
      >
        {result.passed ? 'Congratulations! You passed!' : 'Keep practicing!'}
      </p>
      <p className="text-sm mt-1 text-lsc-dark/70 dark:text-lsc-cream/70">
        Score: {result.score}/{result.total_questions} ({result.percentage}%)
      </p>
      {!result.passed && (
        <button
          onClick={onRetry}
          className="mt-3 text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
        >
          Try Again
        </button>
      )}
    </div>
  )
}
