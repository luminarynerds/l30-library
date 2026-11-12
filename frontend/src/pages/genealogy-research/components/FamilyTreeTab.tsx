/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  GitBranch, Plus, Loader,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface GenealogyPerson {
  id: number;
  given_names: string;
  surname?: string;
  gender?: string;
  is_living?: boolean;
  birth_date?: string;
  death_date?: string;
  birth_place?: string;
  death_place?: string;
  occupation?: string;
}

interface TreeNode {
  person: GenealogyPerson;
  parents: unknown[];
  children: unknown[];
  spouses: unknown[];
}


function PersonCard({ person, parentCount, childCount, spouseCount }: {
  person: GenealogyPerson
  parentCount: number
  childCount: number
  spouseCount: number
}) {
  const genderColor = person.gender === 'male' ? 'border-l-sky-400' :
                      person.gender === 'female' ? 'border-l-emerald-400' :
                      person.gender === 'nonbinary' ? 'border-l-violet-400' : 'border-l-amber-400'

  return (
    <div className={`border-l-4 ${genderColor} p-4 bg-earth-50 dark:bg-earth-700/50 rounded-r-lg`}>
      <div className="flex items-center gap-2 mb-1">
        <p className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream">
          {person.given_names} {person.surname || ''}
        </p>
        {person.is_living && (
          <span className="text-xs px-1.5 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded">Living</span>
        )}
      </div>
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        {person.birth_date || '?'} &ndash; {person.is_living ? '' : (person.death_date || '?')}
      </p>
      <div className="flex gap-3 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        {parentCount > 0 && <span>{parentCount} parent{parentCount > 1 ? 's' : ''}</span>}
        {childCount > 0 && <span>{childCount} child{childCount > 1 ? 'ren' : ''}</span>}
        {spouseCount > 0 && <span>{spouseCount} spouse{spouseCount > 1 ? 's' : ''}</span>}
      </div>
    </div>
  )
}

function AddPersonModal({ projectId, onClose, onCreated }: {
  projectId: number
  onClose: () => void
  onCreated: () => void
}) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    given_names: '',
    surname: '',
    birth_date: '',
    birth_place: '',
    death_date: '',
    death_place: '',
    gender: '' as string,
    is_living: false,
    occupation: '',
  })
  const [saving, setSaving] = useState(false)

  async function handleSubmit() {
    if (!formData.given_names.trim()) return
    try {
      setSaving(true)
      const { personsApi } = await import('@/api/genealogy-research-api')
      await personsApi.create(projectId, {
        ...formData,
        ...(formData.gender ? { gender: formData.gender } : {}),
      } as Record<string, unknown>)
      toast.success(t('toast.familyTreeTab.personAdded'))
      onCreated()
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToAddPerson'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Add Person">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="font-serif text-xl font-bold mb-4 text-lsc-dark dark:text-lsc-cream">Add Person</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Given Names *</label>
              <input type="text" value={formData.given_names} onChange={e => setFormData(p => ({ ...p, given_names: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Surname</label>
              <input type="text" value={formData.surname} onChange={e => setFormData(p => ({ ...p, surname: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Gender</label>
            <select value={formData.gender} onChange={e => setFormData(p => ({ ...p, gender: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm">
              <option value="">Not recorded</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="nonbinary">Nonbinary</option>
              <option value="other">Another gender / not listed</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Birth Date</label>
              <input type="text" value={formData.birth_date} onChange={e => setFormData(p => ({ ...p, birth_date: e.target.value }))}
                placeholder={t('placeholder.familyTree.eg15Mar1845')} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Birth Place</label>
              <input type="text" value={formData.birth_place} onChange={e => setFormData(p => ({ ...p, birth_place: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={formData.is_living} onChange={e => setFormData(p => ({ ...p, is_living: e.target.checked }))} className="rounded" />
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Person is living</span>
          </label>
          {!formData.is_living && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Death Date</label>
                <input type="text" value={formData.death_date} onChange={e => setFormData(p => ({ ...p, death_date: e.target.value }))}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Death Place</label>
                <input type="text" value={formData.death_place} onChange={e => setFormData(p => ({ ...p, death_place: e.target.value }))}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
              </div>
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Occupation</label>
            <input type="text" value={formData.occupation} onChange={e => setFormData(p => ({ ...p, occupation: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-earth-600 hover:text-earth-800 dark:text-earth-300">Cancel</button>
          <button onClick={handleSubmit} disabled={!formData.given_names.trim() || saving}
            className="px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 disabled:opacity-50">
            {saving ? 'Adding...' : 'Add Person'}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

export default function FamilyTreeTab({ projectId }: { projectId: number }) {
  const { t } = useTranslation();
  const [persons, setPersons] = useState<TreeNode[]>([])
  const [_relationships, setRelationships] = useState<unknown[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddPerson, setShowAddPerson] = useState(false)

  useEffect(() => {
    loadTree()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  async function loadTree() {
    try {
      setLoading(true)
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { personsApi: _personsApi, familyTreeApi } = await import('@/api/genealogy-research-api')
      const data = await familyTreeApi.get(projectId)
      setPersons(data.nodes || [])
      setRelationships(data.relationships || [])
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToLoadFamilyTree'))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin" /></div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Family Tree ({persons.length} people)
        </h2>
        <button
          onClick={() => setShowAddPerson(true)}
          className="flex items-center gap-2 px-3 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 text-sm"
        >
          <Plus className="w-4 h-4" />
          Add Person
        </button>
      </div>

      {persons.length === 0 ? (
        <div className="text-center py-16 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <GitBranch className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('genealogyResearchPageContent.yourFamilyTreeIsEmpty')}</p>
          <button
            onClick={() => setShowAddPerson(true)}
            className="px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700"
          >
            Add First Person
          </button>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          {/* Tree Visualization */}
          <div className="p-6 min-h-[500px]">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {persons.map((node) => (
                <PersonCard
                  key={node.person.id}
                  person={node.person}
                  parentCount={node.parents.length}
                  childCount={node.children.length}
                  spouseCount={node.spouses.length}
                />
              ))}
            </div>
          </div>

          {/* Legend */}
          <div className="border-t border-lsc-border dark:border-earth-700 px-6 py-3 bg-earth-50 dark:bg-earth-900/50">
            <div className="flex gap-6 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-sky-400" /> Male
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-emerald-400" /> Female
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-violet-400" /> Nonbinary
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-amber-400" /> Not specified
              </span>
            </div>
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
    </div>
  )
}
