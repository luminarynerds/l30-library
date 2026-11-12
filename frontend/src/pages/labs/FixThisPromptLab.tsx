/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Fix This Prompt - Prompt Makeover Lab
 * See how better prompts get better results
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, RotateCcw, Trophy, ThumbsUp, ThumbsDown } from 'lucide-react';
import clsx from 'clsx';
import { useTranslation } from '@/i18n'
import toast from 'react-hot-toast';
import { useQueryClient } from '@tanstack/react-query';
import * as Sentry from '@/lib/sentry-lazy';
import { api } from '@/lib/api-client';
import { useAuth } from '@/contexts/AuthContext';

const LAB_SLUG = 'fix-this-prompt';

interface LabAwardResponse {
  awarded: boolean;
  badge: { slug: string; name: string; xp_value: number };
  is_first_completion: boolean;
}

interface PromptExample {
  badPrompt: string;
  badResponse: string;
  options: { text: string; isGood: boolean; explanation: string }[];
  goodResponse: string;
  tip: string;
}

const ROUNDS: PromptExample[] = [
  {
    badPrompt: 'Write something about dogs.',
    badResponse: 'Dogs are wonderful pets that have been companions to humans for thousands of years. They come in many breeds and sizes, from small Chihuahuas to large Great Danes. Dogs are known for their loyalty, playfulness, and ability to form strong bonds with their owners...',
    options: [
      { text: 'Write more about dogs please.', isGood: false, explanation: 'Still too vague! More of the same.' },
      { text: 'Write a 2-paragraph guide for first-time dog owners on what to expect in the first week.', isGood: true, explanation: 'Specific audience, clear format, focused topic!' },
      { text: 'Write something better about dogs.', isGood: false, explanation: '"Better" how? AI can\'t read your mind.' },
    ],
    goodResponse: 'Your first week with a new dog can feel overwhelming, but preparation makes all the difference. Before bringing your pup home, set up a quiet space with their bed, water bowl, and a few toys...',
    tip: 'Be specific: WHO is this for? WHAT format? HOW long?',
  },
  {
    badPrompt: 'Explain AI.',
    badResponse: 'Artificial Intelligence (AI) refers to the simulation of human intelligence in machines that are programmed to think and learn like humans. The field encompasses various subfields including machine learning, natural language processing, computer vision, and robotics...',
    options: [
      { text: 'Explain AI like I\'m 10 years old, using a video game analogy.', isGood: true, explanation: 'Clear audience, specific approach, relatable example!' },
      { text: 'Explain AI better.', isGood: false, explanation: 'What does "better" mean to you?' },
      { text: 'Tell me everything about AI.', isGood: false, explanation: 'Way too broad - you\'ll get a textbook.' },
    ],
    goodResponse: 'You know how in video games, the characters you don\'t control still walk around and make decisions? That\'s kind of like AI! The game programmers taught them rules about what to do...',
    tip: 'Set the level: WHO is your audience? Use analogies they\'ll get.',
  },
  {
    badPrompt: 'Help me with my email.',
    badResponse: 'I\'d be happy to help with your email! What would you like assistance with? Writing a new email, responding to one, organizing your inbox, or something else?',
    options: [
      { text: 'Just fix it.', isGood: false, explanation: 'Fix WHAT? AI didn\'t see your email.' },
      { text: 'Help me write a polite but firm email to my landlord about a broken heater that\'s been ignored for 2 weeks.', isGood: true, explanation: 'Context, tone, and specific situation!' },
      { text: 'Write a good email for me.', isGood: false, explanation: 'About what? To whom? What tone?' },
    ],
    goodResponse: 'Subject: Urgent: Heating Repair Needed - Follow Up\n\nDear [Landlord],\n\nI\'m writing to follow up on my heating repair request from [date]. The heater in my unit has been non-functional for two weeks now, and with temperatures dropping...',
    tip: 'Give context: What\'s the situation? What outcome do you want?',
  },
];

