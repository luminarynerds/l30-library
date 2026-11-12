/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Who Wrote This? - Human vs AI Writing Detection
 * Spot which paragraph was written by AI
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, RotateCcw, Trophy, User, Bot } from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import { useQueryClient } from '@tanstack/react-query';
import * as Sentry from '@/lib/sentry-lazy';
import { api } from '@/lib/api-client';
import { useAuth } from '@/contexts/AuthContext';

const LAB_SLUG = 'who-wrote-this';

interface LabAwardResponse {
  awarded: boolean;
  badge: { slug: string; name: string; xp_value: number };
  is_first_completion: boolean;
}

interface WritingSample {
  text: string;
  isAI: boolean;
  tell: string;
}

interface Round {
  topic: string;
  samples: WritingSample[];
}

const ROUNDS: Round[] = [
  {
    topic: 'Describing a Rainy Day',
    samples: [
      {
        text: 'The rain started around noon, just as I was heating up leftover soup. My cat immediately claimed the windowsill, watching the drops race down the glass like it was the most fascinating thing she\'d ever seen.',
        isAI: false,
        tell: 'Personal details (leftover soup, cat\'s behavior) that feel specific and lived-in.'
      },
      {
        text: 'The rain descended upon the city like a gentle curtain, transforming the urban landscape into a symphony of glistening streets and rhythmic droplets. The atmosphere was imbued with a sense of renewal and tranquility.',
        isAI: true,
        tell: 'Overly poetic language ("gentle curtain," "symphony"), generic descriptions, no specific details.'
      },
      {
        text: 'Rain days are honestly the best for getting stuff done. No guilt about staying inside, perfect excuse to make tea, and somehow my brain just works better when it\'s gray out. Weird but true.',
        isAI: false,
        tell: 'Casual voice, personal opinion ("weird but true"), conversational asides.'
      },
    ],
  },
  {
    topic: 'Why I Love Libraries',
    samples: [
      {
        text: 'Libraries serve as invaluable community resources, offering not only access to books and digital media but also providing essential services such as computer access, educational programs, and safe spaces for learning and growth.',
        isAI: true,
        tell: 'List-like structure, no personal connection, sounds like a brochure.'
      },
      {
        text: 'There\'s a particular smell old libraries have - kind of dusty but in a good way? My local branch still has those wooden card catalogs even though everything\'s digital now. I hope they never get rid of them.',
        isAI: false,
        tell: 'Sensory details, uncertainty ("kind of?"), emotional attachment to specific things.'
      },
      {
        text: 'The library down the street saved me during unemployment. Free wifi, quiet space to job hunt, and the librarian who pretended not to notice when I cried in the biography section that one time.',
        isAI: false,
        tell: 'Vulnerable personal story, specific detail ("biography section"), humor about hard times.'
      },
    ],
  },
  {
    topic: 'Morning Coffee',
    samples: [
      {
        text: 'My morning coffee ritual is non-negotiable: same mug (the chipped blue one), same spot at the counter, same few minutes of silence before the day starts. It\'s not about the caffeine, it\'s about the pause.',
        isAI: false,
        tell: 'Specific object ("chipped blue one"), philosophical observation, personal ritual.'
      },
      {
        text: 'The first sip of morning coffee is a transformative experience, awakening the senses and preparing the mind for the day ahead. The rich aroma and complex flavor profile combine to create a moment of pure satisfaction.',
        isAI: true,
        tell: '"Transformative experience," "complex flavor profile" - marketing speak, no real feeling.'
      },
      {
        text: 'Coffee in the morning represents more than just a beverage choice; it embodies a daily ritual that millions of people around the world share, connecting us through this universal appreciation for caffeinated warmth.',
        isAI: true,
        tell: 'Trying to sound profound, vague universalizing ("millions of people"), no personal voice.'
      },
    ],
  },
];

