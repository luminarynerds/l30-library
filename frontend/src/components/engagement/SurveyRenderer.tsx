/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import type {
  ChoiceOption,
  LikertOptions,
  ScenarioOptions,
  Survey,
  SurveyAnswer,
  SurveyQuestion,
  SurveyResponseResult,
} from '@/api/domains/engagement'
import { SurveyOutcomeDisplay } from './SurveyOutcomeDisplay'

interface Props {
  survey: Survey
  onSubmit: (answers: SurveyAnswer[]) => Promise<SurveyResponseResult>
  onComplete?: (result: SurveyResponseResult) => void
}

export function SurveyRenderer({ survey, onSubmit, onComplete }: Props) {
  const [answers, setAnswers] = useState<Record<number, unknown>>({})
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<SurveyResponseResult | null>(null)

  const sortedQuestions = useMemo(
    () => [...survey.questions].sort((a, b) => a.sort_order - b.sort_order),
    [survey.questions],
  )

  const setAnswer = (questionId: number, value: unknown) =>
    setAnswers((prev) => ({ ...prev, [questionId]: value }))

  const validate = (): string | null => {
    for (const q of sortedQuestions) {
      if (q.is_optional || q.is_demographic) continue
      const v = answers[q.id]
      if (v === undefined || v === null || v === '' ||
          (Array.isArray(v) && v.length === 0)) {
        return `Please answer: ${q.question_text}`
      }
    }
    return null
  }

  const handleSubmit = async () => {
    const err = validate()
    if (err) {
      toast.error(err)
      return
    }
    setSubmitting(true)
    try {
      const payload: SurveyAnswer[] = sortedQuestions
        .filter((q) => answers[q.id] !== undefined)
        .map((q) => ({ question_id: q.id, value: answers[q.id] }))
      const submitted = await onSubmit(payload)
      setResult(submitted)
      onComplete?.(submitted)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Submission failed'
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    return <SurveyOutcomeDisplay survey={survey} result={result} />
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden border border-lsc-border dark:border-earth-700">
      <div className="p-6 md:p-8 space-y-6">
        <header>
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {survey.title}
          </h2>
          {survey.description && (
            <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">
              {survey.description}
            </p>
          )}
          {survey.estimated_minutes && (
            <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              About {survey.estimated_minutes} minute
              {survey.estimated_minutes === 1 ? '' : 's'}
            </p>
          )}
        </header>

        <ol className="space-y-6">
          {sortedQuestions.map((q, idx) => (
            <li key={q.id}>
              <QuestionView
                question={q}
                index={idx + 1}
                value={answers[q.id]}
                onChange={(v) => setAnswer(q.id, v)}
              />
            </li>
          ))}
        </ol>

        <div className="flex justify-end pt-4 border-t border-lsc-border dark:border-earth-700">
          <button
            type="button"
            disabled={submitting}
            onClick={handleSubmit}
            className="px-5 py-2 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-lsc-white font-medium disabled:opacity-50"
          >
            {submitting ? (
              <span className="inline-flex items-center gap-2">
                <span className="motion-safe:animate-spin h-4 w-4 border-2 border-lsc-white/40 border-t-lsc-white rounded-full" />
                Submitting…
              </span>
            ) : (
              'Submit'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// ============ per-question views ============

interface QViewProps {
  question: SurveyQuestion
  index: number
  value: unknown
  onChange: (v: unknown) => void
}

function QuestionView({ question, index, value, onChange }: QViewProps) {
  const required = !question.is_optional && !question.is_demographic
  return (
    <div>
      <div className="flex gap-2 items-start">
        <span className="text-lsc-dark/60 dark:text-lsc-cream/60 font-mono text-sm pt-0.5">
          {index}.
        </span>
        <div className="flex-1 space-y-3">
          <p className="text-lsc-dark dark:text-lsc-cream">
            {question.question_text}
            {!required && (
              <span className="ml-2 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                (optional)
              </span>
            )}
          </p>
          <QuestionInput question={question} value={value} onChange={onChange} />
        </div>
      </div>
    </div>
  )
}

function QuestionInput({ question, value, onChange }: Omit<QViewProps, 'index'>) {
  switch (question.question_type) {
    case 'likert':
      return (
        <LikertView
          options={(question.options || { min: 1, max: 10 }) as LikertOptions}
          value={value as number | undefined}
          onChange={(v) => onChange(v)}
        />
      )
    case 'single_choice':
      return (
        <SingleChoiceView
          options={(question.options || []) as ChoiceOption[]}
          value={value as string | undefined}
          onChange={(v) => onChange(v)}
        />
      )
    case 'multi_choice':
      return (
        <MultiChoiceView
          options={(question.options || []) as ChoiceOption[]}
          value={(value as string[]) || []}
          onChange={(v) => onChange(v)}
        />
      )
    case 'free_text':
      return (
        <FreeTextView
          maxLength={
            (question.options as { max_length?: number } | null)?.max_length
          }
          value={(value as string) || ''}
          onChange={(v) => onChange(v)}
        />
      )
    case 'scenario':
      return (
        <ScenarioView
          options={question.options as ScenarioOptions}
          value={(value as string[]) || []}
          onChange={(v) => onChange(v)}
        />
      )
    default:
      return (
        <p className="text-lsc-dark/60 dark:text-lsc-cream/60 italic">
          Unsupported question type: {question.question_type}
        </p>
      )
  }
}

function LikertView({
  options,
  value,
  onChange,
}: {
  options: LikertOptions
  value: number | undefined
  onChange: (v: number) => void
}) {
  const min = options.min ?? 1
  const max = options.max ?? 10
  const ticks = Array.from({ length: max - min + 1 }, (_, i) => min + i)
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
        <span>{options.min_label || `${min}`}</span>
        <span>{options.max_label || `${max}`}</span>
      </div>
      <div role="radiogroup" className="flex flex-wrap gap-2">
        {ticks.map((n) => {
          const selected = value === n
          return (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(n)}
              className={`min-w-10 h-10 px-2 rounded-lg border focus:ring-2 focus:ring-lsc-rose focus:border-transparent ${
                selected
                  ? 'bg-lsc-rose text-lsc-white border-lsc-rose'
                  : 'bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-700 hover:bg-lsc-cream dark:hover:bg-earth-700'
              }`}
            >
              {n}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function SingleChoiceView({
  options,
  value,
  onChange,
}: {
  options: ChoiceOption[]
  value: string | undefined
  onChange: (v: string) => void
}) {
  return (
    <div role="radiogroup" className="space-y-2">
      {options.map((opt) => {
        const selected = value === opt.value
        return (
          <label
            key={opt.value}
            className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer ${
              selected
                ? 'bg-lsc-rose/10 border-lsc-rose'
                : 'bg-lsc-white dark:bg-earth-900 border-lsc-border dark:border-earth-700 hover:bg-lsc-cream dark:hover:bg-earth-700'
            }`}
          >
            <input
              type="radio"
              className="mt-1 accent-lsc-rose"
              checked={selected}
              onChange={() => onChange(opt.value)}
            />
            <span className="text-lsc-dark dark:text-lsc-cream">
              {opt.text}
            </span>
          </label>
        )
      })}
    </div>
  )
}

function MultiChoiceView({
  options,
  value,
  onChange,
}: {
  options: ChoiceOption[]
  value: string[]
  onChange: (v: string[]) => void
}) {
  const toggle = (v: string) => {
    onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v])
  }
  return (
    <div className="space-y-2">
      {options.map((opt) => {
        const selected = value.includes(opt.value)
        return (
          <label
            key={opt.value}
            className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer ${
              selected
                ? 'bg-lsc-rose/10 border-lsc-rose'
                : 'bg-lsc-white dark:bg-earth-900 border-lsc-border dark:border-earth-700 hover:bg-lsc-cream dark:hover:bg-earth-700'
            }`}
          >
            <input
              type="checkbox"
              className="mt-1 accent-lsc-rose"
              checked={selected}
              onChange={() => toggle(opt.value)}
            />
            <span className="text-lsc-dark dark:text-lsc-cream">
              {opt.text}
            </span>
          </label>
        )
      })}
    </div>
  )
}

function FreeTextView({
  maxLength,
  value,
  onChange,
}: {
  maxLength?: number
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div>
      <textarea
        value={value}
        maxLength={maxLength}
        onChange={(e) => onChange(e.target.value)}
        rows={4}
        className="w-full px-3 py-2 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
      />
      {maxLength && (
        <p className="mt-1 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
          {value.length}/{maxLength}
        </p>
      )}
    </div>
  )
}

function ScenarioView({
  options,
  value,
  onChange,
}: {
  options: ScenarioOptions
  value: string[]
  onChange: (v: string[]) => void
}) {
  // Render the AI artifact as a quoted block, then a multi-select of bias
  // flags the user might identify. flag_choices is staff-authored; falls back
  // to expected_flags rendered as plain values.
  const choices: { value: string; text: string }[] =
    options?.flag_choices ||
    (options?.expected_flags || []).map((f) => ({ value: f, text: f }))
  const toggle = (v: string) => {
    onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v])
  }
  return (
    <div className="space-y-3">
      <blockquote className="p-4 rounded-lg bg-lsc-cream dark:bg-earth-900 border-l-4 border-lsc-rose text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">
        {options?.artifact || ''}
      </blockquote>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        Select every issue you see. There may be more than one.
      </p>
      <div className="space-y-2">
        {choices.map((opt) => {
          const selected = value.includes(opt.value)
          return (
            <label
              key={opt.value}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer ${
                selected
                  ? 'bg-lsc-rose/10 border-lsc-rose'
                  : 'bg-lsc-white dark:bg-earth-900 border-lsc-border dark:border-earth-700 hover:bg-lsc-cream dark:hover:bg-earth-700'
              }`}
            >
              <input
                type="checkbox"
                className="mt-1 accent-lsc-rose"
                checked={selected}
                onChange={() => toggle(opt.value)}
              />
              <span className="text-lsc-dark dark:text-lsc-cream">
                {opt.text}
              </span>
            </label>
          )
        })}
      </div>
    </div>
  )
}
