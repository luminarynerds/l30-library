/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import ConfirmDialog from '@/components/ConfirmDialog'
import { useState, useEffect, useCallback } from 'react'
import { GitBranch, Plus, X, Loader, Link2, User } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  personsApi,
  relationshipsApi,
  familyTreeApi,
  type Person,
  type PersonSummary,
  type FamilyTreeNode,
  type Relationship,
  type TimelineEvent,
} from '@/api/genealogy-research-api'
import { useTranslation } from '@/i18n'
import { TreeVisualization, RelationshipBadge } from '@/components/family-tree/TreeVisualization'
import { PersonDetailPanel } from '@/components/family-tree/PersonDetailPanel'
import { AddPersonModal } from '@/components/family-tree/AddPersonModal'
import { EditPersonModal } from '@/components/family-tree/EditPersonModal'
import { AddRelationshipModal } from '@/components/family-tree/AddRelationshipModal'
import { AddTimelineEventModal } from '@/components/family-tree/AddTimelineEventModal'

interface FamilyTreePageProps {
  projectId: number
}

export default function FamilyTreePage({ projectId }: FamilyTreePageProps) {
  const { t } = useTranslation()
  const [tree, setTree] = useState<{ nodes: FamilyTreeNode[]; relationships: Relationship[]; person_count: number } | null>(null)
  const [persons, setPersons] = useState<PersonSummary[]>([])
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [showAddPerson, setShowAddPerson] = useState(false)
  const [showAddRelationship, setShowAddRelationship] = useState(false)
  const [showPersonDetail, setShowPersonDetail] = useState(false)
  const [editingPerson, setEditingPerson] = useState<Person | null>(null)
  const [personTimeline, setPersonTimeline] = useState<TimelineEvent[]>([])
  const [timelineLoading, setTimelineLoading] = useState(false)
  const [showAddEvent, setShowAddEvent] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingDeletePersonId, setPendingDeletePersonId] = useState<number | null>(null)

  const loadTree = useCallback(async () => {
    try {
      setLoading(true)
      const [treeData, personsData] = await Promise.all([
        familyTreeApi.get(projectId),
        personsApi.list(projectId),
      ])
      setTree(treeData as { nodes: FamilyTreeNode[]; relationships: Relationship[]; person_count: number })
      setPersons(personsData as PersonSummary[])
    } catch {
      toast.error(t('familyTree.failedToLoadFamilyTree'))
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  useEffect(() => {
    loadTree()
  }, [loadTree])

  async function loadPersonDetail(personId: number) {
    try {
      const [personData, timelineData] = await Promise.all([
        personsApi.get(projectId, personId),
        personsApi.getTimeline(projectId, personId),
      ])
      setSelectedPerson(personData as Person)
      const timeline = timelineData as { events: TimelineEvent[] }
      setPersonTimeline(timeline.events || [])
      setShowPersonDetail(true)
    } catch {
      toast.error(t('familyTree.failedToLoadPersonDetails'))
    }
  }

  function handleDeletePerson(personId: number) {
    setPendingDeletePersonId(personId)
    setConfirmOpen(true)
  }

  async function handleDeletePersonConfirm() {
    if (pendingDeletePersonId === null) return
    setConfirmOpen(false)
    try {
      await personsApi.delete(projectId, pendingDeletePersonId)
      toast.success(t('familyTree.personRemovedFromTree'))
      setShowPersonDetail(false)
      setSelectedPerson(null)
      setSelectedNodeId(null)
      loadTree()
    } catch {
      toast.error(t('familyTree.failedToDeletePerson'))
    } finally {
      setPendingDeletePersonId(null)
    }
  }

  async function handleDeleteRelationship(relId: number) {
    try {
      await relationshipsApi.delete(projectId, relId)
      toast.success(t('toast.familyTree.relationshipRemoved'))
      loadTree()
    } catch {
      toast.error(t('familyTree.failedToRemoveRelationship'))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader className="w-8 h-8 motion-safe:animate-spin text-status-warning-600" />
      </div>
    )
  }

  const nodes = tree?.nodes || []
  const relationships = tree?.relationships || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-status-warning-500" />
            Family Tree
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {nodes.length} {nodes.length === 1 ? 'person' : 'people'} &bull; {relationships.length} relationships
          </p>
        </div>
        <div className="flex gap-2">
          {selectedNodeId && (
            <button
              onClick={() => setShowAddRelationship(true)}
              className="flex items-center gap-2 px-3 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 text-sm"
            >
              <Link2 className="w-4 h-4" />
              Add Relationship
            </button>
          )}
          <button
            onClick={() => setShowAddPerson(true)}
            className="flex items-center gap-2 px-3 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 text-sm"
          >
            <Plus className="w-4 h-4" />
            Add Person
          </button>
        </div>
      </div>

      {nodes.length === 0 ? (
        <div className="text-center py-20 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <GitBranch className="w-16 h-16 mx-auto text-earth-300 mb-4" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{t('familyTree.startYourFamilyTree')}</h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6 max-w-sm mx-auto">
            Add your first family member to begin building the tree. You can connect people with parent, child, spouse, and sibling relationships.
          </p>
          <button
            onClick={() => setShowAddPerson(true)}
            className="px-6 py-2.5 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700"
          >
            Add First Person
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
              <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900/50">
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('familyTree.clickAPersonToView')}</p>
              </div>
              <div className="p-4">
                <TreeVisualization
                  nodes={nodes}
                  relationships={relationships}
                  selectedNodeId={selectedNodeId}
                  onSelectNode={(id) => {
                    setSelectedNodeId(id)
                    loadPersonDetail(id)
                  }}
                />
              </div>
            </div>

            {relationships.length > 0 && (
              <div className="mt-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
                <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
                  <Link2 className="w-4 h-4 text-earth-600" />
                  All Relationships
                </h3>
                <div className="space-y-2">
                  {relationships.map(rel => {
                    const person1 = persons.find(p => p.id === rel.person1_id)
                    const person2 = persons.find(p => p.id === rel.person2_id)
                    return (
                      <div key={rel.id} className="flex items-center justify-between py-1.5 px-3 rounded bg-earth-50 dark:bg-earth-700/50 text-sm">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {person1 ? `${person1.given_names} ${person1.surname || ''}`.trim() : `#${rel.person1_id}`}
                          </span>
                          <RelationshipBadge type={rel.relationship_type} />
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {person2 ? `${person2.given_names} ${person2.surname || ''}`.trim() : `#${rel.person2_id}`}
                          </span>
                        </div>
                        <button
                          onClick={() => handleDeleteRelationship(rel.id)}
                          className="p-1 text-status-danger-400 hover:text-status-danger-600 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          <div>
            {selectedPerson && showPersonDetail ? (
              <PersonDetailPanel
                person={selectedPerson}
                timeline={personTimeline}
                timelineLoading={timelineLoading}
                projectId={projectId}
                onEdit={() => setEditingPerson(selectedPerson)}
                onDelete={() => handleDeletePerson(selectedPerson.id)}
                onClose={() => { setShowPersonDetail(false); setSelectedNodeId(null) }}
                onAddEvent={() => setShowAddEvent(true)}
                onTimelineRefresh={async () => {
                  if (selectedPerson) {
                    setTimelineLoading(true)
                    try {
                      const data = await personsApi.getTimeline(projectId, selectedPerson.id)
                      const tl = data as { events: TimelineEvent[] }
                      setPersonTimeline(tl.events || [])
                    } finally {
                      setTimelineLoading(false)
                    }
                  }
                }}
              />
            ) : (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 text-center">
                <User className="w-12 h-12 mx-auto text-earth-300 mb-3" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">{t('familyTree.clickAPersonInThe')}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {showAddPerson && (
        <AddPersonModal
          projectId={projectId}
          onClose={() => setShowAddPerson(false)}
          onCreated={() => { setShowAddPerson(false); loadTree() }}
        />
      )}
      {showAddRelationship && selectedNodeId && (
        <AddRelationshipModal
          projectId={projectId}
          anchorPersonId={selectedNodeId}
          persons={persons}
          onClose={() => setShowAddRelationship(false)}
          onCreated={() => { setShowAddRelationship(false); loadTree() }}
        />
      )}
      {editingPerson && (
        <EditPersonModal
          projectId={projectId}
          person={editingPerson}
          onClose={() => setEditingPerson(null)}
          onSaved={async () => {
            setEditingPerson(null)
            await loadTree()
            if (selectedPerson) {
              await loadPersonDetail(selectedPerson.id)
            }
          }}
        />
      )}
      {showAddEvent && selectedPerson && (
        <AddTimelineEventModal
          projectId={projectId}
          personId={selectedPerson.id}
          onClose={() => setShowAddEvent(false)}
          onCreated={async () => {
            setShowAddEvent(false)
            if (selectedPerson) {
              setTimelineLoading(true)
              try {
                const data = await personsApi.getTimeline(projectId, selectedPerson.id)
                const tl = data as { events: TimelineEvent[] }
                setPersonTimeline(tl.events || [])
              } finally {
                setTimelineLoading(false)
              }
            }
          }}
        />
      )}

      <ConfirmDialog
        isOpen={confirmOpen}
        title="Delete this person?"
        message="This will remove them and all their relationships from the tree."
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={handleDeletePersonConfirm}
        onCancel={() => { setConfirmOpen(false); setPendingDeletePersonId(null) }}
      />
    </div>
  )
}
