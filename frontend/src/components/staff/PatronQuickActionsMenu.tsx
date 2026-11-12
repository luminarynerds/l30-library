/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * PatronQuickActionsMenu Component
 *
 * A dropdown menu with quick actions for patron management.
 * Provides common actions without opening the full detail panel.
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  MoreHorizontal,
  ShoppingCart,
  Ban,
  CheckCircle,
  Bell,
  Copy,
  User,
  Star,
  StarOff,
  ExternalLink,
} from 'lucide-react'
import type { Patron } from '@/api/staff-api'
import toast from 'react-hot-toast'
import { useTranslation} from '@/i18n'

// ==================== Types ====================

interface PatronQuickActionsMenuProps {
  patron: Patron
  isPinned: boolean
  onQuickCheckout: (patron: Patron) => void
  onBlockToggle: (patron: Patron) => void
  onSendNotification: (patron: Patron) => void
  onViewProfile: (patron: Patron) => void
  onTogglePin: (patronId: number) => void
  className?: string
}

// ==================== Component ====================

export default function PatronQuickActionsMenu({
  patron,
  isPinned,
  onQuickCheckout,
  onBlockToggle,
  onSendNotification,
  onViewProfile,
  onTogglePin,
  className = '',
}: PatronQuickActionsMenuProps): React.ReactElement {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const menuContentRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Handle keyboard navigation
  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (!isOpen) return

    const items = menuContentRef.current?.querySelectorAll('[role="menuitem"]:not([disabled])') as NodeListOf<HTMLElement> | undefined
    if (items?.length) {
      const currentIndex = Array.from(items).indexOf(document.activeElement as HTMLElement)

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault()
          items[(currentIndex + 1) % items.length]!.focus()
          return
        case 'ArrowUp':
          event.preventDefault()
          items[(currentIndex - 1 + items.length) % items.length]!.focus()
          return
        case 'Home':
          event.preventDefault()
          items[0]!.focus()
          return
        case 'End':
          event.preventDefault()
          items[items.length - 1]!.focus()
          return
      }
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      setIsOpen(false)
      buttonRef.current?.focus()
    }
  }, [isOpen])

  // Copy library card to clipboard
  const handleCopyLibraryCard = async () => {
    if (patron.library_card) {
      try {
        await navigator.clipboard.writeText(patron.library_card)
        toast.success(t('components.staff.patronQuickActionsMenu.libraryCardNumberCopiedTo'))
      } catch {
        toast.error(t('components.staff.patronQuickActionsMenu.unableToCopyToClipboard'))
      }
    } else {
      toast.error(t('components.staff.patronQuickActionsMenu.noLibraryCardNumberAvailable'))
    }
    setIsOpen(false)
  }

  // Action handlers that close the menu
  const handleQuickCheckout = () => {
    onQuickCheckout(patron)
    setIsOpen(false)
  }

  const handleBlockToggle = () => {
    onBlockToggle(patron)
    setIsOpen(false)
  }

  const handleSendNotification = () => {
    onSendNotification(patron)
    setIsOpen(false)
  }

  const handleViewProfile = () => {
    onViewProfile(patron)
    setIsOpen(false)
  }

  const handleTogglePin = () => {
    onTogglePin(patron.id)
    setIsOpen(false)
    toast.success(isPinned ? 'Patron unpinned successfully' : 'Patron pinned successfully')
  }

  return (
    <div className={`relative ${className}`} ref={menuRef} onKeyDown={handleKeyDown}>
      <button
        ref={buttonRef}
        onClick={(e) => {
          e.stopPropagation()
          setIsOpen(!isOpen)
        }}
        className="p-1.5 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors"
        aria-label={`Actions for ${patron.first_name} ${patron.last_name}`}
        aria-expanded={isOpen}
        aria-haspopup="menu"
      >
        <MoreHorizontal className="w-5 h-5" aria-hidden="true" />
      </button>

      {isOpen && (
        <div
          ref={menuContentRef}
          role="menu"
          aria-label={t('aria.staff.patronActions')}
          className="absolute right-0 top-full mt-1 w-52 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 py-1 z-50"
        >
          {/* View Profile */}
          <button
            role="menuitem"
            tabIndex={-1}
            onClick={handleViewProfile}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors focus-visible:outline-none focus-visible:bg-lsc-rose/10"
          >
            <User className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            <span>View Profile</span>
            <ExternalLink className="w-3 h-3 ml-auto text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
          </button>

          {/* Quick Checkout */}
          <button
            role="menuitem"
            tabIndex={-1}
            onClick={handleQuickCheckout}
            disabled={!patron.is_active}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:bg-lsc-rose/10"
          >
            <ShoppingCart className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <span>Quick Checkout</span>
            {!patron.is_active && (
              <span className="ml-auto text-xs text-status-danger-500 dark:text-status-danger-400">Blocked</span>
            )}
          </button>

          {/* Block/Unblock */}
          <button
            role="menuitem"
            tabIndex={-1}
            onClick={handleBlockToggle}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors focus-visible:outline-none focus-visible:bg-lsc-rose/10"
          >
            {patron.is_active ? (
              <>
                <Ban className="w-4 h-4 text-status-danger-500 dark:text-status-danger-400" aria-hidden="true" />
                <span className="text-status-danger-600 dark:text-status-danger-400">Block Patron</span>
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
                <span className="text-status-success-600 dark:text-status-success-400">Unblock Patron</span>
              </>
            )}
          </button>

          {/* Divider */}
          <div className="my-1 border-t border-lsc-border dark:border-earth-700" role="separator" />

          {/* Send Notification */}
          <button
            role="menuitem"
            tabIndex={-1}
            onClick={handleSendNotification}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors focus-visible:outline-none focus-visible:bg-lsc-rose/10"
          >
            <Bell className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            <span>Send Notification</span>
          </button>

          {/* Copy Library Card */}
          <button
            role="menuitem"
            tabIndex={-1}
            onClick={handleCopyLibraryCard}
            disabled={!patron.library_card}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:bg-lsc-rose/10"
          >
            <Copy className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            <span>Copy Library Card</span>
          </button>

          {/* Divider */}
          <div className="my-1 border-t border-lsc-border dark:border-earth-700" role="separator" />

          {/* Pin/Unpin */}
          <button
            role="menuitem"
            tabIndex={-1}
            onClick={handleTogglePin}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors focus-visible:outline-none focus-visible:bg-lsc-rose/10"
          >
            {isPinned ? (
              <>
                <StarOff className="w-4 h-4 text-status-warning-500" aria-hidden="true" />
                <span>Unpin Patron</span>
              </>
            ) : (
              <>
                <Star className="w-4 h-4 text-status-warning-500" aria-hidden="true" />
                <span>Pin to Favorites</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  )
}
