/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * AI Said What? - Hallucination Spotter Lab
 * Spot which "facts" the AI made up
 */
import { useState, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, ArrowRight, RotateCcw, Trophy } from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import { useQueryClient } from '@tanstack/react-query';
import * as Sentry from '@/lib/sentry-lazy';
import { api } from '@/lib/api-client';
import { useAuth } from '@/contexts/AuthContext';

const LAB_SLUG = 'ai-said-what';

interface LabAwardResponse {
  awarded: boolean;
  badge: { slug: string; name: string; xp_value: number };
  is_first_completion: boolean;
}

const ANSWER_OPTIONS = ['real', 'fake', 'unsure'] as const;

interface Claim {
  text: string;
  isReal: boolean;
  explanation: string;
}

interface Round {
  topic: string;
  claims: Claim[];
}

const ROUNDS: Round[] = [
  {
    topic: 'Local History',
    claims: [
      { text: 'Our town was founded in 1847 by German immigrants.', isReal: false, explanation: 'AI made this up! There\'s no record of this founding date or origin.' },
      { text: 'The town library was established in 1952.', isReal: true, explanation: 'This is actually true - we have the records!' },
      { text: 'The creek was originally called "Petit Ruisseau" by French trappers.', isReal: false, explanation: 'Sounds fancy, but completely fabricated. AI loves adding "historical" details.' },
      { text: 'The population is under 5,000 residents.', isReal: true, explanation: 'Correct! Small town vibes.' },
    ],
  },
  {
    topic: 'Famous Authors',
    claims: [
      { text: 'Stephen King\'s first published novel was "Carrie" in 1974.', isReal: true, explanation: 'True! Carrie launched his career.' },
      { text: 'J.K. Rowling wrote Harry Potter while working as a French teacher.', isReal: false, explanation: 'She was a secretary and English teacher, not French. Small detail AI got wrong.' },
      { text: 'Mark Twain\'s real name was Samuel Clemens.', isReal: true, explanation: 'Correct! Mark Twain was his pen name.' },
      { text: 'Agatha Christie disappeared for 11 days in 1926, and no one knows why.', isReal: true, explanation: 'This actually happened! One of history\'s great mysteries.' },
    ],
  },
  {
    topic: 'Science Facts',
    claims: [
      { text: 'Octopuses have three hearts.', isReal: true, explanation: 'True! Two pump blood to gills, one to the body.' },
      { text: 'The Great Wall of China is visible from space with the naked eye.', isReal: false, explanation: 'Common myth! It\'s too narrow to see from orbit.' },
      { text: 'Honey never spoils - 3000-year-old honey is still edible.', isReal: true, explanation: 'True! Honey found in Egyptian tombs was still good.' },
      { text: 'Humans share 60% of their DNA with bananas.', isReal: true, explanation: 'Surprisingly true! We share a lot of basic cellular machinery.' },
    ],
  },
];

type Answer = 'real' | 'fake' | 'unsure' | null;

