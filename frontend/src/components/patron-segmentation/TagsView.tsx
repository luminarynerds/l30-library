/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Tags, Plus, Edit3, Trash2 } from "lucide-react"
import { getTagColorClasses } from "../../api/patron-segmentation-api"
import type { Tag } from "../../api/patron-segmentation-api"

interface Props {
  tags: Tag[]
  onCreateTag: () => void
  onEditTag: (tag: Tag) => void
  onDeleteTag: (tag: Tag) => void
}

export function TagsView({ tags, onCreateTag, onEditTag, onDeleteTag }: Props) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
      {tags.length === 0 ? (
        <div className="p-8 text-center">
          <Tags className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            No Tags Found
          </h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            Create tags to categorize and segment patrons
          </p>
          <button
            onClick={onCreateTag}
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Tag
          </button>
        </div>
      ) : (
        <div className="divide-y divide-lsc-border dark:divide-earth-700">
          {tags.map((tag) => (
            <div
              key={tag.id}
              className="p-4 flex items-center justify-between hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors"
            >
              <div className="flex items-center gap-4">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getTagColorClasses(tag.color)}`}>
                  {tag.name}
                </span>
                <div>
                  {tag.description && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {tag.description}
                    </p>
                  )}
                  <div className="flex items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    <span>{tag.patron_count} patrons</span>
                    {!tag.is_active && (
                      <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-700 rounded text-lsc-dark/70 dark:text-lsc-cream/70">
                        Inactive
                      </span>
                    )}
                    {!tag.is_custom && (
                      <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 rounded text-lsc-rose dark:text-lsc-rose-light">
                        System
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onEditTag(tag)}
                  className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                  title="Edit tag"
                >
                  <Edit3 className="w-4 h-4" />
                </button>
                {tag.is_custom && (
                  <button
                    onClick={() => onDeleteTag(tag)}
                    className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
                    title="Delete tag"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
