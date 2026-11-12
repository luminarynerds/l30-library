/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { FamilyTreeNode, Relationship } from '@/api/genealogy-research-api';
import { useTranslation } from '@/i18n';

function computeGenerations(nodes: FamilyTreeNode[], _relationships: Relationship[]): number[][] {
  if (nodes.length === 0) return [];

  const nodeMap = new Map<number, FamilyTreeNode>();
  nodes.forEach(n => nodeMap.set(n.person.id, n));

  const generation = new Map<number, number>();
  const visited = new Set<number>();

  function assignGen(id: number, gen: number) {
    if (visited.has(id)) return;
    visited.add(id);
    const current = generation.get(id);
    if (current === undefined || gen < current) {
      generation.set(id, gen);
    }
    const node = nodeMap.get(id);
    if (!node) return;
    node.children.forEach(childId => assignGen(childId, gen + 1));
    node.parents.forEach(parentId => assignGen(parentId, gen - 1));
  }

  nodes.forEach(n => assignGen(n.person.id, 0));

  const minGen = Math.min(...Array.from(generation.values()));
  const adjusted = new Map<number, number>();
  generation.forEach((gen, id) => adjusted.set(id, gen - minGen));

  const maxGen = Math.max(...Array.from(adjusted.values()));
  const result: number[][] = Array.from({ length: maxGen + 1 }, () => []);
  adjusted.forEach((gen, id) => (result[gen] ?? []).push(id));

  return result;
}

interface TreeVisualizationProps {
  nodes: FamilyTreeNode[];
  relationships: Relationship[];
  selectedNodeId: number | null;
  onSelectNode: (id: number) => void;
}

export function TreeVisualization({
  nodes,
  relationships,
  selectedNodeId,
  onSelectNode,
}: TreeVisualizationProps) {
  const { t } = useTranslation();
  const generations = computeGenerations(nodes, relationships);

  return (
    <div className="overflow-x-auto min-h-[300px]">
      <div className="space-y-8 min-w-full md:min-w-[600px] py-4">
        {generations.map((gen, genIdx) => (
          <div key={genIdx}>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2 font-medium">
              {genIdx === 0 ? 'Earliest Generation' : genIdx === generations.length - 1 ? 'Latest Generation' : `Generation ${genIdx + 1}`}
            </div>
            <div className="flex gap-4 flex-wrap">
              {gen.map(nodeId => {
                const node = nodes.find(n => n.person.id === nodeId);
                if (!node) return null;
                const { person } = node;
                const isSelected = selectedNodeId === person.id;
                const genderBorder = person.gender === 'male' ? 'border-l-sky-400' :
                                    person.gender === 'female' ? 'border-l-emerald-400' : 'border-l-amber-400';
                return (
                  <button
                    key={person.id}
                    onClick={() => onSelectNode(person.id)}
                    className={`border-l-4 ${genderBorder} text-left p-3 rounded-r-lg transition-all min-w-[140px] max-w-[180px] ${
                      isSelected
                        ? 'bg-status-warning-50 dark:bg-status-warning-900/20 ring-2 ring-status-warning-400'
                        : 'bg-earth-50 dark:bg-earth-700/50 hover:bg-earth-100 dark:hover:bg-earth-700'
                    }`}
                  >
                    <p className="font-semibold text-xs text-lsc-dark dark:text-lsc-cream leading-tight">
                      {person.given_names} {person.surname || ''}
                    </p>
                    <p className="text-[10px] text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                      {person.birth_date || '?'} – {person.is_living ? 'Living' : (person.death_date || '?')}
                    </p>
                    <div className="flex gap-1 mt-1.5 flex-wrap">
                      {node.parents.length > 0 && (
                        <span className="text-[9px] px-1 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded">
                          {node.parents.length}P
                        </span>
                      )}
                      {node.children.length > 0 && (
                        <span className="text-[9px] px-1 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded">
                          {node.children.length}C
                        </span>
                      )}
                      {node.spouses.length > 0 && (
                        <span className="text-[9px] px-1 py-0.5 bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300 rounded">
                          {node.spouses.length}S
                        </span>
                      )}
                      {node.siblings.length > 0 && (
                        <span className="text-[9px] px-1 py-0.5 bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-300 rounded">
                          {node.siblings.length}Sib
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-4 text-[10px] text-lsc-dark/70 dark:text-lsc-cream/70 mt-4 pt-3 border-t border-earth-100 dark:border-earth-700">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-sky-400" /> Male</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-emerald-400" /> Female</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-amber-400" /> Not recorded</span>
        <span className="flex items-center gap-1">{t('familyTree.pParentsCChildrenS')}</span>
      </div>
    </div>
  );
}

export function RelationshipBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    parent: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300',
    child: 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light',
    spouse: 'bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300',
    sibling: 'bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-300',
    partner: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300',
  };
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${colors[type] || 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
      {({'parent': 'Parent', 'child': 'Child', 'spouse': 'Spouse / partner', 'sibling': 'Sibling', 'partner': 'Partner'})[type] ?? type}
    </span>
  );
}
