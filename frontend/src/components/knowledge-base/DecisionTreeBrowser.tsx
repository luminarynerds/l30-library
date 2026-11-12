/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, ChevronLeft, Undo2 } from 'lucide-react';
import api from '../../api/api';
import { useTranslation } from '@/i18n'
import { useFocusAndAnnounce } from '@/hooks/useFocusAndAnnounce'

interface TreeNode {
  id: string;
  question: string;
  yes_next: string | { action: string; result: string };
  no_next: string | { action: string; result: string };
}

interface DecisionTree {
  id: number;
  title: string;
  description: string;
  category: string;
  tree_data: {
    root_node: string;
    nodes: Record<string, TreeNode>;
  };
  view_count: number;
  created_at: string;
}

export default function DecisionTreeBrowser() {
  const { t } = useTranslation()
  const [selectedTreeId, setSelectedTreeId] = useState<number | null>(null);
  const [currentNodeId, setCurrentNodeId] = useState<string>('');
  // History stack of node ids visited to reach the current node (root excluded
  // until you advance). Only real (string) node ids are ever pushed; terminal
  // result objects are shown inline and never enter the stack.
  const [history, setHistory] = useState<string[]>([]);

  const questionHeadingRef = useRef<HTMLHeadingElement>(null);

  const { data: trees, isLoading } = useQuery({
    queryKey: ['decision-trees'],
    queryFn: async () => {
      return await api.get<DecisionTree[]>('/staff-knowledge/decision-trees');
    },
  });

  const { data: selectedTree } = useQuery({
    queryKey: ['decision-tree', selectedTreeId],
    queryFn: async () => {
      if (!selectedTreeId) return null;
      return await api.get<DecisionTree>(`/staff-knowledge/decision-trees/${selectedTreeId}`);
    },
    enabled: !!selectedTreeId,
  });

  const inTreeView = !!(selectedTree && currentNodeId);
  const currentNode = inTreeView ? selectedTree!.tree_data.nodes[currentNodeId] : undefined;

  // Announce + focus the new question (or the completion message) on every
  // node change. Hooks must run before any early return, so the ref simply
  // no-ops on the list view where it is unmounted.
  const announceMessage = !inTreeView
    ? ''
    : currentNode
      ? `${t('components.knowledgeBase.decisionTreeBrowser.question', 'Question')}: ${currentNode.question}`
      : t('components.knowledgeBase.decisionTreeBrowser.complete', 'Decision process complete');
  useFocusAndAnnounce(questionHeadingRef, announceMessage, currentNodeId);

  const backToTrees = () => {
    setSelectedTreeId(null);
    setCurrentNodeId('');
    setHistory([]);
  };

  const openTree = (tree: DecisionTree) => {
    setSelectedTreeId(tree.id);
    setCurrentNodeId(tree.tree_data.root_node);
    setHistory([]);
  };

  // Advance only when the chosen branch points to a real node id. Terminal
  // result objects are rendered inline below, so their buttons no-op.
  const choose = (next: string | { action: string; result: string }) => {
    if (typeof next === 'string') {
      setHistory(prev => [...prev, currentNodeId]);
      setCurrentNodeId(next);
    }
  };

  const goBackOneStep = () => {
    setHistory(prev => {
      if (prev.length === 0) return prev;
      const copy = [...prev];
      const last = copy.pop() as string;
      setCurrentNodeId(last);
      return copy;
    });
  };

  if (inTreeView) {
    if (!currentNode) {
      return (
        <div className="max-w-3xl mx-auto">
          <button
            onClick={backToTrees}
            className="flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light mb-6 font-medium"
          >
            <ChevronLeft className="w-4 h-4" aria-hidden="true" />
            {t('components.knowledgeBase.decisionTreeBrowser.backToTrees', 'Back to Trees')}
          </button>
          <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-lg p-8 text-center">
            <p ref={questionHeadingRef} tabIndex={-1} className="text-status-success-800 dark:text-status-success-300 text-lg font-medium outline-none">
              {t('components.knowledgeBase.decisionTreeBrowser.decisionProcessComplete', 'Decision process complete!')}
            </p>
          </div>
        </div>
      );
    }

    const isYesResult = typeof currentNode.yes_next === 'object';
    const isNoResult = typeof currentNode.no_next === 'object';
    // Step number: number of nodes already visited + the current one.
    const stepNumber = history.length + 1;

    return (
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <button
              onClick={backToTrees}
              className="flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light font-medium"
            >
              <ChevronLeft className="w-4 h-4" aria-hidden="true" />
              {t('components.knowledgeBase.decisionTreeBrowser.backToTrees', 'Back to Trees')}
            </button>
            {history.length > 0 && (
              <button
                onClick={goBackOneStep}
                className="flex items-center gap-2 text-earth-600 dark:text-earth-400 hover:text-lsc-rose dark:hover:text-lsc-rose-light font-medium"
              >
                <Undo2 className="w-4 h-4" aria-hidden="true" />
                {t('components.knowledgeBase.decisionTreeBrowser.backOneStep', 'Back one step')}
              </button>
            )}
          </div>
          <span className="text-sm font-medium text-earth-600 dark:text-earth-400">
            {`${t('components.knowledgeBase.decisionTreeBrowser.step', 'Step')} ${stepNumber}`}
          </span>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-8">
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-8">
            {selectedTree!.title}
          </h2>

          <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-8 mb-8 text-center">
            <p ref={questionHeadingRef} tabIndex={-1} className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream mb-6 outline-none">
              {currentNode.question}
            </p>

            <div className="flex gap-4 justify-center">
              <button
                onClick={() => choose(currentNode.yes_next)}
                aria-label={t('components.knowledgeBase.decisionTreeBrowser.answerYes', 'Answer Yes')}
                className="flex items-center gap-2 px-8 py-3 bg-status-success-600 hover:bg-status-success-700 text-white rounded-lg font-medium transition"
              >
                <span aria-hidden="true">✓</span>
                {t('components.knowledgeBase.decisionTreeBrowser.yes', 'Yes')}
              </button>
              <button
                onClick={() => choose(currentNode.no_next)}
                aria-label={t('components.knowledgeBase.decisionTreeBrowser.answerNo', 'Answer No')}
                className="flex items-center gap-2 px-8 py-3 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-lg font-medium transition"
              >
                <span aria-hidden="true">✕</span>
                {t('components.knowledgeBase.decisionTreeBrowser.no', 'No')}
              </button>
            </div>
          </div>

          {isYesResult && typeof currentNode.yes_next === 'object' && (
            <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-lg p-6 mb-6">
              <h3 className="font-serif font-semibold text-status-success-900 dark:text-status-success-200 mb-2">{t('components.knowledgeBase.decisionTreeBrowser.resultYesPath', 'Result (Yes path):')}</h3>
              <p className="text-status-success-800 dark:text-status-success-300">{currentNode.yes_next.result}</p>
            </div>
          )}

          {isNoResult && typeof currentNode.no_next === 'object' && (
            <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-6">
              <h3 className="font-serif font-semibold text-status-danger-900 dark:text-status-danger-200 mb-2">{t('components.knowledgeBase.decisionTreeBrowser.resultNoPath', 'Result (No path):')}</h3>
              <p className="text-status-danger-800 dark:text-status-danger-300">{currentNode.no_next.result}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      {isLoading && (
        <div className="text-center py-12" role="status">
          <div className="inline-block motion-safe:animate-spin rounded-full h-8 w-8 border-b-2 border-lsc-rose"></div>
          <span className="sr-only">{t('components.knowledgeBase.decisionTreeBrowser.loading', 'Loading decision trees...')}</span>
        </div>
      )}

      {!isLoading && (!trees || trees.length === 0) && (
        <div className="text-center py-12 bg-earth-50 dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700">
          <p className="text-earth-600 dark:text-earth-400">{t('components.knowledgeBase.decisionTreeBrowser.noDecisionTreesAvailableYet')}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {trees?.map(tree => (
          <button
            key={tree.id}
            type="button"
            onClick={() => openTree(tree)}
            className="text-left w-full bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-6 hover:shadow-lg transition cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
          >
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              {tree.title}
            </h3>
            {tree.description && (
              <p className="text-earth-600 dark:text-earth-400 text-sm mb-4 line-clamp-2" title={tree.description}>
                {tree.description}
              </p>
            )}
            <div className="flex items-center justify-between text-sm text-earth-600 dark:text-earth-400">
              <span>{tree.category}</span>
              <ChevronRight className="w-4 h-4" aria-hidden="true" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
