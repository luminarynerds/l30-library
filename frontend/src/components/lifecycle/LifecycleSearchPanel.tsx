/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { RefObject } from "react"
import { Search, Loader2, Barcode, ArrowRight } from "lucide-react"
import type { LifecycleSearchResult } from "../../api/lifecycle-api"

type SearchType = "keyword" | "copy" | "item" | "scan"

interface Props {
  searchType: SearchType
  searchId: string
  isLoading: boolean
  scanInputRef: RefObject<HTMLInputElement>
  searchResults: LifecycleSearchResult[]
  onSearchTypeChange: (type: SearchType) => void
  onSearchIdChange: (value: string) => void
  onSearch: () => void
  onBarcodeScan: (barcode: string) => void
  onSelectResult: (result: LifecycleSearchResult) => void
}

export function LifecycleSearchPanel({
  searchType,
  searchId,
  isLoading,
  scanInputRef,
  searchResults,
  onSearchTypeChange,
  onSearchIdChange,
  onSearch,
  onBarcodeScan,
  onSelectResult,
}: Props): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
      <h2 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <Search className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        Search Items
      </h2>
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex gap-2">
          {(["keyword", "copy", "item", "scan"] as const).map((type) => (
            <button
              key={type}
              onClick={() => onSearchTypeChange(type)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                searchType === type
                  ? "bg-lsc-rose text-white"
                  : "bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/50"
              }`}
            >
              {type === "keyword" ? "By Title / Barcode" : type === "copy" ? "By Copy ID" : type === "item" ? "By Catalog Item ID" : "Scan Barcode"}
            </button>
          ))}
        </div>
        <div className="flex-1 flex gap-2">
          {searchType === "scan" ? (
            <div className="relative flex-1">
              <Barcode className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
              <input
                ref={scanInputRef}
                type="text"
                autoFocus
                value={searchId}
                onChange={(e) => onSearchIdChange(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && searchId.trim()) { onBarcodeScan(searchId); } }}
                placeholder="Scan or type barcode..."
                className="w-full pl-10 pr-4 py-2 border-2 border-lsc-rose/50 dark:border-lsc-rose/40 rounded-xl bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent font-mono"
              />
              {!isLoading && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-pulse">Waiting for scan...</span>}
              {isLoading && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 motion-safe:animate-spin text-lsc-rose" />}
            </div>
          ) : (
            <>
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                <input
                  type="text"
                  value={searchId}
                  onChange={(e) => onSearchIdChange(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && onSearch()}
                  placeholder={searchType === "keyword" ? "Search by title, author, barcode, ISBN, or call number..." : searchType === "copy" ? "Enter item copy ID..." : "Enter catalog item ID..."}
                  className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              <button
                onClick={onSearch}
                disabled={isLoading}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                Search
              </button>
            </>
          )}
        </div>
      </div>

      {searchResults.length > 0 && (
        <div className="mt-4 border border-lsc-border dark:border-earth-700 rounded-xl divide-y divide-lsc-border dark:divide-earth-700 max-h-80 overflow-y-auto">
          {searchResults.map((result) => (
            <button
              key={result.copy_id}
              onClick={() => onSelectResult(result)}
              className="w-full text-left p-3 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 transition-colors flex items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={result.title}>{result.title}</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={result.author ?? undefined}>{result.author}</p>
              </div>
              <div className="flex items-center gap-3 shrink-0 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                {result.barcode && <span className="font-mono">{result.barcode}</span>}
                {result.call_number && <span>{result.call_number}</span>}
                {result.condition && (
                  <span className="px-2 py-0.5 text-xs rounded bg-lsc-cream dark:bg-lsc-brown/50">{result.condition}</span>
                )}
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">Copy #{result.copy_id}</span>
              </div>
              <ArrowRight className="w-4 h-4 text-lsc-rose shrink-0" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
