/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Plus, Loader2, Edit3, Trash2, Eye, EyeOff, Star, ChevronDown,
  Book, GripVertical, ArrowUp, ArrowDown, BookOpen, Calendar, User, CheckCircle,
} from 'lucide-react';
import type { StaffPicksListWithItems, StaffPicksItem } from '../../api/domains/content/staff-picks-api';
import { ShareButton } from '@/components/ShareButton';

interface ListDetailViewProps {
  selectedList: StaffPicksListWithItems | null;
  isLoadingList: boolean;
  onBack: () => void;
  onEditList: (list: StaffPicksListWithItems) => void;
  onToggleActive: (list: StaffPicksListWithItems) => void;
  onAddItem: () => void;
  onEditItem: (item: StaffPicksItem) => void;
  onRemoveItem: (item: StaffPicksItem) => void;
  onMoveItem: (item: StaffPicksItem, direction: 'up' | 'down') => void;
  formatDate: (d: string | null | undefined) => string;
}

export function ListDetailView({
  selectedList,
  isLoadingList,
  onBack,
  onEditList,
  onToggleActive,
  onAddItem,
  onEditItem,
  onRemoveItem,
  onMoveItem,
  formatDate,
}: ListDetailViewProps) {
  return (
    <div className="space-y-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm">
        <button
          onClick={onBack}
          className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline mb-4 flex items-center gap-1"
        >
          <ChevronDown className="w-4 h-4 rotate-90" />
          Back to lists
        </button>

        {isLoadingList ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
          </div>
        ) : selectedList ? (
          <div>
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                    {selectedList.title}
                  </h2>
                  {selectedList.display_order === 0 && (
                    <span className="flex items-center gap-1 px-2 py-0.5 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400 text-xs font-medium rounded-full">
                      <Star className="w-3 h-3" />
                      Featured
                    </span>
                  )}
                  {selectedList.is_active ? (
                    <span className="flex items-center gap-1 px-2 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400 text-xs font-medium rounded-full">
                      <CheckCircle className="w-3 h-3" />
                      Published
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 px-2 py-0.5 bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs font-medium rounded-full">
                      <EyeOff className="w-3 h-3" />
                      Draft
                    </span>
                  )}
                </div>
                {selectedList.description && (
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                    {selectedList.description}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <span className="flex items-center gap-1">
                    <User className="w-4 h-4" />
                    Created by {selectedList.created_by_name || "Unknown"}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    {formatDate(selectedList.created_at)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <ShareButton
                  resourceType="staff_pick"
                  resourceId={selectedList.id}
                  title={selectedList.title}
                  {...(selectedList.description ? { description: selectedList.description } : {})}
                  variant="compact"
                  showCount={true}
                  platforms={['copy_link', 'bluesky', 'mastodon', 'email']}
                />
                <button
                  onClick={() => onEditList(selectedList)}
                  className="flex items-center gap-2 px-3 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                >
                  <Edit3 className="w-4 h-4" />
                  Edit
                </button>
                <button
                  onClick={() => onToggleActive(selectedList)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                    selectedList.is_active
                      ? "text-status-warning-600 dark:text-status-warning-400 hover:bg-status-warning-50 dark:bg-status-warning-900/20 dark:hover:bg-status-warning-900/20"
                      : "text-status-success-600 dark:text-status-success-400 hover:bg-status-success-50 dark:bg-status-success-900/20 dark:hover:bg-status-success-900/20"
                  }`}
                >
                  {selectedList.is_active ? (
                    <>
                      <EyeOff className="w-4 h-4" />
                      Unpublish
                    </>
                  ) : (
                    <>
                      <Eye className="w-4 h-4" />
                      Publish
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mt-6 mb-6">
              <div className="bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <BookOpen className="w-4 h-4" />
                  <span className="text-sm">Items</span>
                </div>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {selectedList.item_count}
                </p>
              </div>
              <div className="bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl p-4">
                <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  <Calendar className="w-4 h-4" />
                  <span className="text-sm">Last Updated</span>
                </div>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {formatDate(selectedList.updated_at || selectedList.created_at)}
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {selectedList && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
          <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              Items ({selectedList.items.length})
            </h3>
            <button
              onClick={onAddItem}
              className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose text-white text-sm rounded-lg hover:bg-lsc-rose/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Item
            </button>
          </div>

          {selectedList.items.length === 0 ? (
            <div className="p-8 text-center">
              <Book className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                No items in this list yet. Add some books to get started.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-lsc-border dark:divide-earth-700">
              {selectedList.items
                .sort((a, b) => a.display_order - b.display_order)
                .map((item, index) => (
                  <div
                    key={item.id}
                    className="p-4 flex items-start gap-4 hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors"
                  >
                    <div className="flex flex-col items-center gap-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <button
                        onClick={() => onMoveItem(item, "up")}
                        disabled={index === 0}
                        className="p-1 hover:text-lsc-rose dark:hover:text-lsc-rose-light disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ArrowUp className="w-4 h-4" />
                      </button>
                      <GripVertical className="w-4 h-4" />
                      <button
                        onClick={() => onMoveItem(item, "down")}
                        disabled={index === selectedList.items.length - 1}
                        className="p-1 hover:text-lsc-rose dark:hover:text-lsc-rose-light disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <ArrowDown className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {item.catalog_item.title}
                      </h4>
                      {item.catalog_item.author && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          by {item.catalog_item.author}
                        </p>
                      )}
                      {item.staff_notes && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 italic bg-lsc-cream/50 dark:bg-lsc-brown/30 px-3 py-2 rounded-lg">
                          "{item.staff_notes}"
                        </p>
                      )}
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                        Added by {item.added_by_name || "Unknown"} on {formatDate(item.added_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => onEditItem(item)}
                        className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                        title="Edit notes"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onRemoveItem(item)}
                        className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                        title="Remove from list"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