export default function FixThisPromptLab() {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [currentRound, setCurrentRound] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });
  const [gameComplete, setGameComplete] = useState(false);

  const round = ROUNDS[currentRound]!;
  const goodIndex = round.options.findIndex(o => o.isGood);

  const handleSelect = (index: number) => {
    if (revealed) return;
    setSelected(index);
  };

  const handleReveal = () => {
    setRevealed(true);
    if (selected === goodIndex) {
      setScore(prev => ({ correct: prev.correct + 1, total: prev.total + 1 }));
    } else {
      setScore(prev => ({ ...prev, total: prev.total + 1 }));
    }
  };

  const handleNext = () => {
    if (currentRound < ROUNDS.length - 1) {
      setCurrentRound(prev => prev + 1);
      setSelected(null);
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
    setSelected(null);
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
            <Trophy aria-hidden="true" className="w-16 h-16 mx-auto text-category-500 mb-4" />
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              {percentage >= 80 ? 'Prompt Pro!' : percentage >= 50 ? 'Getting There!' : 'Now You Know!'}
            </h1>
            <p className="text-5xl font-bold text-category-600 dark:text-category-400 mb-4">
              {score.correct} / {score.total}
            </p>
            <div className="bg-category-50 dark:bg-category-900/20 rounded-xl p-4 mb-6 text-left">
              <p className="font-medium text-category-800 dark:text-category-200 mb-2">Great Prompts Include:</p>
              <ul className="text-sm text-category-700 dark:text-category-300 space-y-1">
                <li>• <strong>Who:</strong> {t('fixThisPromptLab.whoIsThisFor')}</li>
                <li>• <strong>What:</strong> What format/length?</li>
                <li>• <strong>Context:</strong> {t('fixThisPromptLab.whatSTheSituation')}</li>
                <li>• <strong>Tone:</strong> Formal? Casual? Funny?</li>
              </ul>
            </div>
            <div className="flex gap-4 justify-center">
              <button onClick={handleRestart} className="flex items-center gap-2 px-6 py-3 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown/90">
                <RotateCcw aria-hidden="true" className="w-5 h-5" /> Play Again
              </button>
              <Link to="/learn/labs" className="flex items-center gap-2 px-6 py-3 bg-category-600 text-white rounded-xl hover:bg-category-700">
                More Labs <ArrowRight aria-hidden="true" className="w-5 h-5" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <Link to="/learn/labs" className="inline-flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-category-600 hover:underline mb-6">
          <ArrowLeft aria-hidden="true" className="w-4 h-4" /> Back to Labs
        </Link>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
          <div className="bg-gradient-to-r from-category-500 to-violet-500 px-6 py-4">
            <div className="flex items-center justify-between text-white">
              <h1 className="font-serif text-xl font-bold">Fix This Prompt</h1>
              <span className="text-category-100">Round {currentRound + 1} of {ROUNDS.length}</span>
            </div>
          </div>

          <div className="p-6">
            {/* Bad Prompt */}
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-2">
                <ThumbsDown aria-hidden="true" className="w-4 h-4 text-status-danger-500" />
                <span className="text-sm font-medium text-status-danger-600 dark:text-status-danger-400">Vague Prompt:</span>
              </div>
              <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-3">
                <p className="font-mono text-sm text-status-danger-800 dark:text-status-danger-200">"{round.badPrompt}"</p>
              </div>
            </div>

            {/* Bad Response */}
            <div className="mb-6">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{t('fixThisPromptLab.aiSGenericResponse')}</p>
              <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">
                "{round.badResponse.slice(0, 150)}..."
              </div>
            </div>

            {/* Options */}
            <div className="mb-6">
              <p className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">
                Which prompt would work better?
              </p>
              <div className="space-y-3">
                {round.options.map((option, i) => (
                  <button
                    key={i}
                    onClick={() => handleSelect(i)}
                    disabled={revealed}
                    className={clsx(
                      'w-full text-left rounded-xl border-2 p-3 transition-all',
                      revealed
                        ? option.isGood
                          ? 'border-status-success-400 bg-status-success-50 dark:bg-status-success-900/20'
                          : 'border-status-danger-300 dark:border-status-danger-700 bg-status-danger-50 dark:bg-status-danger-900/20'
                        : selected === i
                          ? 'border-category-400 bg-category-50 dark:bg-category-900/20'
                          : 'border-lsc-border dark:border-earth-700 hover:border-lsc-border'
                    )}
                  >
                    <p className="font-mono text-sm text-lsc-dark dark:text-lsc-cream">"{option.text}"</p>
                    {revealed && (
                      <p className={clsx(
                        'mt-2 text-sm',
                        option.isGood ? 'text-status-success-700 dark:text-status-success-300' : 'text-status-danger-600 dark:text-status-danger-400'
                      )}>
                        {option.isGood ? 'Correct: ' : 'Incorrect: '}{option.explanation}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Better Response (shown after reveal) */}
            {revealed && (
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-2">
                  <ThumbsUp aria-hidden="true" className="w-4 h-4 text-status-success-500" />
                  <span className="text-sm font-medium text-status-success-600 dark:text-status-success-400">Better response:</span>
                </div>
                <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-700 rounded-xl p-3 text-sm text-status-success-800 dark:text-status-success-200">
                  "{round.goodResponse.slice(0, 200)}..."
                </div>
                <p className="mt-3 text-sm text-category-700 dark:text-category-300 bg-category-50 dark:bg-category-900/20 rounded-xl p-3">
                  <strong>Tip:</strong> {round.tip}
                </p>
              </div>
            )}

            <div className="flex justify-center">
              {!revealed ? (
                <button
                  onClick={handleReveal}
                  disabled={selected === null}
                  className={clsx(
                    'px-8 py-3 rounded-xl font-medium transition-colors',
                    selected !== null ? 'bg-category-600 text-white hover:bg-category-700' : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
                  )}
                >
                  Check My Answer
                </button>
              ) : (
                <button onClick={handleNext} className="flex items-center gap-2 px-8 py-3 bg-category-600 text-white rounded-xl hover:bg-category-700">
                  {currentRound < ROUNDS.length - 1 ? 'Next Round' : 'See Results'} <ArrowRight aria-hidden="true" className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
