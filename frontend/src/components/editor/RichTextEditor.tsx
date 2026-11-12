/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * RichTextEditor - shared TipTap WYSIWYG editor.
 *
 * Extracted from BlogFormPage so the blog and the learning-center lesson editor
 * share one editor (toolbar, link/callout/image handling, accessibility). Stores
 * and emits HTML; the patron-side renderers (MarkdownContent, blog post page)
 * sanitize it. Content is uncontrolled inside TipTap: it is initialised once from
 * `defaultValue`, and external resets (async load, version restore) go through the
 * imperative `setContent` handle, mirroring how BlogFormPage drove the editor before.
 */
import { forwardRef, useCallback, useImperativeHandle, useRef, useState } from "react"
import { useEditor, EditorContent, type Editor } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import Link from "@tiptap/extension-link"
import { BlogImage } from "@/extensions/blog-image"
import { Callout, type CalloutType } from "@/extensions/callout"
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Heading2,
  Heading3,
  Quote,
  Code,
  Link as LinkIcon,
  Image as ImageIcon,
  ImagePlus,
  Loader2,
  Info,
  AlertTriangle,
  Lightbulb,
  AlertCircle,
  ChevronDown,
  Minus,
  X,
} from "lucide-react"
import toast from "react-hot-toast"
import { ModalBackdrop } from "@/components/ui/ModalBackdrop"
import ImageAltModal from "@/components/blog/ImageAltModal"

export interface RichTextEditorHandle {
  /** Replace the whole document (async load, version restore). */
  setContent: (html: string) => void
  /** Insert an image at the current selection (media library, etc). */
  insertImage: (img: { url: string; alt: string; decorative: boolean }) => void
  /** Escape hatch for callers that still need the raw editor instance. */
  getEditor: () => Editor | null
}

export interface RichTextEditorProps {
  /** Initial HTML. Used once on mount; later resets go through the ref. */
  defaultValue?: string
  /** Fires on every change with the editor's HTML. */
  onChange: (html: string) => void
  /**
   * Upload a file and return its URL (and optionally a suggested alt). When
   * provided, the image button + drag-and-drop are enabled and the editor opens
   * the accessible alt-text modal before inserting. Omit to hide image support.
   */
  onImageUpload?: (file: File) => Promise<{ url: string; suggestedAlt?: string }>
  /** When provided, shows a "media library" button that calls this. */
  onOpenMediaLibrary?: () => void
  /** Taller editor for distraction-free writing. */
  focusMode?: boolean
  /** Accessible name for the editing region. */
  ariaLabel?: string
}

const MAX_IMAGE_BYTES = 5 * 1024 * 1024

function altFromFilename(file: File): string {
  return file.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ")
}

