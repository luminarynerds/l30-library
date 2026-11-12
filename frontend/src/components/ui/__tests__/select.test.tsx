import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../select'

function Harness({ onValueChange = vi.fn() }: { onValueChange?: (v: string) => void }) {
  return (
    <Select onValueChange={onValueChange}>
      <SelectTrigger aria-label="Timing">
        <SelectValue placeholder="Pick timing" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="morning">Morning</SelectItem>
        <SelectItem value="afternoon">Afternoon</SelectItem>
      </SelectContent>
    </Select>
  )
}

describe('ui/select', () => {
  it('is a real button with combobox semantics', () => {
    render(<Harness />)
    expect(screen.getByRole('combobox', { name: 'Timing' })).toBeInTheDocument()
  })

  it('is keyboard operable: open with Enter, choose with arrows + Enter', async () => {
    const onValueChange = vi.fn()
    const user = userEvent.setup()
    render(<Harness onValueChange={onValueChange} />)
    const trigger = screen.getByRole('combobox', { name: 'Timing' })
    trigger.focus()
    await user.keyboard('{Enter}')           // opens listbox
    await user.keyboard('{ArrowDown}{Enter}') // selects an option
    expect(onValueChange).toHaveBeenCalledWith(expect.any(String))
  })
})
