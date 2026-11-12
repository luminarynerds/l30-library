/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as React from 'react'
import * as SelectPrimitive from '@radix-ui/react-select'
import { ChevronDown, Check } from 'lucide-react'
import { DialogPortalContext } from './dialog'

export const Select = SelectPrimitive.Root
export const SelectGroup = SelectPrimitive.Group
export const SelectValue = SelectPrimitive.Value

export const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={`flex w-full items-center justify-between gap-2 rounded-lg border border-lsc-border bg-lsc-white px-3 py-2 text-sm text-lsc-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose dark:border-earth-700 dark:bg-earth-900 dark:text-lsc-cream ${className ?? ''}`}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown className="h-4 w-4 opacity-70" aria-hidden="true" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
))
SelectTrigger.displayName = 'SelectTrigger'

export const SelectContent = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = 'popper', ...props }, ref) => {
  // Inside a Dialog, portal into the dialog's focus-trap host so the open
  // listbox stays keyboard-operable; outside a Dialog this is null and Radix
  // portals to document.body as usual.
  const portalContainer = React.useContext(DialogPortalContext)
  return (
  <SelectPrimitive.Portal container={portalContainer ?? undefined}>
    <SelectPrimitive.Content
      ref={ref}
      position={position}
      className={`z-50 min-w-[8rem] overflow-hidden rounded-lg border border-lsc-border bg-lsc-white text-lsc-dark shadow-md dark:border-earth-700 dark:bg-earth-900 dark:text-lsc-cream ${className ?? ''}`}
      {...props}
    >
      <SelectPrimitive.Viewport className="p-1">{children}</SelectPrimitive.Viewport>
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
  )
})
SelectContent.displayName = 'SelectContent'

export const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={`relative flex w-full cursor-default select-none items-center rounded px-8 py-2 text-sm outline-none data-[highlighted]:bg-lsc-cream dark:data-[highlighted]:bg-earth-800 ${className ?? ''}`}
    {...props}
  >
    <span className="absolute left-2 flex h-4 w-4 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="h-4 w-4" aria-hidden="true" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
))
SelectItem.displayName = 'SelectItem'

export const SelectLabel = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.Label ref={ref} className={`px-8 py-1.5 text-xs font-medium opacity-70 ${className ?? ''}`} {...props} />
))
SelectLabel.displayName = 'SelectLabel'