export default function WhoWroteThisLab() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [currentRound, setCurrentRound] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });
  const [gameComplete, setGameComplete] = useState(false);

  const round = ROUNDS[currentRound]!;
  const aiIndex = round.samples.findIndex(s => s.isAI);

  const handleSelect = (index: number) => {
    if (revealed) return;
    setSelected(index);
  };

  const handleReveal = () => {
    setRevealed(true);
    if (selected === aiIndex) {
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
            <Trophy aria-hidden="true" className="w-16 h-16 mx-auto text-teal-500 mb-4" />
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              {percentage >= 80 ? 'Sharp Eye!' : percentage >= 50 ? 'Not Bad!' : 'Tricky, Right?'}
            </h1>
            <p className="text-5xl font-bold text-teal-600 dark:text-teal-400 mb-4">
              {score.correct} / {score.total}
            </p>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
              {percentage >= 80 ? 'You can spot AI writing like a pro!' :
               percentage >= 50 ? 'AI is getting better, but you\'ve got good instincts.' :
               'Don\'t feel bad - AI writing is designed to fool us!'}
            </p>
            <div className="bg-teal-50 dark:bg-teal-900/20 rounded-xl p-4 mb-6 text-left">
              <p className="font-medium text-teal-800 dark:text-teal-200 mb-2">AI Writing Tells:</p>
              <ul className="text-sm text-teal-700 dark:text-teal-300 space-y-1">
                <li>• Overly formal or "polished" language</li>
                <li>• Generic descriptions, no specific personal details</li>
                <li>• Tries too hard to sound profound</li>
                <li>• Missing the messy, uncertain parts of human thought</li>
              </ul>
            </div>
            <div className="flex gap-4 justify-center">
              <button onClick={handleRestart} className="flex items-center gap-2 px-6 py-3 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown/90">
                <RotateCcw aria-hidden="true" className="w-5 h-5" /> Play Again
              </button>
              <Link to="/learn/labs" className="flex items-center gap-2 px-6 py-3 bg-teal-600 text-white rounded-xl hover:bg-teal-700">
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
        <Link to="/learn/labs" className="inline-flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-teal-600 hover:underline mb-6">
          <ArrowLeft aria-hidden="true" className="w-4 h-4" /> Back to Labs
        </Link>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
          <div className="bg-gradient-to-r from-teal-500 to-cyan-500 px-6 py-4">
            <div className="flex items-center justify-between text-white">
              <h1 className="font-serif text-xl font-bold">Who Wrote This?</h1>
              <span className="text-teal-100">Round {currentRound + 1} of {ROUNDS.length}</span>
            </div>
            <div className="mt-2 h-1 bg-lsc-white dark:bg-earth-800/30 rounded-full">
              <div className="h-full bg-lsc-white dark:bg-earth-800 rounded-full transition-all" style={{ width: `${((currentRound + 1) / ROUNDS.length) * 100}%` }} />
            </div>
          </div>

          <div className="p-6">
            <div className="text-center mb-6">
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">Topic:</p>
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{round.topic}</h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                One of these was written by AI. Which one?
              </p>
            </div>

            <div className="space-y-4">
              {round.samples.map((sample, i) => (
                <button
                  key={i}
                  onClick={() => handleSelect(i)}
                  disabled={revealed}
                  className={clsx(
                    'w-full text-left rounded-xl border-2 p-4 transition-all',
                    revealed
                      ? sample.isAI
                        ? 'border-status-danger-400 dark:border-status-danger-600 bg-status-danger-50 dark:bg-status-danger-900/20'
                        : 'border-status-success-400 dark:border-status-success-600 bg-status-success-50 dark:bg-status-success-900/20'
                      : selected === i
                        ? 'border-teal-400 dark:border-teal-500 bg-teal-50 dark:bg-teal-900/20'
                        : 'border-lsc-border dark:border-earth-700 hover:border-lsc-border dark:hover:border-earth-500 bg-lsc-cream dark:bg-lsc-brown/50'
                  )}
                >
                  <p className="text-lsc-dark dark:text-lsc-cream italic">"{sample.text}"</p>
                  
                  {revealed && (
                    <div className="mt-3 flex items-start gap-2">
                      {sample.isAI ? (
                        <Bot aria-hidden="true" className="w-5 h-5 text-status-danger-500 flex-shrink-0" />
                      ) : (
                        <User aria-hidden="true" className="w-5 h-5 text-status-success-500 flex-shrink-0" />
                      )}
                      <div>
                        <p className={clsx('font-medium text-sm', sample.isAI ? 'text-status-danger-700 dark:text-status-danger-300' : 'text-status-success-700 dark:text-status-success-300')}>
                          {sample.isAI ? 'AI wrote this!' : 'Human wrote this'}
                        </p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{sample.tell}</p>
                      </div>
                    </div>
                  )}
                </button>
              ))}
            </div>

            <div className="mt-6 flex justify-center">
              {!revealed ? (
                <button
                  onClick={handleReveal}
                  disabled={selected === null}
                  className={clsx(
                    'px-8 py-3 rounded-xl font-medium transition-colors',
                    selected !== null ? 'bg-teal-600 text-white hover:bg-teal-700' : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
                  )}
                >
                  Check My Answer
                </button>
              ) : (
                <button onClick={handleNext} className="flex items-center gap-2 px-8 py-3 bg-teal-600 text-white rounded-xl hover:bg-teal-700">
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
