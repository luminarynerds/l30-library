/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Real or Fake? - Deepfake Detective Lab
 * Spot AI-generated content
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, RotateCcw, Trophy, ImageOff, Camera, Bot } from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import { useQueryClient } from '@tanstack/react-query';
import * as Sentry from '@/lib/sentry-lazy';
import { api } from '@/lib/api-client';
import { useAuth } from '@/contexts/AuthContext';

const LAB_SLUG = 'real-or-fake';

interface LabAwardResponse {
  awarded: boolean;
  badge: { slug: string; name: string; xp_value: number };
  is_first_completion: boolean;
}

interface ImageRound {
  description: string;
  isAI: boolean;
  tell: string;
  imageHint: string; // We'll describe instead of showing
}

const ROUNDS: ImageRound[] = [
  {
    description: 'A photo of a golden retriever sitting in autumn leaves, looking at the camera with a friendly expression.',
    isAI: true,
    tell: 'Look at the background - the leaves have an unnatural, repetitive pattern. AI often struggles with natural randomness.',
    imageHint: 'Hint: AI tends to make backgrounds too "perfect"',
  },
  {
    description: 'A selfie of a woman in her 30s at a coffee shop, slightly blurry background, natural lighting.',
    isAI: false,
    tell: 'The imperfections are natural - slightly uneven lighting, authentic background blur, natural skin texture.',
    imageHint: 'Hint: Real photos have authentic imperfections',
  },
  {
    description: 'A professional headshot of a businessman in a suit, perfect lighting, symmetrical face, smooth skin.',
    isAI: true,
    tell: 'Too perfect! AI faces often have unnaturally symmetrical features and overly smooth skin. Check the ears - they\'re slightly different shapes.',
    imageHint: 'Hint: AI loves making people "too perfect"',
  },
  {
    description: 'A candid photo of friends at a birthday party, one person mid-laugh, cake visible.',
    isAI: false,
    tell: 'The chaos is real - motion blur, overlapping people, genuine expressions. AI struggles with natural group dynamics.',
    imageHint: 'Hint: Genuine chaos is hard for AI',
  },
  {
    description: 'A scenic mountain landscape at sunset with a lake reflection, dramatic clouds.',
    isAI: true,
    tell: 'The reflection doesn\'t quite match the mountains. AI often gets water reflections slightly wrong.',
    imageHint: 'Hint: Check reflections carefully!',
  },
];

