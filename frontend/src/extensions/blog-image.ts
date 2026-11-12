/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import Image from "@tiptap/extension-image"

declare module "@tiptap/extension-image" {
  interface SetImageOptions {
    /** Persisted by BlogImage for decorative images. */
    role?: string
  }
}

/**
 * BlogImage extends the stock @tiptap/extension-image with a `role` attribute
 * so decorative images can be inserted as `<img alt="" role="presentation">`.
 *
 * Stock Image only declares src/alt/title/width/height; `role` would be silently
 * dropped by renderHTML without this extension.
 */
export const BlogImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      role: {
        default: null,
        parseHTML: (el) => el.getAttribute("role"),
        renderHTML: (attrs) => (attrs.role ? { role: attrs.role } : {}),
      },
    }
  },
})

export default BlogImage
