/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useState } from "react";
import { Send, Sparkles, Users, ArrowLeft, ThumbsUp, ThumbsDown, Phone, Mail, MapPin } from "lucide-react";
import { getAgents, chatWithAgent, submitAgentFeedback, type LibraryAgent } from "../api/library-agents-api";
import toast from "react-hot-toast";
import { getAgentIcon } from "../utils/icons";
import { getUserMessage } from "../lib/api-client";
import { usePageTitle } from "@/hooks/usePageTitle";
import { useBranding } from "@/contexts/BrandingContext";
import { t } from '@/i18n'

// Using LibraryAgent from API - see library-agents-api.ts

const AGENTS_LOAD_TIMEOUT_MS = 15000;

// The backend usually answers from a rule table in ~50ms, which makes the
// typing indicator flash and the reply feel fake. Hold it for a beat so the
// indicator is actually visible, scaling slightly with reply length but
// capped so a long reply never feels stuck.
const REPLY_REVEAL_MIN_MS = 600;
const REPLY_REVEAL_MAX_MS = 900;
const REPLY_REVEAL_MS_PER_CHAR = 2;

function replyRevealDelayMs(replyText: string): number {
  return Math.min(REPLY_REVEAL_MAX_MS, REPLY_REVEAL_MIN_MS + replyText.length * REPLY_REVEAL_MS_PER_CHAR);
}


// DB-stored avatar_color values are often Tailwind class strings (e.g. "bg-sky-500")
// which won't resolve as CSS colors when used as inline style. Resolve them to
// hex values, and rewrite banned palette entries (purple) to a Nordic token color.
const AVATAR_FALLBACK_HEX = "#6b7f6e"; // sage-600
const AVATAR_HEX_BY_CLASS: Record<string, string> = {
  "bg-green-600": "#16a34a",
  "bg-sky-500": "#0ea5e9",
  "bg-blue-500": "#3b82f6",
  "bg-pink-500": "#ec4899",
  "bg-amber-600": "#d97706",
  "bg-rose-500": "#f43f5e",
  "bg-purple-500": AVATAR_FALLBACK_HEX,
  "bg-purple-600": AVATAR_FALLBACK_HEX,
};
function resolveAvatarColor(raw: string | null | undefined): string {
  if (!raw) return AVATAR_FALLBACK_HEX;
  if (raw in AVATAR_HEX_BY_CLASS) return AVATAR_HEX_BY_CLASS[raw] ?? AVATAR_FALLBACK_HEX;
  if (raw.startsWith("#") || raw.startsWith("rgb") || raw.startsWith("hsl")) return raw;
  return AVATAR_FALLBACK_HEX;
}

interface Message {
  id: string;
  sender: "user" | "agent";
  text: string;
  timestamp: Date;
  conversationId?: number;
  feedbackGiven?: "helpful" | "not-helpful";
}

interface ChatSession {
  agent: LibraryAgent;
  messages: Message[];
  sessionId?: string;
}

// The banner renders before any reply exists, so mode is unknown at first
// paint. Split into an always-true sentence (never claims AI) plus a
// mode-specific sentence appended once known, so no state of this UI --
// including first paint and a mid-conversation model outage -- asserts
// something false.
export function AiDisclosure({ mode }: { mode: 'rule_based' | 'llm' | null }) {
  return (
    <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border-b border-status-warning-200 dark:border-status-warning-800 px-4 py-3">
      <p className="text-xs text-status-warning-800 dark:text-status-warning-200">
        {t('askLibrarian.disclosureAlways', "You're chatting with an automated assistant, not a real person. It can be wrong.")}
        {' '}
        {mode === 'llm'
          ? t('askLibrarian.disclosureLlm', 'Its answers are AI-generated.')
          : mode === 'rule_based'
            ? t('askLibrarian.disclosureRuleBased', 'Right now it answers from a written list of common library questions, not an AI model.')
            : null}
        {' '}
        {t('askLibrarian.disclosureStaff', 'For anything important, call, email, or visit the desk.')}
      </p>
    </div>
  )
}

