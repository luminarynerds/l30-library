/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { Suspense } from 'react'
import { Route, useParams } from 'react-router-dom'
import { withAuth, withFeature } from './routeGuards'
import { lazyWithRetry } from '../utils/lazyWithRetry'

const GenealogyPage = lazyWithRetry(() => import('../pages/GenealogyPage'), 'genealogy-genealogy-page')
const GenealogyTrainingPage = lazyWithRetry(() => import('../pages/GenealogyTrainingPage'), 'genealogy-genealogy-training-page')
const GenealogyInquiryPage = lazyWithRetry(() => import('../pages/GenealogyInquiryPage'), 'genealogy-genealogy-inquiry-page')
const AskGenealogyPage = lazyWithRetry(() => import('../pages/AskGenealogyPage'), 'genealogy-ask-genealogy-page')
const CommunityArchivesPage = lazyWithRetry(() => import('../pages/CommunityArchivesPage'), 'genealogy-community-archives-page')
const ArchiveSubmissionFormPage = lazyWithRetry(() => import('../pages/ArchiveSubmissionFormPage'), 'genealogy-archive-submission-form-page')
const GenealogyResearchPage = lazyWithRetry(() => import('../pages/GenealogyResearchPage'), 'genealogy-genealogy-research-page')
const FamilyTreePage = lazyWithRetry(() => import('../pages/FamilyTreePage'), 'genealogy-family-tree-page')
const GenealogyDocumentsPage = lazyWithRetry(() => import('../pages/GenealogyDocumentsPage'), 'genealogy-genealogy-documents-page')
const GenealogyDNAPage = lazyWithRetry(() => import('../pages/GenealogyDNAPage'), 'genealogy-genealogy-dna-page')

function InlineRouteFallback(): React.ReactElement {
  return <div className="min-h-[30vh] p-4" role="status" aria-live="polite">Loading...</div>
}

function FamilyTreePageWrapper(): React.ReactElement {
  const { projectId } = useParams<{ projectId: string }>()
  return (
    <Suspense fallback={<InlineRouteFallback />}>
      <FamilyTreePage projectId={Number(projectId)} />
    </Suspense>
  )
}

function GenealogyDocumentsPageWrapper(): React.ReactElement {
  const { projectId } = useParams<{ projectId: string }>()
  return (
    <Suspense fallback={<InlineRouteFallback />}>
      <GenealogyDocumentsPage projectId={Number(projectId)} />
    </Suspense>
  )
}

function GenealogyDNAPageWrapper(): React.ReactElement {
  const { projectId } = useParams<{ projectId: string }>()
  return (
    <Suspense fallback={<InlineRouteFallback />}>
      <GenealogyDNAPage projectId={Number(projectId)} />
    </Suspense>
  )
}

export function renderGenealogyRoutesFragment(): React.ReactElement {
  return (
    <>
      <Route path="genealogy" element={withFeature('genealogy_enabled', <GenealogyPage />)} />
      <Route path="genealogy/training" element={withFeature('genealogy_enabled', <GenealogyTrainingPage />)} />
      <Route path="genealogy/inquiry" element={withFeature('genealogy_enabled', <GenealogyInquiryPage />)} />
      <Route path="genealogy/ask-genealogist" element={withFeature('genealogy_enabled', <AskGenealogyPage />)} />
      <Route path="genealogy/archives" element={withFeature('genealogy_enabled', <CommunityArchivesPage />)} />
      <Route path="genealogy/archives/submit" element={withFeature('genealogy_enabled', <ArchiveSubmissionFormPage />)} />
      <Route path="genealogy/research" element={withFeature('genealogy_enabled', withAuth(<GenealogyResearchPage />))} />
      <Route path="genealogy/research/projects/:projectId/tree" element={withFeature('genealogy_enabled', withAuth(<FamilyTreePageWrapper />))} />
      <Route path="genealogy/research/projects/:projectId/documents" element={withFeature('genealogy_enabled', withAuth(<GenealogyDocumentsPageWrapper />))} />
      <Route path="genealogy/research/projects/:projectId/dna" element={withFeature('genealogy_enabled', withAuth(<GenealogyDNAPageWrapper />))} />
    </>
  )
}