export default function RealOrFakeLab() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [currentRound, setCurrentRound] = useState(0);
  const [guess, setGuess] = useState<'real' | 'fake' | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [score, setScore] = useState({ correct: 0, total: 0 });
  const [gameComplete, setGameComplete] = useState(false);

  const round = ROUNDS[currentRound]!;

  const handleGuess = (g: 'real' | 'fake') => {
    if (revealed) return;
    setGuess(g);
  };

  const handleReveal = () => {
    setRevealed(true);
    const correct = (guess === 'fake' && round.isAI) || (guess === 'real' && !round.isAI);
    if (correct) {
      setScore(prev => ({ correct: prev.correct + 1, total: prev.total + 1 }));
    } else {
      setScore(prev => ({ ...prev, total: prev.total + 1 }));
    }
  };

  const handleNext = () => {
    if (currentRound < ROUNDS.length - 1) {
      setCurrentRound(prev => prev + 1);
      setGuess(null);
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
    setGuess(null);
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
            <Trophy aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-rose dark:text-lsc-rose-light mb-4" />
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              {percentage >= 80 ? 'Eagle Eye!' : percentage >= 60 ? 'Good Instincts!' : 'AI Is Tricky!'}
            </h1>
            <p className="text-5xl font-bold text-lsc-rose dark:text-lsc-rose-light mb-4">
              {score.correct} / {score.total}
            </p>
            <div className="bg-lsc-rose/5 dark:bg-lsc-rose/10 rounded-xl p-4 mb-6 text-left">
              <p className="font-medium text-lsc-rose dark:text-lsc-rose-light mb-2">Deepfake Red Flags:</p>
              <ul className="text-sm text-lsc-rose/80 dark:text-lsc-rose-light/80 space-y-1">
                <li>• Hands with wrong number of fingers</li>
                <li>• Overly smooth skin, too-perfect features</li>
                <li>• Weird backgrounds (melting, repeating)</li>
                <li>• Text that doesn\'t make sense</li>
                <li>• Asymmetrical earrings/glasses</li>
              </ul>
            </div>
            <div className="flex gap-4 justify-center">
              <button onClick={handleRestart} className="flex items-center gap-2 px-6 py-3 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl">
                <RotateCcw aria-hidden="true" className="w-5 h-5" /> Play Again
              </button>
              <Link to="/learn/labs" className="flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/80">
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
        <Link to="/learn/labs" className="inline-flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose hover:underline mb-6">
          <ArrowLeft aria-hidden="true" className="w-4 h-4" /> Back to Labs
        </Link>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
          <div className="bg-gradient-to-r from-lsc-rose to-rose-500 px-6 py-4">
            <div className="flex items-center justify-between text-white">
              <h1 className="font-serif text-xl font-bold">Real or Fake?</h1>
              <span className="text-lsc-rose-light">{currentRound + 1} of {ROUNDS.length}</span>
            </div>
          </div>

          <div className="p-6">
            {/* Image Placeholder */}
            <div className="aspect-video bg-lsc-cream dark:bg-lsc-brown rounded-xl mb-6 flex flex-col items-center justify-center">
              <ImageOff aria-hidden="true" className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mb-3" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center px-4 mb-2">
                {round.description}
              </p>
              <p className="text-2xl">{round.imageHint}</p>
            </div>

            <p className="text-center text-lsc-dark dark:text-lsc-cream font-medium mb-4">
              Is this image real or AI-generated?
            </p>

            {!revealed ? (
              <div className="flex gap-4 justify-center mb-6">
                <button
                  onClick={() => handleGuess('real')}
                  className={clsx(
                    'flex-1 max-w-[150px] py-4 rounded-xl font-medium transition-all flex items-center justify-center gap-2',
                    guess === 'real'
                      ? 'bg-status-success-500 text-white scale-105'
                      : 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 hover:bg-status-success-200'
                  )}
                >
                  <Camera className="w-4 h-4" aria-hidden="true" /> Real
                </button>
                <button
                  onClick={() => handleGuess('fake')}
                  className={clsx(
                    'flex-1 max-w-[150px] py-4 rounded-xl font-medium transition-all flex items-center justify-center gap-2',
                    guess === 'fake'
                      ? 'bg-status-danger-500 text-white scale-105'
                      : 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 hover:bg-status-danger-200'
                  )}
                >
                  <Bot className="w-4 h-4" aria-hidden="true" /> AI Fake
                </button>
              </div>
            ) : (
              <div className={clsx(
                'rounded-xl p-4 mb-6',
                round.isAI ? 'bg-status-danger-50 dark:bg-status-danger-900/20' : 'bg-status-success-50 dark:bg-status-success-900/20'
              )}>
                <p className={clsx(
                  'font-bold text-lg mb-2 flex items-center gap-2',
                  round.isAI ? 'text-status-danger-700 dark:text-status-danger-300' : 'text-status-success-700 dark:text-status-success-300'
                )}>
                  {round.isAI ? <><Bot className="w-5 h-5" aria-hidden="true" /> AI Generated!</> : <><Camera className="w-5 h-5" aria-hidden="true" /> Real Photo!</>}
                </p>
                <p className="text-lsc-dark dark:text-lsc-cream/80">{round.tell}</p>
              </div>
            )}

            <div className="flex justify-center">
              {!revealed ? (
                <button
                  onClick={handleReveal}
                  disabled={!guess}
                  className={clsx(
                    'px-8 py-3 rounded-xl font-medium',
                    guess ? 'bg-lsc-rose text-white hover:bg-lsc-rose/80' : 'bg-lsc-cream text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
                  )}
                >
                  Reveal Answer
                </button>
              ) : (
                <button onClick={handleNext} className="flex items-center gap-2 px-8 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/80">
                  {currentRound < ROUNDS.length - 1 ? 'Next Image' : 'See Results'} <ArrowRight aria-hidden="true" className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