export default function AISaidWhatLab() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [currentRound, setCurrentRound] = useState(0);
  const [answers, setAnswers] = useState<Answer[]>([null, null, null, null]);
  const [revealed, setRevealed] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });
  const [gameComplete, setGameComplete] = useState(false);

  // Refs for keyboard navigation on each claim's button group
  const buttonGroupRefs = useRef<(HTMLDivElement | null)[]>([]);

  const round = ROUNDS[currentRound]!;

  const handleAnswer = (index: number, answer: Answer) => {
    if (revealed) return;
    const newAnswers = [...answers];
    newAnswers[index] = answer;
    setAnswers(newAnswers);
  };


  // Keyboard navigation handler for radio group pattern (WCAG 2.2)
  const handleKeyDown = useCallback((
    e: React.KeyboardEvent,
    claimIndex: number,
    optionIndex: number
  ) => {
    if (revealed) return;

    let newIndex: number | null = null;

    switch (e.key) {
      case 'ArrowLeft':
      case 'ArrowUp':
        e.preventDefault();
        newIndex = optionIndex > 0 ? optionIndex - 1 : ANSWER_OPTIONS.length - 1;
        break;
      case 'ArrowRight':
      case 'ArrowDown':
        e.preventDefault();
        newIndex = optionIndex < ANSWER_OPTIONS.length - 1 ? optionIndex + 1 : 0;
        break;
      case 'Home':
        e.preventDefault();
        newIndex = 0;
        break;
      case 'End':
        e.preventDefault();
        newIndex = ANSWER_OPTIONS.length - 1;
        break;
    }

    if (newIndex !== null) {
      const option = ANSWER_OPTIONS[newIndex];
      if (option) {
        handleAnswer(claimIndex, option);
        // Focus the new button after state update
        const buttonGroup = buttonGroupRefs.current[claimIndex];
        const buttons = buttonGroup?.querySelectorAll('button');
        buttons?.[newIndex]?.focus();
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revealed]);

  const handleReveal = () => {
    setRevealed(true);
    let correct = 0;
    answers.forEach((answer, i) => {
      const claim = round.claims[i]!;
      if ((answer === 'real' && claim.isReal) || (answer === 'fake' && !claim.isReal)) {
        correct++;
      }
    });
    setScore(prev => ({ correct: prev.correct + correct, total: prev.total + 4 }));
  };

  const handleNext = () => {
    if (currentRound < ROUNDS.length - 1) {
      setCurrentRound(prev => prev + 1);
      setAnswers([null, null, null, null]);
      setRevealed(false);
    } else {
      setGameComplete(true);
      if (isAuthenticated) {
        api
          .post<LabAwardResponse>(`/learning/labs/${LAB_SLUG}/complete`, {
            score: score.correct,
            total: score.total,
          })
          .then(res => {
            queryClient.invalidateQueries({ queryKey: ['my-achievements'] });
            queryClient.invalidateQueries({ queryKey: ['my-stats'] });
            if (res.is_first_completion) {
              toast.success(`Badge earned: ${res.badge.name}!`);
            }
          })
          .catch(err => {
            Sentry.captureException(err);
          });
      }
    }
  };

  const handleRestart = () => {
    setCurrentRound(0);
    setAnswers([null, null, null, null]);
    setRevealed(false);
    setScore({ correct: 0, total: 0 });
    setGameComplete(false);
  };

  if (gameComplete) {
    const percentage = Math.round((score.correct / score.total) * 100);
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 shadow-lg">
            <Trophy aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-rose mb-4" />
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Nice Work!
            </h1>
            <p className="text-5xl font-bold text-lsc-rose dark:text-lsc-rose-light mb-4">
              {score.correct} / {score.total}
            </p>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
              {percentage >= 80 ? "You're a hallucination-spotting pro!" :
               percentage >= 60 ? "Pretty good! AI can be tricky." :
               "Don't worry - even experts get fooled. That's the point!"}
            </p>
            <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-4 mb-6 text-left">
              <p className="font-medium text-lsc-dark dark:text-earth-300 mb-2">What you learned:</p>
              <ul className="text-sm text-lsc-rose dark:text-lsc-cream/70 space-y-1">
                <li>• AI confidently makes up "facts" - always verify important info</li>
                <li>• Specific details (dates, names) are often fabricated</li>
                <li>• Even true-sounding claims need checking</li>
              </ul>
            </div>
            <div className="flex gap-4 justify-center">
              <button
                type="button"
                onClick={handleRestart}
                className="flex items-center gap-2 px-6 py-3 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
              >
                <RotateCcw aria-hidden="true" className="w-5 h-5" />
                Play Again
              </button>
              <Link
                to="/learn/labs"
                className="flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
              >
                More Labs
                <ArrowRight aria-hidden="true" className="w-5 h-5" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const allAnswered = answers.every(a => a !== null);

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <Link
          to="/learn/labs"
          className="inline-flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose mb-6 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
        >
          <ArrowLeft aria-hidden="true" className="w-4 h-4" />
          Back to Labs
        </Link>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
          {/* Progress */}
          <div className="bg-gradient-to-r from-lsc-rose to-orange-500 px-6 py-4">
            <div className="flex items-center justify-between text-white">
              <h1 className="font-serif text-xl font-bold">AI Said What?</h1>
              <span className="text-status-warning-100">
                Round {currentRound + 1} of {ROUNDS.length}
              </span>
            </div>
            <div className="mt-2 h-1 bg-lsc-white dark:bg-earth-800/30 rounded-full">
              <div
                className="h-full bg-lsc-white dark:bg-earth-800 rounded-full transition-all"
                style={{ width: `${((currentRound + 1) / ROUNDS.length) * 100}%` }}
              />
            </div>
          </div>

          <div className="p-6">
            {/* Topic */}
            <div className="text-center mb-6">
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">Topic:</p>
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                {round.topic}
              </h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                AI made some claims. Which are real? Which did it make up?
              </p>
            </div>

            {/* Claims */}
            <div className="space-y-4">
              {round.claims.map((claim, i) => (
                <div
                  key={i}
                  className={clsx(
                    'rounded-xl border-2 p-4 transition-all',
                    revealed
                      ? claim.isReal
                        ? 'border-status-success-300 dark:border-status-success-700 bg-status-success-50 dark:bg-status-success-900/20'
                        : 'border-status-danger-300 dark:border-status-danger-700 bg-status-danger-50 dark:bg-status-danger-900/20'
                      : 'border-lsc-border dark:border-earth-700 bg-lsc-cream dark:bg-lsc-brown/50'
                  )}
                >
                  <p className="text-lsc-dark dark:text-lsc-cream mb-3">"{claim.text}"</p>

                  {!revealed ? (
                    <div
                      ref={(el) => { buttonGroupRefs.current[i] = el; }}
                      role="radiogroup"
                      aria-label={`Rate claim: ${claim.text}`}
                      className="flex gap-2"
                    >
                      {ANSWER_OPTIONS.map((option, optionIndex) => {
                        const isSelected = answers[i] === option;
                        const label = option === 'real' ? 'Real' : option === 'fake' ? 'Fake' : '? Unsure';
                        return (
                          <button
                            key={option}
                            type="button"
                            role="radio"
                            aria-checked={isSelected}
                            aria-label={`Mark as ${option}`}
                            tabIndex={isSelected || (answers[i] === null && optionIndex === 0) ? 0 : -1}
                            onClick={() => handleAnswer(i, option)}
                            onKeyDown={(e) => handleKeyDown(e, i, optionIndex)}
                            className={clsx(
                              'flex-1 py-2 px-3 rounded-xl text-sm font-medium transition-colors',
                              'focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2',
                              isSelected
                                ? option === 'real' ? 'bg-status-success-500 text-white' :
                                  option === 'fake' ? 'bg-status-danger-500 text-white' :
                                  'bg-lsc-rose text-white'
                                : 'bg-lsc-white dark:bg-lsc-brown text-lsc-dark/70 dark:text-earth-300 hover:bg-lsc-cream dark:hover:bg-lsc-rose'
                            )}
                          >
                            {label}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex items-start gap-3">
                      {claim.isReal ? (
                        <CheckCircle aria-hidden="true" className="w-5 h-5 text-status-success-600 flex-shrink-0 mt-0.5" />
                      ) : (
                        <XCircle aria-hidden="true" className="w-5 h-5 text-status-danger-600 flex-shrink-0 mt-0.5" />
                      )}
                      <div>
                        <p className={clsx(
                          'font-medium text-sm',
                          claim.isReal ? 'text-status-success-700 dark:text-status-success-300' : 'text-status-danger-700 dark:text-status-danger-300'
                        )}>
                          {claim.isReal ? 'This is real!' : 'AI made this up!'}
                        </p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          {claim.explanation}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Actions */}
            <div className="mt-6 flex justify-center">
              {!revealed ? (
                <button
                  type="button"
                  onClick={handleReveal}
                  disabled={!allAnswered}
                  aria-disabled={!allAnswered}
                  className={clsx(
                    'px-8 py-3 rounded-xl font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2',
                    allAnswered
                      ? 'bg-lsc-rose text-white hover:bg-lsc-rose/90'
                      : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
                  )}
                >
                  Reveal Answers
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleNext}
                  className="flex items-center gap-2 px-8 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                >
                  {currentRound < ROUNDS.length - 1 ? 'Next Round' : 'See Results'}
                  <ArrowRight aria-hidden="true" className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
