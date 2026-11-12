/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState} from 'react'
import {
  GitBranch, FileText, Users, Plus, ChevronRight,
  Loader,
  Globe,
} from 'lucide-react'

import { useGenealogyProjects } from '@/pages/genealogy-research/hooks/useGenealogyProjects'
import { GENEALOGY_TABS, type TabId } from '@/pages/genealogy-research/utils/genealogyTabs'
import { useTranslation} from '@/i18n'
import ProjectDashboardTab from './DashboardTab'
import FamilyTreeTab from './FamilyTreeTab'
import DocumentsTab from './DocumentsTab'
import TimelineTab from './TimelineTab'
import ResearchNotesTab from './NotesTab'
import RecordLinksTab from './DNALinksTab'
import DNATab from './ProfilesTab'
import GuidanceTab from './SuggestionsTab'
import ProjectSearchTab from './SearchTab'
import ProjectSettingsTab from './CollaboratorsTab'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

export default function GenealogyResearchPage() {
  const {
    projects,
    selectedProject,
    setSelectedProject,
    loading,
    showCreateModal,
    setShowCreateModal,
    handleCreateProject,
  } = useGenealogyProjects()
  const [activeTab, setActiveTab] = useState<TabId>('dashboard')

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader className="w-8 h-8 motion-safe:animate-spin text-status-warning-600" />
      </div>
    )
  }

  if (!selectedProject) {
    return (
      <PageContainer width="wide" className="py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Genealogy Research Platform
            </h1>
            <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">
              Collaborative family history research with document management, record linking, and AI-powered guidance.
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 transition-colors"
          >
            <Plus className="w-5 h-5" />
            New Project
          </button>
        </div>

        {projects.length === 0 ? (
          <div className="text-center py-16 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
            <GitBranch className="w-16 h-16 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-4" />
            <h2 className="font-serif text-lg font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              No Research Projects Yet
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6 max-w-md mx-auto">
              Create your first genealogy research project to start building family trees,
              managing documents, and collaborating with others.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-3 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700"
            >
              Create Your First Project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map(project => (
              <button
                key={project.id}
                onClick={() => setSelectedProject(project)}
                className="text-left p-6 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:border-status-warning-400 hover:shadow-lg transition-all"
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-serif font-semibold text-lg text-lsc-dark dark:text-lsc-cream">
                    {project.name}
                  </h3>
                  {project.is_public && (
                    <Globe className="w-4 h-4 text-status-success-500 flex-shrink-0" />
                  )}
                </div>
                {project.description && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 line-clamp-2" title={project.description}>
                    {project.description}
                  </p>
                )}
                <div className="flex gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  <span className="flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {project.person_count} people
                  </span>
                  <span className="flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    {project.document_count} docs
                  </span>
                  <span className="flex items-center gap-1">
                    <GitBranch className="w-3 h-3" />
                    {project.generation_count} gen
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}

        {showCreateModal && (
          <CreateProjectModal
            onClose={() => setShowCreateModal(false)}
            onCreate={handleCreateProject}
          />
        )}
      </PageContainer>
    )
  }

  return (
    <PageContainer width="wide" className="py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => setSelectedProject(null)}
          className="text-sm text-status-warning-600 hover:text-status-warning-700 dark:text-status-warning-300 font-medium"
        >
          All Projects
        </button>
        <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {selectedProject.name}
        </h1>
      </div>

      {/* Tabs */}
      <div className="border-b border-lsc-border dark:border-earth-700 mb-6 overflow-x-auto">
        <nav className="flex gap-1 -mb-px">
          {GENEALOGY_TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'border-status-warning-500 text-status-warning-600 dark:text-status-warning-400'
                  : 'border-transparent text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'dashboard' && <ProjectDashboardTab projectId={selectedProject.id} />}
      {activeTab === 'tree' && <FamilyTreeTab projectId={selectedProject.id} />}
      {activeTab === 'documents' && <DocumentsTab projectId={selectedProject.id} />}
      {activeTab === 'timeline' && <TimelineTab projectId={selectedProject.id} />}
      {activeTab === 'notes' && <ResearchNotesTab projectId={selectedProject.id} />}
      {activeTab === 'record-links' && <RecordLinksTab projectId={selectedProject.id} />}
      {activeTab === 'dna' && <DNATab projectId={selectedProject.id} />}
      {activeTab === 'guidance' && <GuidanceTab projectId={selectedProject.id} />}
      {activeTab === 'search' && <ProjectSearchTab projectId={selectedProject.id} />}
      {activeTab === 'settings' && <ProjectSettingsTab project={selectedProject} onUpdate={p => setSelectedProject(p)} />}
    </PageContainer>
  )
}

function CreateProjectModal({ onClose, onCreate }: {
  onClose: () => void
  onCreate: (name: string, description: string, isPublic: boolean) => void
}) {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isPublic, setIsPublic] = useState(false)

  return (
    <ModalBackdrop onClose={onClose} title="New Research Project">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-lg w-full p-6">
        <h2 className="font-serif text-xl font-bold mb-4 text-lsc-dark dark:text-lsc-cream">
          New Research Project
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Project Name
            </label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={t('placeholder.genealogyResearchContent.egJohnsonFamilyResearch')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
              placeholder={t('genealogyResearchPageContent.briefDescriptionOfYourResearch')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={e => setIsPublic(e.target.checked)}
              className="rounded"
            />
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Make this project publicly viewable
            </span>
          </label>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-earth-600 hover:text-earth-800 dark:text-earth-300">
            Cancel
          </button>
          <button
            onClick={() => onCreate(name, description, isPublic)}
            disabled={!name.trim()}
            className="px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 disabled:opacity-50"
          >
            Create Project
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
