/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for QuizPlayer component
 *
 * Tests for:
 * - Rapid submit race condition fix (answers captured via ref)
 * - Quiz flow (start, answer, submit)
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render } from "@testing-library/react"
import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QuizPlayer } from "../../components/training/QuizPlayer"

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock token store
vi.mock("../../utils/tokenStore", () => ({
  getAccessToken: vi.fn(() => "test-token"),
}))

// Mock quiz data
const mockQuestions = [
  {
    id: 1,
    question_text: "What is 2 + 2?",
    question_type: "multiple_choice",
    options: [
      { text: "3" },
      { text: "4" },
      { text: "5" },
    ],
    sort_order: 1,
  },
  {
    id: 2,
    question_text: "Is the sky blue?",
    question_type: "true_false",
    options: [
      { text: "True" },
      { text: "False" },
    ],
    sort_order: 2,
  },
]

const mockQuizStartResponse = {
  attempt_id: 1,
  questions: mockQuestions,
  total_questions: 2,
  passing_score: 70,
}

const mockQuizResult = {
  attempt_id: 1,
  score: 2,
  total_questions: 2,
  percentage: 100,
  passed: true,
  feedback: [
    {
      question_id: 1,
      correct: true,
      correct_option_index: 1,
      explanation: "2 + 2 equals 4",
      selected_option_index: 1,
    },
    {
      question_id: 2,
      correct: true,
      correct_option_index: 0,
      explanation: "The sky appears blue due to light scattering",
      selected_option_index: 0,
    },
  ],
  xp_earned: 50,
}

