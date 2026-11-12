import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../dialog'

function Harness({ open = true, onOpenChange = vi.fn() }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Session Booked!</DialogTitle>
          <DialogDescription>Details here</DialogDescription>
        </DialogHeader>
        <button>OK</button>
      </DialogContent>
    </Dialog>
  )
}

function HarnessNoDescription({ open = true, onOpenChange = vi.fn() }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Session Booked!</DialogTitle>
        </DialogHeader>
        <button>OK</button>
      </DialogContent>
    </Dialog>
  )
}

describe('ui/dialog', () => {
  it('renders role=dialog, aria-modal, named by its title', () => {
    render(<Harness />)
    expect(screen.getByRole('dialog', { name: 'Session Booked!' })).toHaveAttribute('aria-modal', 'true')
  })

  it('renders nothing when closed', () => {
    render(<Harness open={false} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('Escape calls onOpenChange(false)', async () => {
    const onOpenChange = vi.fn()
    const user = userEvent.setup()
    render(<Harness onOpenChange={onOpenChange} />)
    await user.keyboard('{Escape}')
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('has no aria-describedby when DialogDescription is not rendered', () => {
    render(<HarnessNoDescription />)
    expect(screen.getByRole('dialog')).not.toHaveAttribute('aria-describedby')
  })

  it('aria-describedby resolves to an element in the document when DialogDescription is rendered', () => {
    render(<Harness />)
    const dialog = screen.getByRole('dialog')
    const describedbyId = dialog.getAttribute('aria-describedby')
    expect(describedbyId).toBeTruthy()
    expect(document.getElementById(describedbyId as string)).not.toBeNull()
  })
})
