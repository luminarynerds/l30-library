/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Vitest coverage for the cg_lifecycle_001 admin lifecycle UI. The
 * page-level admin-gate (kebab + "New group" button hidden for non-admin)
 * is asserted in ParentConnectionGroupsPage.test.tsx; this file focuses
 * on the modals' internal behaviour: capacity-conflict error rendering,
 * archive notify-toggle, cancel/reschedule alertdialog semantics, and
 * the email-preview pane reflecting patron_message live.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

const { tEcho } = vi.hoisted(() => ({
  tEcho: (key: string, opts?: Record<string, unknown>) =>
    opts ? `${key}|${JSON.stringify(opts)}` : key,
}))
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: tEcho }),
  t: tEcho,
}))

vi.mock('@/lib/sentry-lazy', () => ({ captureException: vi.fn() }))

const { toastSuccess, toastError } = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}))
vi.mock('react-hot-toast', () => ({
  default: { success: toastSuccess, error: toastError },
}))

const {
  createMock,
  updateMock,
  archiveMock,
  listMeetingsMock,
  cancelMeetingMock,
  rescheduleMeetingMock,
} = vi.hoisted(() => ({
  createMock: vi.fn(),
  updateMock: vi.fn(),
  archiveMock: vi.fn(),
  listMeetingsMock: vi.fn(),
  cancelMeetingMock: vi.fn(),
  rescheduleMeetingMock: vi.fn(),
}))
vi.mock('@/api/parent-onboarding-api', () => ({
  createConnectionGroup: createMock,
  updateConnectionGroup: updateMock,
  archiveConnectionGroup: archiveMock,
  listConnectionGroupMeetings: listMeetingsMock,
  cancelConnectionGroupMeeting: cancelMeetingMock,
  rescheduleConnectionGroupMeeting: rescheduleMeetingMock,
}))

const { listBranchesMock } = vi.hoisted(() => ({
  listBranchesMock: vi.fn(),
}))
vi.mock('@/api/branch-api', () => ({
  listBranches: listBranchesMock,
}))

