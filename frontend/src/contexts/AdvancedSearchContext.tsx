/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
/**
 * Advanced Search Context
 *
 * Provides global state management for the advanced staff search modal.
 * Allows opening the search modal from anywhere in the app with Ctrl+K.
 */

import { createContext, useContext, useState, useCallback, useMemo, ReactNode } from 'react';
import { AdvancedStaffSearchModal } from '../components/AdvancedStaffSearchModal';

interface AdvancedSearchContextType {
  isOpen: boolean;
  openSearch: () => void;
  closeSearch: () => void;
  toggleSearch: () => void;
}

const AdvancedSearchContext = createContext<AdvancedSearchContextType | undefined>(undefined);

export function AdvancedSearchProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);

  const openSearch = useCallback(() => setIsOpen(true), []);
  const closeSearch = useCallback(() => setIsOpen(false), []);
  const toggleSearch = useCallback(() => setIsOpen(prev => !prev), []);

  // Ctrl+K is handled by HeaderSearch — no duplicate listener here.

  const contextValue = useMemo(() => ({
    isOpen, openSearch, closeSearch, toggleSearch,
  }), [isOpen, openSearch, closeSearch, toggleSearch]);

  return (
    <AdvancedSearchContext.Provider value={contextValue}>
      {children}
      <AdvancedStaffSearchModal isOpen={isOpen} onClose={closeSearch} />
    </AdvancedSearchContext.Provider>
  );
}

export function useAdvancedSearch() {
  const context = useContext(AdvancedSearchContext);
  if (!context) {
    throw new Error('useAdvancedSearch must be used within AdvancedSearchProvider');
  }
  return context;
}
