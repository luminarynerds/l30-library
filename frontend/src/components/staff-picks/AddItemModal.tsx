/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Loader2, Search, Plus } from 'lucide-react';
import type { CatalogItem } from '../../api/catalog-api';
import { useTranslation } from '@/i18n';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface AddItemModalProps {
  searchQuery: string;
  onSearchQueryChange: (q: string) => void;
  onSearch: () => void;
  isSearching: boolean;
  searchResults: CatalogItem[];
  selectedItem: CatalogItem | null;
  onSelectItem: (item: CatalogItem) => void;
  onClearItem: () => void;
  itemNotes: string;
  onNotesChange: (notes: string) => void;
  onAdd: () => void;
  isAdding: boolean;
  onClose: () => void;
}

export function AddItemModal({
  searchQuery,
  onSearchQueryChange,
  onSearch,
  isSearching,
  searchResults,
  selectedItem,
  onSelectItem,
  onClearItem,
  itemNotes,
  onNotesChange,
  onAdd,
  isAdding,
  onClose,
}: AddItemModalProps) {
  const { t } = useTranslation();

  return (
    <ModalBackdrop onClose={onClose} title="Add Item to List">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] flex flex-col">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Add Item to List
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 flex-1 overflow-auto space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Search Catalog
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => onSearchQueryChange(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && onSearch()}
                placeholder={t('staffPicks.searchByTitleAuthorOr')}
                aria-label={t('staffPicks.searchByTitleAuthorOr2')}
                className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
              <button
                onClick={onSearch}
                disabled={isSearching || !searchQuery.trim()}
                className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
              >
                {isSearching ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          {selectedItem && (
            <div className="bg-lsc-cream dark:bg-lsc-brown/30 p-3 rounded-lg">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                    {selectedItem.title}
                  </p>
                  {selectedItem.author && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      by {selectedItem.author}
                    </p>
                  )}
                </div>
                <button
                  onClick={onClearItem}
                  className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {searchResults.length > 0 && !selectedItem && (
            <div className="border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden">
              <div className="max-h-60 overflow-auto divide-y divide-lsc-border dark:divide-earth-700">
                {searchResults.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onSelectItem(item)}
                    className="w-full p-3 text-left hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 transition-colors"
                  >
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {item.title}
                    </p>
                    {item.author && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        by {item.author}
                      </p>
                    )}
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      {item.item_type || "Book"}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {selectedItem && (
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Staff Notes (optional)
              </label>
              <textarea
                value={itemNotes}
                onChange={(e) => onNotesChange(e.target.value)}
                placeholder={t('staffPicks.whyYouRecommendThisBook')}
                rows={3}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
          )}
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onAdd}
            disabled={isAdding || !selectedItem}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isAdding && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            <Plus className="w-4 h-4" />
            Add to List
          </button>
        </div>
      </div>
    </ModalBackdrop>
  );
}