export default function AskLibrarianPage() {
  usePageTitle(t('navigation.askALibrarian', 'Ask a Librarian'))
  const branding = useBranding();
  const [agents, setAgents] = useState<LibraryAgent[]>([]);
  const [chatSession, setChatSession] = useState<ChatSession | null>(null);
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [agentsError, setAgentsError] = useState<string | null>(null);
  const [replyMode, setReplyMode] = useState<'rule_based' | 'llm' | null>(null);
  // sr-only live region: announces the typing state and the revealed reply
  // once each, decoupled from the visible typing indicator so it doesn't
  // re-announce on unrelated re-renders (e.g. feedback button clicks).
  const [replyStatus, setReplyStatus] = useState("");

  const fetchAgentsData = useCallback(async () => {
    setIsLoadingAgents(true);
    setAgentsError(null);

    try {
      const data = await Promise.race([
        getAgents(),
        new Promise<LibraryAgent[]>((_, reject) =>
          setTimeout(() => reject(new Error("Agents request timed out")), AGENTS_LOAD_TIMEOUT_MS)
        ),
      ]);
      setAgents(data);
    } catch (err) {
      setAgentsError("Unable to load librarians right now");
      toast.error(getUserMessage(err, t('askLibrarian.unableToLoadLibrarians', 'Unable to load librarians right now')));
    } finally {
      setIsLoadingAgents(false);
    }
  }, []);

  useEffect(() => {
    fetchAgentsData();
  }, [fetchAgentsData]);

  const startChat = (agent: LibraryAgent) => {
    // Each new session starts with mode unknown again — a leftover 'llm' from
    // a previous agent's reply must never carry over onto this agent's first
    // paint. See AiDisclosure above.
    setReplyMode(null);
    setReplyStatus("");

    const greeting: Message = {
      id: `greeting-${Date.now()}`,
      sender: "agent",
      text:
        agent.greeting_message ||
        t('askLibrarian.defaultGreeting', { role: agent.role }),
      timestamp: new Date(),
    };

    setChatSession({
      agent,
      messages: [greeting],
    });
  };

  // Opening a chat swaps the tall librarian grid for a much shorter chat card.
  // Window scroll isn't React state, so it stays where the grid was and the
  // patron lands past the card, looking at the footer. Pull the panel back
  // under the sticky header when it mounts, and take focus with it -- the
  // button that was focused just unmounted, which otherwise drops keyboard and
  // screen reader users onto <body>.
  //
  // A stable useCallback ref fires on mount/unmount only. An effect keyed on
  // the session would re-fire on every message and yank the view mid-reply.
  // The scroll is deliberately instant, not smooth. A smooth scroll is
  // rAF-driven, so it silently does nothing whenever it can't animate (a
  // backgrounded tab reproduces this every time) -- and doing nothing is
  // exactly the bug. Instant also matches ScrollToTop, and there is no content
  // worth animating past: the grid it would scroll through just unmounted.
  const chatPanelRef = useCallback((node: HTMLDivElement | null) => {
    if (!node) return;
    node.focus({ preventScroll: true });
    node.scrollIntoView({ block: "start" });
  }, []);

  const sendMessage = async () => {
    if (!inputMessage.trim() || !chatSession) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: inputMessage,
      timestamp: new Date(),
    };

    setChatSession({
      ...chatSession,
      messages: [...chatSession.messages, userMessage],
    });
    setInputMessage("");
    setIsTyping(true);
    setReplyStatus(t('aria.askLibrarian.assistantTyping', 'Library assistant is typing a reply.'));

    try {
      const response = await chatWithAgent(
        chatSession.agent.id,
        inputMessage,
        chatSession.sessionId
      );

      // The backend often answers in ~50ms (rule-table lookup), which makes
      // the typing indicator flash. Hold the reveal for a beat so it's
      // actually visible; the delay is client-side only and never applies to
      // the error path below, so a real failure still surfaces immediately.
      await new Promise((resolve) => setTimeout(resolve, replyRevealDelayMs(response.response)));

      setReplyMode(response.mode);

      const agentMessage: Message = {
        id: `agent-${Date.now()}`,
        sender: "agent",
        text: response.response,
        timestamp: new Date(),
        conversationId: response.conversation_id,
      };

      setChatSession((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          messages: [...prev.messages, agentMessage],
          sessionId: response.session_id,
        };
      });
      setReplyStatus(`${t('aria.askLibrarian.replyPrefix', 'Reply: ')}${response.response}`);
    } catch (err) {
      setReplyStatus("");
      toast.error(getUserMessage(err, t('askLibrarian.failedToSendMessage', 'Failed to send message')));
    } finally {
      setIsTyping(false);
    }
  };

  const handleFeedback = async (
    messageId: string,
    conversationId: number,
    helpful: boolean
  ) => {
    try {
      await submitAgentFeedback(conversationId, helpful);
      setChatSession((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          messages: prev.messages.map((m) =>
            m.id === messageId
              ? { ...m, feedbackGiven: helpful ? "helpful" : "not-helpful" }
              : m
          ),
        };
      });
    } catch {
      /* feedback is nice-to-have — fail quietly */
    }
  };

  return (
    <div className="space-y-8">
      {/* Header — flat warm-neutral, Nordic editorial */}
      <header className="bg-lsc-cream dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl px-8 py-10 text-center">
        <h1 className="text-4xl md:text-5xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('navigation.askALibrarian', 'Ask a Librarian')}
        </h1>
        <p className="mt-3 text-lg text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mx-auto">
          {t('askLibrarian.headerIntro', "Reach a real person at the desk, or chat with our library assistant for recommendations, research help, and everyday library questions.")}
        </p>
      </header>

      <div>
        {chatSession ? (
          // Chat View
          <div
            ref={chatPanelRef}
            tabIndex={-1}
            role="region"
            aria-label={t('aria.askLibrarian.chatPanel', 'Chat with the library assistant')}
            className="max-w-2xl mx-auto scroll-mt-24"
          >
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
              {/* Chat Header */}
              <div className="bg-lsc-rose dark:bg-lsc-rose-dark text-white p-6 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => {
                      setChatSession(null);
                      setReplyMode(null);
                      setReplyStatus("");
                    }}
                    aria-label={t('aria.askLibrarian.backToLibrarianList', 'Back to librarian list')}
                    className="hover:bg-lsc-white/20 dark:hover:bg-earth-800/40 p-2 rounded-lg transition focus:outline-none focus:ring-2 focus:ring-lsc-white"
                  >
                    <ArrowLeft className="h-6 w-6" />
                  </button>
                  <div>
                    <h2 className="font-serif text-xl font-bold">{t('askLibrarian.aiAssistantLabel', 'Library Assistant')}</h2>
                    <p className="text-white/90 text-sm">{chatSession.agent.role}</p>
                  </div>
                </div>
              </div>

              {/* AI Disclosure Banner */}
              <AiDisclosure mode={replyMode} />

              {/* Announces the typing state once, then the revealed reply once —
                  separate from the visible typing indicator below so unrelated
                  re-renders (e.g. thumbs-up clicks) don't re-trigger it. */}
              <div role="status" className="sr-only">{replyStatus}</div>

              {/* Messages */}
              <div className="h-64 sm:h-80 md:h-96 overflow-y-auto p-4 sm:p-6 space-y-4">
                {chatSession.messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.sender === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`flex flex-col ${
                        message.sender === "user" ? "items-end" : "items-start"
                      }`}
                    >
                      <div
                        className={`max-w-[80%] sm:max-w-xs px-4 py-2 rounded-lg ${
                          message.sender === "user"
                            ? "bg-lsc-rose text-white rounded-br-none"
                            : "bg-lsc-border dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-bl-none"
                        }`}
                      >
                        {message.text}
                      </div>
                      {message.sender === "agent" && message.conversationId != null && (
                        message.feedbackGiven ? (
                          <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1 px-1">
                            {message.feedbackGiven === "helpful"
                              ? t('askLibrarian.thanksHelpful', 'Thanks for the feedback')
                              : t('askLibrarian.thanksNotHelpful', "Thanks, we'll use this to improve")}
                          </span>
                        ) : (
                          <div className="flex items-center gap-1 mt-1 px-1">
                            <button
                              type="button"
                              onClick={() => handleFeedback(message.id, message.conversationId!, true)}
                              aria-label={t('aria.askLibrarian.markHelpful', 'Mark this response as helpful')}
                              title={t('askLibrarian.helpfulTooltip', 'Helpful')}
                              className="text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-status-success-600 dark:hover:text-status-success-400 p-1 rounded focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                            >
                              <ThumbsUp className="w-3.5 h-3.5" aria-hidden="true" />
                            </button>
                            <button
                              type="button"
                              onClick={() => handleFeedback(message.id, message.conversationId!, false)}
                              aria-label={t('aria.askLibrarian.markNotHelpful', 'Mark this response as not helpful')}
                              title={t('askLibrarian.notHelpfulTooltip', 'Not helpful')}
                              className="text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-status-danger-600 dark:hover:text-status-danger-400 p-1 rounded focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                            >
                              <ThumbsDown className="w-3.5 h-3.5" aria-hidden="true" />
                            </button>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="bg-lsc-border dark:bg-earth-700 px-4 py-2 rounded-lg rounded-bl-none">
                      <div className="flex items-center gap-2">
                        <div className="flex gap-1.5">
                          <div className="w-2 h-2 bg-lsc-dark dark:bg-lsc-cream rounded-full motion-safe:animate-bounce"></div>
                          <div className="w-2 h-2 bg-lsc-dark dark:bg-lsc-cream rounded-full motion-safe:animate-bounce" style={{ animationDelay: "0.1s" }}></div>
                          <div className="w-2 h-2 bg-lsc-dark dark:bg-lsc-cream rounded-full motion-safe:animate-bounce" style={{ animationDelay: "0.2s" }}></div>
                        </div>
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">{t('askLibrarian.aiThinking', 'is thinking... (usually under 10 seconds)')}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Input */}
              <div className="border-t border-lsc-border dark:border-earth-700 p-4 flex gap-2">
                <label htmlFor="ask-librarian-input" className="sr-only">
                  {t('askLibrarian.messageInputLabel', 'Message the library assistant')}
                </label>
                <input
                  id="ask-librarian-input"
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                  placeholder={t('placeholder.askLibrarian.typeYourMessage')}
                  aria-label={t('askLibrarian.messageInputLabel', 'Message the library assistant')}
                  className="flex-1 px-4 py-2 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  disabled={isTyping}
                />
                <button
                  onClick={sendMessage}
                  disabled={isTyping || !inputMessage.trim()}
                  aria-label={t('aria.askLibrarian.sendMessage', 'Send message')}
                  className="bg-lsc-rose hover:bg-lsc-rose-dark disabled:opacity-50 text-white p-2 rounded-lg transition focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
                >
                  <Send className="h-6 w-6" aria-hidden="true" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          // Agent Selection View
          <div>
            {/* Human path first: a real person is the default, not the AI. */}
            <section
              aria-labelledby="talk-to-a-person-heading"
              className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6 sm:p-8 shadow-sm mb-10"
            >
              <h2
                id="talk-to-a-person-heading"
                className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream"
              >
                {t('askLibrarian.talkToRealPerson', 'Talk to a real person')}
              </h2>
              <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl">
                {t('askLibrarian.talkToRealPersonBody', 'A library worker can help you by phone, email, or in person at the desk. This is the best way to get a real answer.')}
              </p>
              <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
                <a
                  href={`tel:${branding.phone.replace(/\D/g,'')}`}
                  className="flex items-center gap-3 rounded-lg border border-lsc-border dark:border-earth-700 px-4 py-3 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border/30 dark:hover:bg-earth-700 transition focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                >
                  <Phone className="h-5 w-5 text-lsc-rose dark:text-lsc-rose-light shrink-0" aria-hidden="true" />
                  <span className="flex flex-col">
                    <span className="font-semibold">{t('askLibrarian.callUs', 'Call us')}</span>
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{branding.phone}</span>
                  </span>
                </a>
                <a
                  href={`mailto:${branding.contact_email}`}
                  className="flex items-center gap-3 rounded-lg border border-lsc-border dark:border-earth-700 px-4 py-3 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border/30 dark:hover:bg-earth-700 transition focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                >
                  <Mail className="h-5 w-5 text-lsc-rose dark:text-lsc-rose-light shrink-0" aria-hidden="true" />
                  <span className="flex flex-col">
                    <span className="font-semibold">{t('askLibrarian.emailUs', 'Email us')}</span>
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 break-all">{branding.contact_email}</span>
                  </span>
                </a>
                <a
                  href="/locations"
                  className="flex items-center gap-3 rounded-lg border border-lsc-border dark:border-earth-700 px-4 py-3 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border/30 dark:hover:bg-earth-700 transition focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                >
                  <MapPin className="h-5 w-5 text-lsc-rose dark:text-lsc-rose-light shrink-0" aria-hidden="true" />
                  <span className="flex flex-col">
                    <span className="font-semibold">{t('askLibrarian.visitTheDesk', 'Visit the desk')}</span>
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('askLibrarian.hoursAndLocations', 'Hours & locations')}</span>
                  </span>
                </a>
              </div>
            </section>

            <div className="flex items-center gap-2 mb-3">
              <Users className="h-6 w-6 text-lsc-rose dark:text-lsc-rose-light" />
              <h2 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">
                {t('askLibrarian.chatWithAiNow', 'Or chat with our library assistant now')}
              </h2>
            </div>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-8 max-w-2xl">
              {t('askLibrarian.chatWithAiNowBody', 'Our library assistant can help right away. Pick the kind of help you need. It is not a real person, and it can be wrong, so check anything important with library staff.')}
            </p>

            {isLoadingAgents ? (
              <div className="motion-safe:animate-pulse" aria-busy="true" aria-live="polite">
                <span className="sr-only">{t('askLibrarian.loadingLibrarians', 'Loading librarians…')}</span>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm h-full flex flex-col items-center"
                    >
                      <div className="w-16 h-16 rounded-full bg-lsc-border dark:bg-earth-700 mb-4"></div>
                      <div className="h-5 w-2/3 bg-lsc-border dark:bg-earth-700 rounded mb-2"></div>
                      <div className="h-3 w-1/2 bg-lsc-border dark:bg-earth-700 rounded mb-4"></div>
                      <div className="h-3 w-full bg-lsc-border dark:bg-earth-700 rounded mb-1.5"></div>
                      <div className="h-3 w-full bg-lsc-border dark:bg-earth-700 rounded mb-1.5"></div>
                      <div className="h-3 w-4/5 bg-lsc-border dark:bg-earth-700 rounded"></div>
                    </div>
                  ))}
                </div>
              </div>
            ) : agentsError ? (
              <div className="max-w-2xl bg-lsc-white dark:bg-earth-800 border border-status-danger-200 dark:border-status-danger-900/40 rounded-xl p-6 shadow-sm">
                <h3 className="font-serif text-lg font-semibold text-status-danger-700 dark:text-status-danger-400 mb-2">
                  {t('askLibrarian.unableToLoadLibrarians', 'Unable to load librarians right now')}
                </h3>
                <p className="text-lsc-dark/80 dark:text-lsc-cream/80 mb-4">
                  {t('askLibrarian.unableToLoadLibrariansBody', 'Please try again in a moment, or reach out to us directly if this keeps happening.')}
                </p>
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={fetchAgentsData}
                    className="bg-lsc-rose hover:bg-lsc-rose-dark text-white px-4 py-2 rounded-lg transition"
                  >
                    {t('common.retry', 'Retry')}
                  </button>
                  <a
                    href="/contact"
                    className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border/30 dark:hover:bg-earth-700 transition"
                  >
                    {t('askLibrarian.contactTheLibrary', 'Contact the library')}
                  </a>
                </div>
              </div>
            ) : agents.length === 0 ? (
              <div className="max-w-2xl bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                  {t('askLibrarian.noLibrariansAvailable', 'No librarians are available right now')}
                </h3>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('askLibrarian.noLibrariansAvailableBody', 'Please check back soon, or visit our contact page for other ways to get help.')}
                </p>
              </div>
            ) : (
              <ul role="list" aria-label={t('aria.askLibrarian.availableLibrarians')} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {agents.map((agent) => {
                  // Lead with the need, not a fictional staff identity. The chat
                  // handoff still uses the full agent object, so startChat is unchanged.
                  const needLabel =
                    agent.specialties?.length > 0
                      ? agent.specialties.join(", ")
                      : agent.role;
                  return (
                  <li key={agent.id}>
                    <article className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm hover:shadow-lg transition-all h-full flex flex-col">
                      <div
                        style={{ backgroundColor: resolveAvatarColor(agent.avatar_color) }}
                        className="w-12 h-12 rounded-lg flex items-center justify-center mb-4"
                        aria-hidden="true"
                      >
                        <span className="text-lsc-cream">
                          {getAgentIcon(agent.emoji || "", "w-6 h-6", false)}
                        </span>
                      </div>

                      <div className="flex-1 flex flex-col">
                        <span className="inline-flex w-fit items-center gap-1 text-xs font-medium text-status-warning-700 dark:text-status-warning-300 bg-status-warning-100 dark:bg-status-warning-900/30 px-2 py-0.5 rounded-full mb-3">
                          <Sparkles className="w-3 h-3" aria-hidden="true" />
                          {t('askLibrarian.aiAssistantLabel', 'Library Assistant')}
                        </span>
                        <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                          {needLabel}
                        </h3>
                        <button
                          onClick={() => startChat(agent)}
                          aria-label={`${t('askLibrarian.startAiChatPrefix', 'Start chat: ')}${needLabel}`}
                          className="mt-auto self-start text-lsc-rose-dark dark:text-status-warning-300 hover:underline underline-offset-2 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
                        >
                          {t('askLibrarian.startChat', 'Start Chat →')}
                        </button>
                      </div>
                    </article>
                  </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

