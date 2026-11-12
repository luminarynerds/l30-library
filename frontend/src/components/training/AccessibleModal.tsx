/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useEffect, useRef } from 'react';
import FocusTrap from 'focus-trap-react';
import { X } from 'lucide-react';
import { t } from '@/i18n'

interface AccessibleModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
  dismissible?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
};

export const AccessibleModal: React.FC<AccessibleModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  className,
  dismissible = true,
  size = 'md',
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);

  // Handle Escape key
  useEffect(() => {
    if (!isOpen || !dismissible) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, dismissible, onClose]);

  // Lock body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (dismissible && e.target === backdropRef.current) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <FocusTrap active={isOpen} focusTrapOptions={{ escapeDeactivates: true }}>
      <div
        ref={backdropRef}
        className="fixed inset-0 z-50 flex items-center justify-center bg-lsc-dark/50 backdrop-blur-sm"
        onClick={handleBackdropClick}
        role="presentation"
      >
        <div
          ref={modalRef}
          className={`relative w-full mx-4 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg ${sizeClasses[size]} ${className || ''}`}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? 'modal-title' : undefined}
        >
          {title && (
            <div className="flex items-center justify-between border-b border-lsc-border dark:border-earth-700 px-6 py-4">
              <h2 id="modal-title" className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {title}
              </h2>
              {dismissible && (
                <button
                  onClick={onClose}
                  className="p-2 rounded-xl text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"
                  aria-label={t('aria.addRoleModal.closeModal')}
                >
                  <X aria-hidden="true" className="w-5 h-5" />
                </button>
              )}
            </div>
          )}

          <div className="p-6">
            {children}
          </div>
        </div>
      </div>
    </FocusTrap>
  );
};

export default AccessibleModal;
