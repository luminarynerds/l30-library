/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable no-case-declarations */
import { useState } from 'react';
import { Puzzle, MessageSquare, Info } from 'lucide-react';
import { useTranslation } from '@/i18n'
import type { SandboxContent } from './lesson-types';
import { MarkdownContent } from './MarkdownContent';

// True when content lacks any sandbox-discriminator field (no sandbox_type and
// no field that drives an interactive variant). Such content was authored as an
// article and cannot be evaluated as a sandbox; we render a read-only fallback
// so the lesson does not silently auto-pass via "".includes("").
function isArticleShapedFallback(content: SandboxContent): boolean {
  if (content.sandbox_type) return false;
  const hasSandboxDiscriminator =
    content.expected_output !== undefined ||
    content.initial_code !== undefined ||
    content.prompt_template !== undefined ||
    (content.blanks && content.blanks.length > 0) ||
    (content.pairs && content.pairs.length > 0) ||
    (content.items && content.items.length > 0);
  return !hasSandboxDiscriminator;
}

export function SandboxPlayer({ content, onComplete }: { content: SandboxContent | null; onComplete: () => void }) {
  const { t } = useTranslation();
  const [userInput, setUserInput] = useState('');
  const [output, setOutput] = useState<string | null>(null);
  const [showHint, setShowHint] = useState(0);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const [matchingSelections, setMatchingSelections] = useState<Record<string, string>>({});
  const [fillBlankAnswers, setFillBlankAnswers] = useState<Record<string, string>>({});

  if (!content) {
    return (
      <div className="p-6 md:p-8">
        <div className="bg-lsc-cream dark:bg-lsc-dark rounded-xl p-6 text-center">
          <Puzzle aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            No sandbox content available.
          </p>
        </div>
      </div>
    );
  }

  if (isArticleShapedFallback(content)) {
    return (
      <div className="p-6 md:p-8 space-y-4">
        <div className="p-4 bg-status-info-50 dark:bg-status-info-900/20 rounded-xl border border-status-info-200 dark:border-status-info-800 flex items-start gap-3">
          <Info aria-hidden="true" className="w-5 h-5 mt-0.5 text-status-info-700 dark:text-status-info-300 shrink-0" />
          <p className="text-sm text-status-info-700 dark:text-status-info-200">
            Hands-on sandbox lesson — interactive component coming soon. Review the material below and mark as reviewed to continue.
          </p>
        </div>
        {content.instructions && (
          <div className="p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl">
            <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">Instructions</h4>
            <p className="text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">{content.instructions}</p>
          </div>
        )}
        {content.body && (
          <MarkdownContent content={content.body} className="prose dark:prose-invert max-w-none text-lsc-dark dark:text-lsc-cream" />
        )}
        {content.key_points && content.key_points.length > 0 && (
          <div className="p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl">
            <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">Key points</h4>
            <ul className="list-disc pl-5 space-y-1 text-sm text-lsc-dark dark:text-lsc-cream">
              {content.key_points.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </div>
        )}
        {content.exercise_steps && content.exercise_steps.length > 0 && (
          <div className="p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl">
            <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">Exercise steps</h4>
            <ol className="list-decimal pl-5 space-y-1 text-sm text-lsc-dark dark:text-lsc-cream">
              {content.exercise_steps.map((s, i) => <li key={i}>{s}</li>)}
            </ol>
          </div>
        )}
        {content.sample_records && content.sample_records.length > 0 && (
          <div className="p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl">
            <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">Sample records</h4>
            <ul className="list-disc pl-5 space-y-1 text-sm text-lsc-dark dark:text-lsc-cream font-mono">
              {content.sample_records.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        )}
        <button
          onClick={onComplete}
          className="w-full py-3 bg-lsc-rose text-white rounded-xl font-medium hover:brightness-90 transition-colors"
        >
          Mark as reviewed
        </button>
      </div>
    );
  }

  const sandboxType = content.sandbox_type || 'code';

  const checkAnswer = () => {
    let correct = false;

    switch (sandboxType) {
      case 'code':
        // Simple output matching - in production, this would run in a secure sandbox
        correct = userInput.trim().toLowerCase().includes(content.expected_output?.toLowerCase() || '');
        break;
      case 'prompt':
        // Check if prompt includes key elements
        const promptLower = userInput.toLowerCase();
        correct = content.expected_output?.split(',').every(keyword =>
          promptLower.includes(keyword.trim().toLowerCase())
        ) || false;
        break;
      case 'fill_blank':
        correct = content.blanks?.every(blank =>
          fillBlankAnswers[blank.id]?.toLowerCase() === blank.answer.toLowerCase()
        ) || false;
        break;
      case 'matching':
        correct = content.pairs?.every(pair =>
          matchingSelections[pair.left] === pair.right
        ) || false;
        break;
    }

    setIsCorrect(correct);
    if (correct) {
      onComplete();
    }
  };

  const resetSandbox = () => {
    setUserInput(content.initial_code || '');
    setOutput(null);
    setIsCorrect(null);
    setShowHint(0);
    setMatchingSelections({});
    setFillBlankAnswers({});
  };

  return (
    <div className="p-6 md:p-8">
      {content.instructions && (
        <div className="mb-6 p-4 bg-status-info-50 dark:bg-status-info-900/20 rounded-xl border border-status-info-200 dark:border-status-info-800">
          <h4 className="font-medium text-status-info-800 dark:text-status-info-300 mb-2 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            Instructions
          </h4>
          <p className="text-status-info-700 dark:text-status-info-200 text-sm whitespace-pre-wrap">{content.instructions}</p>
        </div>
      )}

      {sandboxType === 'code' && (
        <div className="space-y-4">
          <div className="bg-earth-900 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-earth-800 border-b border-earth-700">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Code Editor</span>
            </div>
            <textarea
              value={userInput || content.initial_code || ''}
              onChange={e => setUserInput(e.target.value)}
              className="w-full h-48 p-4 bg-transparent text-status-success-400 font-mono text-sm resize-none focus:outline-none"
              placeholder={t('lessonViewer.writeYourCodeHere')}
              spellCheck={false}
            />
          </div>

          {output !== null && (
            <div className="bg-earth-800 rounded-xl p-4">
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 block mb-2">Output:</span>
              <pre className="text-sm text-lsc-cream font-mono">{output}</pre>
            </div>
          )}
        </div>
      )}

      {sandboxType === 'prompt' && (
        <div className="space-y-4">
          {content.prompt_template && (
            <div className="p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl">
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 block mb-2">Template:</span>
              <p className="text-sm text-lsc-dark dark:text-lsc-cream font-mono">{content.prompt_template}</p>
            </div>
          )}
          <textarea
            value={userInput}
            onChange={e => setUserInput(e.target.value)}
            className="w-full h-32 p-4 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream resize-none"
            placeholder={t('lessonViewer.writeYourPromptHere')}
          />
        </div>
      )}

      {sandboxType === 'fill_blank' && content.blanks && (
        <div className="space-y-4">
          {content.blanks.map((blank, idx) => (
            <div key={blank.id} className="flex items-center gap-3">
              <span className="text-lsc-dark dark:text-lsc-cream">{idx + 1}.</span>
              {blank.options ? (
                <select
                  value={fillBlankAnswers[blank.id] || ''}
                  onChange={e => setFillBlankAnswers(prev => ({ ...prev, [blank.id]: e.target.value }))}
                  className="flex-1 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="">Select an answer...</option>
                  {blank.options.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={fillBlankAnswers[blank.id] || ''}
                  onChange={e => setFillBlankAnswers(prev => ({ ...prev, [blank.id]: e.target.value }))}
                  className="flex-1 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                  placeholder={t('placeholder.lessonViewer.typeYourAnswer')}
                />
              )}
            </div>
          ))}
        </div>
      )}

      {sandboxType === 'matching' && content.pairs && content.pairs.length > 0 && (
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Match these:</span>
            {content.pairs.map(pair => (
              <div key={pair.left} className="p-3 bg-lsc-cream dark:bg-lsc-brown rounded-lg">
                <span className="text-lsc-dark dark:text-lsc-cream">{pair.left}</span>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">With:</span>
            {content.pairs && content.pairs.map(pair => (
              <select
                key={pair.left}
                value={matchingSelections[pair.left] || ''}
                onChange={e => setMatchingSelections(prev => ({ ...prev, [pair.left]: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              >
                <option value="">Select match...</option>
                {content.pairs!.map(p => (
                  <option key={p.right} value={p.right}>{p.right}</option>
                ))}
              </select>
            ))}
          </div>
        </div>
      )}

      {content.hints && content.hints.length > 0 && (
        <div className="mt-4">
          {showHint > 0 && (
            <div className="p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg border border-status-warning-200 dark:border-status-warning-800 mb-3">
              <span className="text-xs text-status-warning-600 dark:text-status-warning-400 block mb-1">Hint {showHint}:</span>
              <p className="text-sm text-status-warning-700 dark:text-status-warning-300">{content.hints[showHint - 1]}</p>
            </div>
          )}
          {showHint < content.hints.length && (
            <button
              onClick={() => setShowHint(prev => prev + 1)}
              className="text-sm text-lsc-rose hover:underline"
            >
              {showHint === 0 ? 'Need a hint?' : 'Show another hint'}
            </button>
          )}
        </div>
      )}

      {isCorrect !== null && (
        <div className={`mt-4 p-4 rounded-xl ${
          isCorrect
            ? 'bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800'
            : 'bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800'
        }`}>
          <p className={`font-medium ${isCorrect ? 'text-status-success-700 dark:text-status-success-300' : 'text-status-danger-700 dark:text-status-danger-300'}`}>
            {isCorrect ? 'Correct! Well done!' : 'Not quite right. Try again!'}
          </p>
        </div>
      )}

      <div className="mt-6 flex gap-3">
        <button
          onClick={checkAnswer}
          className="flex-1 py-3 bg-lsc-rose text-white rounded-xl font-medium hover:brightness-90 transition-colors"
        >
          Check Answer
        </button>
        <button
          onClick={resetSandbox}
          className="px-4 py-3 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl font-medium hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80 transition-colors"
        >
          Reset
        </button>
      </div>
    </div>
  );
}
