/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { List, Plus, BookOpen, User, Calendar, Eye, EyeOff, Star, FileText, Trash2 } from 'lucide-react';
import type { StaffPicksList } from '../../api/domains/content/staff-picks-api';

interface ListsViewProps {
  lists: StaffPicksList[];
  onCreateList: () => void;
  onLoadDetail: (id: number) => void;
  onToggleActive: (list: StaffPicksList) => void;
  onSetFeatured: (list: StaffPicksList) => void;
  onDeleteList: (list: StaffPicksList) => void;
  formatDate: (d: string | null | undefined) => string;
}

export function ListsView({
  lists,
  onCreateList,
  onLoadDetail,
  onToggleActive,
  onSetFeatured,
  onDeleteList,
  formatDate,
}: ListsViewProps) {
  if (lists.length === 0) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 text-center">
        <List className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
          No Staff Picks Lists
        </h3>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Create your first curated reading list for patrons
        </p>
        <button
          onClick={onCreateList}
          className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create List
        </button>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {lists.map((list) => (
        <div
          key={list.id}
          className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
                <h3
                  className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream cursor-pointer hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
                  onClick={() => onLoadDetail(list.id)}
                >
                  {list.title}
                </h3>
                {list.display_order === 0 && (
                  <span className="flex items-center gap-1 px-2 py-0.5 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400 text-xs font-medium rounded-full">
                    <Star className="w-3 h-3" />
                    Featured
                  </span>
                )}
                {list.is_active ? (
                  <span className="flex items-center gap-1 px-2 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400 text-xs font-medium rounded-full">
                    <Eye className="w-3 h-3" />
                    Published
                  </span>
                ) : (
                  <span className="flex items-center gap-1 px-2 py-0.5 bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs font-medium rounded-full">
                    <EyeOff className="w-3 h-3" />
                    Draft
                  </span>
                )}
              </div>
              {list.description && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3 line-clamp-2" title={list.description}>
                  {list.description}
                </p>
              )}
              <div className="flex flex-wrap items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <span className="flex items-center gap-1">
                  <BookOpen className="w-4 h-4" />
                  {list.item_count} items
                </span>
                <span className="flex items-center gap-1">
                  <User className="w-4 h-4" />
                  {list.created_by_name || "Unknown"}
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {formatDate(list.created_at)}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onLoadDetail(list.id)}
                className="inline-flex items-center gap-1.5 px-3 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors text-sm font-medium whitespace-nowrap"
                title="Add or remove the books in this list"
              >
                <FileText className="w-4 h-4" />
                Manage items
              </button>
              <button
                onClick={() => onToggleActive(list)}
                className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                title={list.is_active ? "Unpublish" : "Publish"}
              >
                {list.is_active ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
              {list.display_order !== 0 && (
                <button
                  onClick={() => onSetFeatured(list)}
                  className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-warning-600 dark:hover:text-status-warning-400 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                  title="Set as featured"
                >
                  <Star className="w-5 h-5" />
                </button>
              )}
              <button
                onClick={() => onDeleteList(list)}
                className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                title="Delete list"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