// focus-trap-react is finicky in jsdom; stub for test simplicity.
vi.mock('focus-trap-react', () => ({
  default: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

import {
  ArchiveGroupDialog,
  CancelMeetingDialog,
  CreateGroupModal,
  EditGroupModal,
  MeetingsDrawer,
} from '../ConnectionGroupLifecycleModals'

const group = {
  id: 12,
  name: 'Tuesday Crew',
  description: 'A group',
  group_type: 'first_time_parents' as const,
  max_members: 10,
  current_members: 5,
  is_active: true,
  created_at: '2026-01-01',
  meeting_frequency: 'weekly' as const,
  meeting_day_of_week: 'tuesday',
  meeting_time: '10:00',
  location: 'Community Room A',
  branch_id: 1,
}

function wrap(ui: ReactNode): JSX.Element {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>
}

beforeEach(() => {
  createMock.mockReset()
  updateMock.mockReset()
  archiveMock.mockReset()
  listMeetingsMock.mockReset()
  cancelMeetingMock.mockReset()
  rescheduleMeetingMock.mockReset()
  listBranchesMock.mockReset()
  toastSuccess.mockReset()
  toastError.mockReset()
})


describe('CreateGroupModal', () => {
  it('disables submit until name + branch are filled', async () => {
    listBranchesMock.mockResolvedValue([{ id: 1, name: 'Main' }])
    render(wrap(<CreateGroupModal isOpen onClose={() => {}} />))

    // Find the submit button by its echoed i18n key. The exact label is
    // "parentOnboarding.connectionGroups.admin.create.submit".
    const submit = await screen.findByRole('button', {
      name: 'parentOnboarding.connectionGroups.admin.create.submit',
    })
    expect(submit).toBeDisabled()
  })
})


describe('EditGroupModal capacity guard', () => {
  it('renders capacityCurrent helper with active member count', async () => {
    render(
      wrap(
        <EditGroupModal
          group={group}
          activeMemberCount={8}
          isOpen
          onClose={() => {}}
        />,
      ),
    )
    const helper = await screen.findByTestId('cg-edit-capacity-current')
    expect(helper.textContent).toContain(
      'parentOnboarding.connectionGroups.admin.edit.capacityCurrent',
    )
    expect(helper.textContent).toContain('"count":"8"')
  })

  it('renders the capacity-too-low error after a 422 with excess', async () => {
    updateMock.mockRejectedValue({
      data: {
        detail: {
          error: 'capacity_below_active_members',
          requested_max_members: 5,
          current_active_count: 8,
          excess: 3,
          affected_member_ids: [1, 2, 3],
        },
      },
    })
    render(
      wrap(
        <EditGroupModal
          group={group}
          activeMemberCount={8}
          isOpen
          onClose={() => {}}
        />,
      ),
    )
    const submit = await screen.findByRole('button', {
      name: 'parentOnboarding.connectionGroups.admin.edit.submit',
    })
    fireEvent.click(submit)
    const err = await screen.findByTestId('cg-edit-capacity-error')
    expect(err.textContent).toContain(
      'parentOnboarding.connectionGroups.admin.edit.errorCapacityTooLow',
    )
    expect(err.textContent).toContain('"excess":"3"')
  })
})


describe('ArchiveGroupDialog', () => {
  it('hides patron message field until notify_members is checked', async () => {
    render(wrap(<ArchiveGroupDialog group={group} isOpen onClose={() => {}} />))
    expect(screen.queryByTestId('cg-archive-patron-message')).toBeNull()
    fireEvent.click(screen.getByTestId('cg-archive-notify-toggle'))
    await waitFor(() =>
      expect(screen.getByTestId('cg-archive-patron-message')).toBeTruthy(),
    )
  })

  it('sends notify_members=true and patron_message when toggle is on', async () => {
    archiveMock.mockResolvedValue({
      id: 12,
      is_active: false,
      notified_member_count: 5,
      email_dispatched: true,
      email_partial: false,
    })
    render(wrap(<ArchiveGroupDialog group={group} isOpen onClose={() => {}} />))
    fireEvent.click(screen.getByTestId('cg-archive-notify-toggle'))
    const msg = await screen.findByTestId('cg-archive-patron-message')
    fireEvent.change(msg, { target: { value: 'Thanks all!' } })
    fireEvent.click(
      screen.getByRole('button', {
        name: 'parentOnboarding.connectionGroups.admin.archive.submit',
      }),
    )
    await waitFor(() => expect(archiveMock).toHaveBeenCalled())
    expect(archiveMock).toHaveBeenCalledWith(12, {
      archive_reason: 'cohort_complete',
      archive_notes: undefined,
      notify_members: true,
      patron_message: 'Thanks all!',
    })
  })
})


describe('CancelMeetingDialog', () => {
  const meeting = {
    id: 99,
    group_id: 12,
    meeting_date: '2026-06-01',
    scheduled_time: '10:00',
    location: 'Community Room A',
    status: 'scheduled' as const,
  }

  it('uses role=alertdialog because the action is irreversible', async () => {
    render(
      wrap(
        <CancelMeetingDialog
          group={group}
          meeting={meeting}
          isOpen
          onClose={() => {}}
          onSuccess={() => {}}
        />,
      ),
    )
    const dialog = await screen.findByTestId('cg-cancel-meeting-dialog')
    expect(dialog.getAttribute('role')).toBe('alertdialog')
  })

  it('preview pane reflects the patron_message input live', async () => {
    render(
      wrap(
        <CancelMeetingDialog
          group={group}
          meeting={meeting}
          isOpen
          onClose={() => {}}
          onSuccess={() => {}}
        />,
      ),
    )
    const msg = await screen.findByTestId('cg-cancel-patron-message')
    fireEvent.change(msg, { target: { value: 'Storm tomorrow.' } })
    await waitFor(() => {
      const preview = screen.getByTestId('cg-cancel-preview')
      expect(preview.textContent).toContain('Storm tomorrow.')
    })
  })

  it('reports email_partial when the server returns it', async () => {
    cancelMeetingMock.mockResolvedValue({
      meeting: { ...meeting, status: 'cancelled' },
      notified_member_count: 3,
      email_dispatched: true,
      email_partial: true,
    })
    const onSuccess = vi.fn()
    render(
      wrap(
        <CancelMeetingDialog
          group={group}
          meeting={meeting}
          isOpen
          onClose={() => {}}
          onSuccess={onSuccess}
        />,
      ),
    )
    fireEvent.click(
      screen.getByRole('button', {
        name: 'parentOnboarding.connectionGroups.admin.meetings.cancelSubmit',
      }),
    )
    await waitFor(() => expect(onSuccess).toHaveBeenCalled())
    // Partial path uses the "cancelPartial" toast string, not the count one.
    expect(toastSuccess).toHaveBeenCalledWith(
      'parentOnboarding.connectionGroups.admin.meetings.cancelPartial',
    )
  })
})


describe('MeetingsDrawer', () => {
  it('renders rows from listMeetings and exposes cancel/reschedule actions', async () => {
    listMeetingsMock.mockResolvedValue({
      meetings: [
        {
          id: 1,
          group_id: 12,
          meeting_date: '2026-06-01',
          scheduled_time: '10:00',
          location: 'A',
          status: 'scheduled',
        },
        {
          id: 2,
          group_id: 12,
          meeting_date: '2026-06-08',
          scheduled_time: '10:00',
          location: 'A',
          status: 'cancelled',
        },
      ],
      total: 2,
    })
    render(wrap(<MeetingsDrawer group={group} isOpen onClose={() => {}} />))
    const rows = await screen.findAllByTestId('cg-meeting-row')
    expect(rows).toHaveLength(2)
    // Only the scheduled row should expose the actions.
    const cancelActions = screen.queryAllByTestId('cg-meeting-cancel-action')
    expect(cancelActions).toHaveLength(1)
  })
})
