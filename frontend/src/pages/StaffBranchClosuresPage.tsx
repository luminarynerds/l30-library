/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useState } from 'react'
import { Building2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { AdminShell } from '../components/shells/AdminShell'
import { useAuth } from '../contexts/AuthContext'
import { useBranchOptions } from '@/hooks/useBranchOptions'
import { listBranchClosures, type BranchClosure } from '@/api/branch-api'
import { ClosuresList } from '@/components/closure-management/ClosuresList'
import { CloseTodayButton } from '@/components/closure-management/CloseTodayButton'

// ClosuresList/ClosureManagementPanel declare their own local BranchClosure
// shape (optional string fields, no null) that predates branch-api.ts's
// generated-schema-accurate type (nullable fields). Normalize at this
// boundary rather than change either "complete" component.
function forClosuresList(closures: BranchClosure[]) {
  return closures.map((c) => ({
    ...c,
    start_time: c.start_time ?? undefined,
    end_time: c.end_time ?? undefined,
    description: c.description ?? undefined,
    closure_documentation: c.closure_documentation ?? undefined,
    reopening_announcement: c.reopening_announcement ?? undefined,
    created_by_id: c.created_by_id ?? undefined,
  }))
}

export default function StaffBranchClosuresPage(): React.ReactElement {
  const { user } = useAuth()
  const { branches, loading: branchesLoading } = useBranchOptions()
  const [branchId, setBranchId] = useState<number | null>(user?.home_branch_id ?? null)
  const [closures, setClosures] = useState<BranchClosure[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // Default to the staff member's home branch; fall back to the first branch
  // once the list loads if they don't have one on file.
  useEffect(() => {
    if (branchId == null && branches.length > 0) {
      setBranchId(branches[0]?.id ?? null)
    }
  }, [branches, branchId])

  const loadClosures = useCallback(async () => {
    if (branchId == null) return
    setIsLoading(true)
    try {
      const data = await listBranchClosures(branchId)
      setClosures(data)
    } catch {
      toast.error('Failed to load closures')
    } finally {
      setIsLoading(false)
    }
  }, [branchId])

  useEffect(() => {
    loadClosures()
  }, [loadClosures])

  const selectedBranch = branches.find((b) => b.id === branchId)

  return (
    <AdminShell
      title="Branch Closures"
      subtitle="Scheduled and same-day closures for a branch"
      icon={<Building2 className="h-8 w-8" />}
      {...(branchId != null && {
        actions: (
          <CloseTodayButton
            branchId={branchId}
            onSuccess={() => {
              toast.success('Branch closed for today')
              loadClosures()
            }}
            onError={(message) => toast.error(message)}
          />
        ),
      })}
    >
      <div className="space-y-6">
        {branches.length > 1 ? (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <label
              htmlFor="closures-branch-id"
              className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
            >
              Branch
            </label>
            <select
              id="closures-branch-id"
              value={branchId ?? ''}
              onChange={(e) => setBranchId(e.target.value ? Number(e.target.value) : null)}
              disabled={branchesLoading}
              className="w-64 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream px-3 py-2 text-sm"
            >
              {branches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>
        ) : (
          selectedBranch && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{selectedBranch.name}</p>
          )
        )}

        <ClosuresList
          closures={forClosuresList(closures)}
          isLoading={isLoading || branchesLoading}
          onRefresh={loadClosures}
        />
      </div>
    </AdminShell>
  )
}