const RichTextEditor = forwardRef<RichTextEditorHandle, RichTextEditorProps>(function RichTextEditor(
  { defaultValue = "", onChange, onImageUpload, onOpenMediaLibrary, focusMode = false, ariaLabel },
  ref,
) {
  const [linkModalOpen, setLinkModalOpen] = useState(false)
  const [linkUrlInput, setLinkUrlInput] = useState("")
  const [showCalloutPicker, setShowCalloutPicker] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [pendingAltImage, setPendingAltImage] = useState<{ url: string; suggestedAlt: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const editor = useEditor({
    immediatelyRender: true,
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3, 4] },
        // StarterKit v3 bundles Link; disable it so the explicit Link below
        // (openOnClick: false) is the only registration and TipTap doesn't warn
        // about a duplicate "link" extension.
        link: false,
      }),
      Link.configure({ openOnClick: false }),
      BlogImage,
      Callout,
    ],
    content: defaultValue,
    editorProps: {
      attributes: {
        role: "textbox",
        "aria-multiline": "true",
        ...(ariaLabel ? { "aria-label": ariaLabel } : {}),
      },
    },
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
  })

  const insertImage = useCallback(
    ({ url, alt, decorative }: { url: string; alt: string; decorative: boolean }) => {
      if (!editor) return
      const attrs: { src: string; alt: string; role?: string } = {
        src: url,
        alt: decorative ? "" : alt,
      }
      if (decorative) attrs.role = "presentation"
      editor.chain().focus().setImage(attrs).run()
    },
    [editor],
  )

  useImperativeHandle(
    ref,
    () => ({
      setContent: (html: string) => editor?.commands.setContent(html),
      insertImage,
      getEditor: () => editor,
    }),
    [editor, insertImage],
  )

  const addLink = () => {
    setLinkUrlInput("")
    setLinkModalOpen(true)
  }

  const handleLinkInsert = () => {
    const trimmed = linkUrlInput.trim()
    if (trimmed && editor) {
      editor.chain().focus().setLink({ href: trimmed }).run()
    }
    setLinkModalOpen(false)
    setLinkUrlInput("")
  }

  const handleImageUpload = useCallback(
    async (file: File) => {
      if (!onImageUpload || !editor) return
      if (!file.type.startsWith("image/")) {
        toast.error("Only image files are allowed")
        return
      }
      if (file.size > MAX_IMAGE_BYTES) {
        toast.error("Image must be under 5MB")
        return
      }
      setIsUploading(true)
      try {
        const result = await onImageUpload(file)
        // Open the accessible alt-text modal instead of inserting silently.
        // Empty alt without role="presentation" passes axe but hides the image
        // from screen readers; the modal forces an explicit description or
        // decorative choice.
        setPendingAltImage({
          url: result.url,
          suggestedAlt: result.suggestedAlt ?? altFromFilename(file),
        })
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Upload failed")
      } finally {
        setIsUploading(false)
      }
    },
    [onImageUpload, editor],
  )

  const handleAltConfirm = useCallback(
    ({ alt, decorative }: { alt: string; decorative: boolean }) => {
      if (!pendingAltImage) return
      insertImage({ url: pendingAltImage.url, alt, decorative })
      setPendingAltImage(null)
    },
    [pendingAltImage, insertImage],
  )

  const addImage = () => fileInputRef.current?.click()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleImageUpload(file)
    e.target.value = ""
  }

  const handleEditorDrop = useCallback(
    (e: React.DragEvent) => {
      if (!onImageUpload) return
      const files = e.dataTransfer?.files
      if (!files?.length) return
      const imageFile = Array.from(files).find((f) => f.type.startsWith("image/"))
      if (imageFile) {
        e.preventDefault()
        handleImageUpload(imageFile)
      }
    },
    [onImageUpload, handleImageUpload],
  )

  const handleEditorDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
  }, [])

  if (!editor) return null

  return (
    <>
      {onImageUpload && (
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/gif,image/webp"
          onChange={handleFileChange}
          className="hidden"
          aria-hidden="true"
        />
      )}
      <div className="border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
        {/* Toolbar */}
        <div className="flex flex-wrap gap-1 p-2 bg-lsc-cream dark:bg-lsc-brown/50 border-b border-lsc-border dark:border-earth-700">
          <ToolbarButton onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive("bold")} label="Bold">
            <Bold className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive("italic")} label="Italic">
            <Italic className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            active={editor.isActive("heading", { level: 2 })}
            label="Heading 2"
          >
            <Heading2 className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
            active={editor.isActive("heading", { level: 3 })}
            label="Heading 3"
          >
            <Heading3 className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            active={editor.isActive("bulletList")}
            label="Bullet list"
          >
            <List className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
            active={editor.isActive("orderedList")}
            label="Numbered list"
          >
            <ListOrdered className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
            active={editor.isActive("blockquote")}
            label="Blockquote"
          >
            <Quote className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleCodeBlock().run()}
            active={editor.isActive("codeBlock")}
            label="Code block"
          >
            <Code className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton onClick={() => editor.chain().focus().setHorizontalRule().run()} active={false} label="Horizontal rule">
            <Minus className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton onClick={addLink} active={editor.isActive("link")} label="Add link">
            <LinkIcon className="w-4 h-4" />
          </ToolbarButton>
          {onImageUpload && (
            <ToolbarButton onClick={addImage} active={false} label="Upload image">
              {isUploading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <ImageIcon className="w-4 h-4" />}
            </ToolbarButton>
          )}
          {onOpenMediaLibrary && (
            <ToolbarButton onClick={onOpenMediaLibrary} active={false} label="Insert from media library">
              <ImagePlus className="w-4 h-4" />
            </ToolbarButton>
          )}

          <div className="w-px h-5 bg-lsc-border dark:bg-earth-700 mx-0.5" />

          {/* Callout picker */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowCalloutPicker(!showCalloutPicker)}
              onBlur={() => setTimeout(() => setShowCalloutPicker(false), 150)}
              className={`flex items-center gap-1 p-2 rounded-lg transition-colors ${
                editor.isActive("callout")
                  ? "bg-lsc-rose/20 text-lsc-rose"
                  : "text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-lsc-cream dark:hover:bg-earth-700"
              }`}
              aria-label="Insert callout"
              aria-expanded={showCalloutPicker}
            >
              <Info className="w-4 h-4" />
              <ChevronDown className="w-3 h-3" />
            </button>
            {showCalloutPicker && (
              <div className="absolute top-full left-0 mt-1 z-20 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg py-1 min-w-[160px]">
                {([
                  { type: "info" as CalloutType, icon: Info, label: "Info" },
                  { type: "tip" as CalloutType, icon: Lightbulb, label: "Tip" },
                  { type: "warning" as CalloutType, icon: AlertTriangle, label: "Warning" },
                  { type: "important" as CalloutType, icon: AlertCircle, label: "Important" },
                ]).map(({ type, icon: Icon, label }) => (
                  <button
                    key={type}
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => {
                      if (editor.isActive("callout")) {
                        editor.chain().focus().unsetCallout().run()
                      } else {
                        editor.chain().focus().setCallout({ type }).run()
                      }
                      setShowCalloutPicker(false)
                    }}
                    className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
                  >
                    <Icon className="w-4 h-4" />
                    {label}
                  </button>
                ))}
                {editor.isActive("callout") && (
                  <>
                    <div className="border-t border-lsc-border dark:border-earth-700 my-1" />
                    <button
                      type="button"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => {
                        editor.chain().focus().unsetCallout().run()
                        setShowCalloutPicker(false)
                      }}
                      className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-status-danger-600 dark:text-status-danger-400 hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
                    >
                      <X className="w-4 h-4" />
                      Remove callout
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
        {/* Editor content */}
        <EditorContent
          editor={editor}
          className={`prose prose-lg dark:prose-invert max-w-none p-4 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus-within:outline-none ${focusMode ? "min-h-[70vh]" : "min-h-[300px]"}`}
          onDrop={handleEditorDrop}
          onDragOver={handleEditorDragOver}
        />
        {isUploading && (
          <div className="flex items-center gap-2 px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/60 bg-lsc-cream/50 dark:bg-earth-700/50 border-t border-lsc-border dark:border-earth-700">
            <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
            Uploading image...
          </div>
        )}
      </div>
      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 px-1 pt-1">
        {(() => {
          const text = editor.getText()
          const words = text.split(/\s+/).filter(Boolean).length
          return `${words} words / ${text.length} characters`
        })()}
      </div>
      <style>{`
        .ProseMirror .callout {
          border-left: 4px solid;
          border-radius: 0.5rem;
          padding: 0.75rem 1rem;
          margin: 0.75rem 0;
        }
        .ProseMirror .callout[data-callout-type="info"] {
          border-color: #3b82f6;
          background: rgba(59, 130, 246, 0.08);
        }
        .ProseMirror .callout[data-callout-type="tip"] {
          border-color: #22c55e;
          background: rgba(34, 197, 94, 0.08);
        }
        .ProseMirror .callout[data-callout-type="warning"] {
          border-color: #f59e0b;
          background: rgba(245, 158, 11, 0.08);
        }
        .ProseMirror .callout[data-callout-type="important"] {
          border-color: #ef4444;
          background: rgba(239, 68, 68, 0.08);
        }
      `}</style>

      {/* Accessible alt-text modal (replaces window.prompt) */}
      {pendingAltImage && (
        <ImageAltModal
          isOpen={!!pendingAltImage}
          imageUrl={pendingAltImage.url}
          initialAlt={pendingAltImage.suggestedAlt}
          onConfirm={handleAltConfirm}
          onCancel={() => setPendingAltImage(null)}
        />
      )}

      {/* Link URL modal (replaces window.prompt) */}
      {linkModalOpen && (
        <ModalBackdrop onClose={() => setLinkModalOpen(false)} title="Insert link">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-sm mx-4 space-y-4">
            <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Insert link</h2>
            <div className="space-y-1">
              <label htmlFor="rte-link-url" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                URL
              </label>
              <input
                id="rte-link-url"
                type="url"
                value={linkUrlInput}
                onChange={(e) => setLinkUrlInput(e.target.value)}
                autoFocus
                placeholder="https://example.com"
                className="w-full px-3 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault()
                    handleLinkInsert()
                  }
                }}
              />
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setLinkModalOpen(false)}
                className="px-4 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700"
              >
                Cancel
              </button>
              <button
                onClick={handleLinkInsert}
                disabled={!linkUrlInput.trim()}
                className="px-4 py-2 text-sm rounded-xl bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90 disabled:opacity-50"
              >
                Insert
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </>
  )
})

export default RichTextEditor

// ============================================================================
// Toolbar Button
// ============================================================================

function ToolbarButton({
  onClick,
  active,
  label,
  children,
}: {
  onClick: () => void
  active: boolean
  label: string
  children: React.ReactNode
}): React.ReactElement {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`p-2 rounded-lg transition-colors ${
        active
          ? "bg-lsc-rose/20 text-lsc-rose"
          : "text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-lsc-cream dark:hover:bg-earth-700"
      }`}
      aria-label={label}
      aria-pressed={active}
    >
      {children}
    </button>
  )
}
