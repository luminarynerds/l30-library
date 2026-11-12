/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  GitBranch, FileText, Clock, MessageSquare, Link2, Dna, FolderOpen, Settings, Lightbulb, Search,
} from 'lucide-react'

export type TabId = 'dashboard' | 'tree' | 'documents' | 'timeline' | 'notes' | 'record-links' | 'dna' | 'guidance' | 'search' | 'settings'

export const GENEALOGY_TABS: { id: TabId; label: string; icon: JSX.Element }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: <FolderOpen className="w-4 h-4" /> },
  { id: 'tree', label: 'Family Tree', icon: <GitBranch className="w-4 h-4" /> },
  { id: 'documents', label: 'Documents', icon: <FileText className="w-4 h-4" /> },
  { id: 'timeline', label: 'Timeline', icon: <Clock className="w-4 h-4" /> },
  { id: 'notes', label: 'Research Notes', icon: <MessageSquare className="w-4 h-4" /> },
  { id: 'record-links', label: 'Record Links', icon: <Link2 className="w-4 h-4" /> },
  { id: 'dna', label: 'DNA', icon: <Dna className="w-4 h-4" /> },
  { id: 'guidance', label: 'Guidance', icon: <Lightbulb className="w-4 h-4" /> },
  { id: 'search', label: 'Search', icon: <Search className="w-4 h-4" /> },
  { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
]
