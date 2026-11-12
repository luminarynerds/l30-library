/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { researchProjectsApi, type ResearchProject } from '@/api/genealogy-research-api'

export function useGenealogyProjects() {
  const [projects, setProjects] = useState<ResearchProject[]>([])
  const [selectedProject, setSelectedProject] = useState<ResearchProject | null>(null)
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)

  async function loadProjects() {
    try {
      setLoading(true)
      const data = await researchProjectsApi.list()
      setProjects(data)
    } catch {
      toast.error('Failed to load research projects')
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    void loadProjects()
  }, [])

  async function handleCreateProject(name: string, description: string, isPublic: boolean) {
    try {
      const project = await researchProjectsApi.create({ name, description, is_public: isPublic })
      setProjects(prev => [project, ...prev])
      setSelectedProject(project)
      setShowCreateModal(false)
      toast.success('Research project created')
    } catch {
      toast.error('Failed to create project')
    }
  }

  return {
    projects,
    selectedProject,
    setSelectedProject,
    loading,
    showCreateModal,
    setShowCreateModal,
    handleCreateProject,
  }
}