describe("QuizPlayer", () => {
  const mockOnBack = vi.fn()
  const mockOnComplete = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()

    // Default mock for loading previous attempts (empty)
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/quiz/attempts")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([]),
        })
      }
      if (url.includes("/quiz/start")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockQuizStartResponse),
        })
      }
      if (url.includes("/quiz/submit")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockQuizResult),
        })
      }
      return Promise.reject(new Error("Unknown endpoint"))
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe("Quiz Flow", () => {
    it("should render loading state initially", async () => {
      render(
        <QuizPlayer
          lessonId={1}
          lessonTitle="Test Lesson"
          onBack={mockOnBack}
          onComplete={mockOnComplete}
        />
      )

      expect(screen.getByText(/loading quiz/i)).toBeInTheDocument()
    })

    it("should show ready state with start button", async () => {
      render(
        <QuizPlayer
          lessonId={1}
          lessonTitle="Test Lesson"
          onBack={mockOnBack}
          onComplete={mockOnComplete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/start quiz/i)).toBeInTheDocument()
      })
    })

    it("should start quiz and show first question", async () => {
      const user = userEvent.setup()

      render(
        <QuizPlayer
          lessonId={1}
          lessonTitle="Test Lesson"
          onBack={mockOnBack}
          onComplete={mockOnComplete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/start quiz/i)).toBeInTheDocument()
      })

      await user.click(screen.getByText(/start quiz/i))

      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument()
      })
    })
  })

  describe("Answer Selection", () => {
    it("should allow selecting an answer", async () => {
      const user = userEvent.setup()

      render(
        <QuizPlayer
          lessonId={1}
          lessonTitle="Test Lesson"
          onBack={mockOnBack}
          onComplete={mockOnComplete}
        />
      )

      // Wait for ready state and start quiz
      await waitFor(() => {
        expect(screen.getByText(/start quiz/i)).toBeInTheDocument()
      })

      await user.click(screen.getByText(/start quiz/i))

      // Wait for question
      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument()
      })

      // Select answer "4"
      const answerButton = screen.getByText("4")
      await user.click(answerButton)

      // Next button should be enabled after selection
      const nextButton = screen.getByRole("button", { name: /next/i })
      expect(nextButton).not.toBeDisabled()
    })

    it("should navigate between questions", async () => {
      const user = userEvent.setup()

      render(
        <QuizPlayer
          lessonId={1}
          lessonTitle="Test Lesson"
          onBack={mockOnBack}
          onComplete={mockOnComplete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/start quiz/i)).toBeInTheDocument()
      })

      await user.click(screen.getByText(/start quiz/i))

      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument()
      })

      // Select answer
      await user.click(screen.getByText("4"))

      // Go to next question
      await user.click(screen.getByRole("button", { name: /next/i }))

      await waitFor(() => {
        expect(screen.getByText("Is the sky blue?")).toBeInTheDocument()
      })
    })
  })

  describe("Race Condition Fix - Rapid Submit", () => {
    it("should capture answers correctly on rapid submit", async () => {
      const user = userEvent.setup()
      let capturedAnswers: unknown[] = []

      // Track the submit call to capture answers
      mockFetch.mockImplementation((url: string, options?: RequestInit) => {
        if (url.includes("/quiz/attempts")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve([]),
          })
        }
        if (url.includes("/quiz/start")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockQuizStartResponse),
          })
        }
        if (url.includes("/quiz/submit")) {
          const body = options?.body
          if (body) {
            capturedAnswers = JSON.parse(body as string).answers
          }
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockQuizResult),
          })
        }
        return Promise.reject(new Error("Unknown endpoint"))
      })

      render(
        <QuizPlayer
          lessonId={1}
          lessonTitle="Test Lesson"
          onBack={mockOnBack}
          onComplete={mockOnComplete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/start quiz/i)).toBeInTheDocument()
      })

      await user.click(screen.getByText(/start quiz/i))

      // Wait for first question
      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument()
      })

      // Answer first question (select "4" which is index 1)
      await user.click(screen.getByText("4"))

      // Navigate to second question
      await user.click(screen.getByRole("button", { name: /next/i }))

      await waitFor(() => {
        expect(screen.getByText("Is the sky blue?")).toBeInTheDocument()
      })

      // Answer second question (select "True" which is index 0)
      await user.click(screen.getByText("True"))

      // Submit quiz
      await user.click(screen.getByRole("button", { name: /submit quiz/i }))

      // Wait for submission
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining("/quiz/submit"),
          expect.objectContaining({ method: "POST" })
        )
      })

      // Verify both answers were captured correctly
      // This tests the race condition fix where answers are captured via ref
      expect(capturedAnswers).toHaveLength(2)
      expect(capturedAnswers).toContainEqual({ question_id: 1, selected_option_index: 1 })
      expect(capturedAnswers).toContainEqual({ question_id: 2, selected_option_index: 0 })
    })

    it("should prevent double submission", async () => {
      const user = userEvent.setup()
      let submitCount = 0

      mockFetch.mockImplementation((url: string) => {
        if (url.includes("/quiz/attempts")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve([]),
          })
        }
        if (url.includes("/quiz/start")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockQuizStartResponse),
          })
        }
        if (url.includes("/quiz/submit")) {
          submitCount++
          // Simulate slow network
          return new Promise(resolve =>
            setTimeout(() => resolve({
              ok: true,
              json: () => Promise.resolve(mockQuizResult),
            }), 500)
          )
        }
        return Promise.reject(new Error("Unknown endpoint"))
      })

      render(
        <QuizPlayer
          lessonId={1}
          lessonTitle="Test Lesson"
          onBack={mockOnBack}
          onComplete={mockOnComplete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/start quiz/i)).toBeInTheDocument()
      })

      await user.click(screen.getByText(/start quiz/i))

      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument()
      })

      // Answer both questions
      await user.click(screen.getByText("4"))
      await user.click(screen.getByRole("button", { name: /next/i }))

      await waitFor(() => {
        expect(screen.getByText("Is the sky blue?")).toBeInTheDocument()
      })

      await user.click(screen.getByText("True"))

      // Rapidly click submit multiple times
      const submitButton = screen.getByRole("button", { name: /submit quiz/i })
      await user.click(submitButton)
      await user.click(submitButton)
      await user.click(submitButton)

      // Wait for completion
      await waitFor(() => {
        expect(screen.getByText(/congratulations/i)).toBeInTheDocument()
      }, { timeout: 3000 })

      // Should only have submitted once
      expect(submitCount).toBe(1)
    })
  })

  describe("Error Handling", () => {
    it("should show error when quiz start fails", async () => {
      const user = userEvent.setup()

      mockFetch.mockImplementation((url: string) => {
        if (url.includes("/quiz/attempts")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve([]),
          })
        }
        if (url.includes("/quiz/start")) {
          return Promise.resolve({
            ok: false,
            json: () => Promise.resolve({ detail: "Quiz not available" }),
          })
        }
        return Promise.reject(new Error("Unknown endpoint"))
      })

      render(
        <QuizPlayer
          lessonId={1}
          lessonTitle="Test Lesson"
          onBack={mockOnBack}
          onComplete={mockOnComplete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/start quiz/i)).toBeInTheDocument()
      })

      await user.click(screen.getByText(/start quiz/i))

      await waitFor(() => {
        expect(screen.getByText(/quiz not available/i)).toBeInTheDocument()
      })
    })

    it("should handle submit failure and not show results", async () => {
      const user = userEvent.setup()

      mockFetch.mockImplementation((url: string) => {
        if (url.includes("/quiz/attempts")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve([]),
          })
        }
        if (url.includes("/quiz/start")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockQuizStartResponse),
          })
        }
        if (url.includes("/quiz/submit")) {
          return Promise.resolve({
            ok: false,
            json: () => Promise.resolve({ detail: "Submission failed" }),
          })
        }
        return Promise.reject(new Error("Unknown endpoint"))
      })

      render(
        <QuizPlayer
          lessonId={1}
          lessonTitle="Test Lesson"
          onBack={mockOnBack}
          onComplete={mockOnComplete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/start quiz/i)).toBeInTheDocument()
      })

      await user.click(screen.getByText(/start quiz/i))

      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument()
      })

      // Answer questions
      await user.click(screen.getByText("4"))
      await user.click(screen.getByRole("button", { name: /next/i }))

      await waitFor(() => {
        expect(screen.getByText("Is the sky blue?")).toBeInTheDocument()
      })

      await user.click(screen.getByText("True"))

      // Submit
      await user.click(screen.getByRole("button", { name: /submit quiz/i }))

      // Wait for isSubmitting to be reset (indicating the request completed)
      await waitFor(() => {
        // Should still be on the quiz page (not showing results)
        expect(screen.getByText("Is the sky blue?")).toBeInTheDocument()
      })

      // onComplete should NOT have been called
      expect(mockOnComplete).not.toHaveBeenCalled()

      // Submit button should be enabled again after failure
      await waitFor(() => {
        const submitButton = screen.getByRole("button", { name: /submit quiz/i })
        expect(submitButton).not.toBeDisabled()
      })
    })
  })

  describe("Completion Callback", () => {
    it("should call onComplete when quiz is passed", async () => {
      const user = userEvent.setup()

      render(
        <QuizPlayer
          lessonId={1}
          lessonTitle="Test Lesson"
          onBack={mockOnBack}
          onComplete={mockOnComplete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/start quiz/i)).toBeInTheDocument()
      })

      await user.click(screen.getByText(/start quiz/i))

      await waitFor(() => {
        expect(screen.getByText("What is 2 + 2?")).toBeInTheDocument()
      })

      // Complete quiz
      await user.click(screen.getByText("4"))
      await user.click(screen.getByRole("button", { name: /next/i }))

      await waitFor(() => {
        expect(screen.getByText("Is the sky blue?")).toBeInTheDocument()
      })

      await user.click(screen.getByText("True"))
      await user.click(screen.getByRole("button", { name: /submit quiz/i }))

      await waitFor(() => {
        expect(screen.getByText(/congratulations/i)).toBeInTheDocument()
      })

      expect(mockOnComplete).toHaveBeenCalled()
    })
  })

  describe("Back Navigation", () => {
    it("should call onBack when back button is clicked", async () => {
      const user = userEvent.setup()

      render(
        <QuizPlayer
          lessonId={1}
          lessonTitle="Test Lesson"
          onBack={mockOnBack}
          onComplete={mockOnComplete}
        />
      )

      await waitFor(() => {
        expect(screen.getByText(/back to lesson/i)).toBeInTheDocument()
      })

      await user.click(screen.getByText(/back to lesson/i))

      expect(mockOnBack).toHaveBeenCalled()
    })
  })
})
