/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useAuth } from '../../contexts/AuthContext'
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import DocumentsSection from '../../components/board/DocumentsSection'
import PageContainer from '@/components/layout/PageContainer'

export default function BoardDocumentsPage() {
  const { token, user } = useAuth()
  const userRole = user?.role || 'patron'

  return (
    <>
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      <PageContainer className="py-8">
        <Link
          to="/board"
          className="inline-flex items-center gap-2 text-lsc-rose hover:text-lsc-rose/80 mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Board
        </Link>

        <DocumentsSection token={token} userRole={userRole} />
      </PageContainer>
    </div>
  </>
  )
}
