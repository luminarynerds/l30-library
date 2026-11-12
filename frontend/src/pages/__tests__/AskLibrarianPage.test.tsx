/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, beforeEach, vi } from 'vitest'

const getAgentsMock = vi.fn()
const chatWithAgentMock = vi.fn()
const submitAgentFeedbackMock = vi.fn()

vi.mock('../../api/library-agents-api', () => ({
  getAgents: (...args: unknown[]) => getAgentsMock(...args),
  chatWithAgent: (...args: unknown[]) => chatWithAgentMock(...args),
  submitAgentFeedback: (...args: unknown[]) => submitAgentFeedbackMock(...args),
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

// usePageTitle pulls in BrandingContext; it only sets document.title, which is
// irrelevant here. Stub it so the page renders without a BrandingProvider.
vi.mock('@/hooks/usePageTitle', () => ({ usePageTitle: vi.fn() }))

// The page now reads library phone/email from branding for its contact links;
// mock the hook so it renders without a BrandingProvider (same reason as above).
vi.mock('@/contexts/BrandingContext', () => ({
  useBranding: () => ({
    library_name: 'Test Library',
    phone: '555-123-4567',
    contact_email: 'hello@testlibrary.example',
    domain: 'testlibrary.example',
  }),
}))

import AskLibrarianPage from '../AskLibrarianPage'

const agent = {
  id: 7,
  name: 'Ada Reference',
  role: 'Reference Librarian',
  department: 'Adult Services',
  greeting_message: 'Hi, I can help with research.',
  avatar_color: '#0ea5e9',
  initials: 'AR',
  emoji: '',
  specialties: ['Research', 'Genealogy'],
  bio: 'Ada has helped patrons for years.',
  is_active: true,
}

// A second agent, used to prove replyMode doesn't leak across chat sessions
// (see "does not carry an AI claim across sessions when switching agents").
const agentB = {
  id: 8,
  name: 'Priya Reference',
  role: 'Teen Services Librarian',
  department: 'Youth Services',
  greeting_message: 'Hi, I can help with teen stuff.',
  avatar_color: '#3b82f6',
  initials: 'PR',
  emoji: '',
  specialties: ['Homework Help'],
  bio: 'Priya specializes in teen services.',
  is_active: true,
}

// session_id is a UUID — parseInt() of it is NaN. Feedback must target the
// integer conversation_id instead; the assertions below pin that.
const chatResponse = {
  agent_name: agent.name,
  agent_role: agent.role,
  response: 'Here is what I found.',
  session_id: 'b7e2c1a0-4f3d-4c9a-9e1b-2d6f8a0c3e57',
  conversation_id: 4242,
  detected_intent: null,
  suggested_followups: null,
}

// jsdom has no layout, so it doesn't implement scrollIntoView at all. Record
// the elements it's called on so the scroll-into-view test can assert the
// target, and so every other test that opens a chat doesn't throw.
let scrolledInto: { target: Element; options?: ScrollIntoViewOptions | boolean }[] = []

beforeEach(() => {
  vi.clearAllMocks()
  scrolledInto = []
  Element.prototype.scrollIntoView = function (
    this: Element,
    options?: ScrollIntoViewOptions | boolean,
  ) {
    scrolledInto.push({ target: this, options })
  }
  getAgentsMock.mockResolvedValue([agent])
  chatWithAgentMock.mockResolvedValue(chatResponse)
  submitAgentFeedbackMock.mockResolvedValue(undefined)
})

// The agent-selection card leads with the patron's need (specialties), not a
// fictional staff identity — see "Lead with the need" in AskLibrarianPage.tsx.
// For this fixture's specialties, that's the button's accessible name.
const START_CHAT_NAME = /start chat: research, genealogy/i

/** Render the page, open a chat, send one message, and wait for the reply. */
async function openChatAndSendMessage(user: ReturnType<typeof userEvent.setup>) {
  render(<AskLibrarianPage />)
  await waitFor(() => expect(screen.getByText('Research, Genealogy')).toBeInTheDocument())

  await user.click(screen.getByRole('button', { name: START_CHAT_NAME }))
  await waitFor(() =>
    expect(screen.getByText('Hi, I can help with research.')).toBeInTheDocument(),
  )

  await user.type(
    screen.getByLabelText('Message the library assistant'),
    'What books do you have?',
  )
  await user.click(screen.getByRole('button', { name: 'Send message' }))
  await waitFor(() =>
    expect(screen.getByText('Here is what I found.')).toBeInTheDocument(),
  )
}

describe('AskLibrarianPage', () => {
  it('lists the available librarians once loaded', async () => {
    render(<AskLibrarianPage />)
    await waitFor(() => expect(screen.getByText('Research, Genealogy')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: START_CHAT_NAME })).toBeInTheDocument()
    expect(getAgentsMock).toHaveBeenCalled()
  })

  it('opens a chat showing the greeting, with no feedback controls on it', async () => {
    const user = userEvent.setup()
    render(<AskLibrarianPage />)
    await waitFor(() => expect(screen.getByText('Research, Genealogy')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: START_CHAT_NAME }))
    expect(await screen.findByText('Hi, I can help with research.')).toBeInTheDocument()
    // The greeting is local-only (no conversation_id), so it carries no thumbs.
    expect(screen.queryByRole('button', { name: /mark this response/i })).toBeNull()
  })

  // Regression guard for the "page jumps to the bottom" report: opening a chat
  // swaps the tall librarian grid for a much shorter chat card. Window scroll
  // isn't part of React state, so it stayed where the grid was and the patron
  // landed past the card, on the footer. The panel has to pull itself into
  // view, and take focus with it — the button that was focused just unmounted,
  // which otherwise drops keyboard and screen reader users onto <body>.
  it('pulls the chat panel into view and takes focus when a chat opens', async () => {
    const user = userEvent.setup()
    render(<AskLibrarianPage />)
    await waitFor(() => expect(screen.getByText('Research, Genealogy')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: START_CHAT_NAME }))
    await waitFor(() =>
      expect(screen.getByText('Hi, I can help with research.')).toBeInTheDocument(),
    )

    const panel = screen.getByRole('region', { name: 'Chat with the library assistant' })
    const call = scrolledInto.find((c) => c.target === panel)
    expect(call).toBeDefined()
    expect(panel).toHaveFocus()

    // Instant, never smooth. A smooth scroll is rAF-driven and silently does
    // nothing when it can't animate — a backgrounded tab reproduced exactly
    // the original bug on prod, with the panel top left at -264px.
    expect(call?.options).toEqual({ block: 'start' })
  })

  it('submits thumbs-up feedback against the conversation_id, not the session_id', async () => {
    const user = userEvent.setup()
    await openChatAndSendMessage(user)

    await user.click(screen.getByRole('button', { name: 'Mark this response as helpful' }))

    // Regression guard: the earlier bug stored parseInt(session_id) — NaN for a
    // UUID — as the id. Feedback must be sent against the integer conversation_id.
    await waitFor(() =>
      expect(submitAgentFeedbackMock).toHaveBeenCalledWith(4242, true),
    )
    expect(await screen.findByText('Thanks for the feedback')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /mark this response/i })).toBeNull()
  })

  it('submits thumbs-down feedback', async () => {
    const user = userEvent.setup()
    await openChatAndSendMessage(user)

    await user.click(
      screen.getByRole('button', { name: 'Mark this response as not helpful' }),
    )

    await waitFor(() =>
      expect(submitAgentFeedbackMock).toHaveBeenCalledWith(4242, false),
    )
    expect(
      await screen.findByText("Thanks, we'll use this to improve"),
    ).toBeInTheDocument()
  })

  // Regression guard for the cross-session mode leak: replyMode must reset to
  // null both when a new chat starts and when the patron backs out to the
  // librarian list, so a previous agent's 'llm' reply never renders an AI
  // claim on the very first paint of a different agent's chat.
  it('does not carry an AI claim across sessions when switching agents', async () => {
    const user = userEvent.setup()
    getAgentsMock.mockResolvedValue([agent, agentB])
    chatWithAgentMock.mockResolvedValueOnce({ ...chatResponse, mode: 'llm' })

    render(<AskLibrarianPage />)
    await waitFor(() => expect(screen.getByText('Research, Genealogy')).toBeInTheDocument())

    // Chat with agent A and receive a reply the model actually generated.
    await user.click(screen.getByRole('button', { name: START_CHAT_NAME }))
    await waitFor(() =>
      expect(screen.getByText('Hi, I can help with research.')).toBeInTheDocument(),
    )
    await user.type(
      screen.getByLabelText('Message the library assistant'),
      'What books do you have?',
    )
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await waitFor(() => expect(screen.getByText(/AI-generated/i)).toBeInTheDocument())

    // Back out to the librarian list.
    await user.click(screen.getByRole('button', { name: 'Back to librarian list' }))
    await waitFor(() => expect(screen.getByText('Homework Help')).toBeInTheDocument())

    // Start a fresh chat with a different agent. First paint must not assert
    // AI generation — no reply has arrived yet for this session.
    await user.click(screen.getByRole('button', { name: /start chat: homework help/i }))
    await waitFor(() =>
      expect(screen.getByText('Hi, I can help with teen stuff.')).toBeInTheDocument(),
    )
    expect(screen.queryByText(/AI-generated/i)).not.toBeInTheDocument()
  })
})
