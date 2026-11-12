/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * RichTextEditor - A simple rich text editor with basic formatting
 * Supports: bold, italic, bullet lists, numbered lists, links
 * Stores content as HTML
 */
import { useState, useRef, useCallback, useEffect } from "react";
import DOMPurify from "dompurify";
import {
  Bold, Italic, List, ListOrdered, Link, Eye, Edit3, Undo, Redo
} from "lucide-react";
import { t } from '@/i18n'

// Security: Strict DOMPurify config
const DOMPURIFY_CONFIG = {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'span'],
  ALLOWED_ATTR: ['href', 'target', 'rel'],
  KEEP_CONTENT: true
};

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  label?: string;
  showPreviewToggle?: boolean;
}

export default function RichTextEditor({
  value,
  onChange,
  placeholder = "Enter text...",
  rows = 4,
  label,
  showPreviewToggle = true,
}: RichTextEditorProps) {
  const [showPreview, setShowPreview] = useState(false);
  const editorRef = useRef<HTMLDivElement>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize editor content
  useEffect(() => {
    if (editorRef.current && !isInitialized) {
      editorRef.current.innerHTML = DOMPurify.sanitize(value || "", DOMPURIFY_CONFIG);
      // Use a microtask to avoid synchronous setState in effect
      Promise.resolve().then(() => {
        setIsInitialized(true);
      });
    }
  }, [value, isInitialized]);

  // Reset when value changes externally (e.g., switching between items)
  useEffect(() => {
    if (editorRef.current && isInitialized) {
      const currentContent = editorRef.current.innerHTML;
      const sanitizedValue = DOMPurify.sanitize(value || "", DOMPURIFY_CONFIG);
      // Only update if content differs significantly (ignore minor whitespace)
      if (currentContent.replace(/\s/g, '') !== sanitizedValue.replace(/\s/g, '')) {
        editorRef.current.innerHTML = sanitizedValue;
      }
    }
  }, [value, isInitialized]);

  const handleInput = useCallback(() => {
    if (editorRef.current) {
      const html = editorRef.current.innerHTML;
      // Sanitize on output
      const sanitized = DOMPurify.sanitize(html, DOMPURIFY_CONFIG);
      onChange(sanitized);
    }
  }, [onChange]);

  const execCommand = useCallback((command: string, value: string | undefined = undefined) => {
    document.execCommand(command, false, value);
    editorRef.current?.focus();
    handleInput();
  }, [handleInput]);

  const handleBold = () => execCommand("bold");
  const handleItalic = () => execCommand("italic");

  const handleBulletList = () => execCommand("insertUnorderedList");
  const handleNumberedList = () => execCommand("insertOrderedList");

  const handleLink = () => {
    const url = prompt("Enter URL:");
    if (url) {
      execCommand("createLink", url);
    }
  };

  const handleUndo = () => execCommand("undo");
  const handleRedo = () => execCommand("redo");

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Handle keyboard shortcuts
    if (e.metaKey || e.ctrlKey) {
      switch (e.key.toLowerCase()) {
        case 'b':
          e.preventDefault();
          handleBold();
          break;
        case 'i':
          e.preventDefault();
          handleItalic();
          break;
        case 'z':
          e.preventDefault();
          if (e.shiftKey) {
            handleRedo();
          } else {
            handleUndo();
          }
          break;
      }
    }
  };

  const toolbarButtonClass = "p-1.5 rounded hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 transition-colors";

  return (
    <div className="rich-text-editor">
      {label && (
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
          {label}
        </label>
      )}

      <div className="border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden bg-lsc-white dark:bg-lsc-brown">
        {/* Toolbar */}
        <div className="flex items-center gap-0.5 px-2 py-1.5 border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-800/50">
          <button
            type="button"
            onClick={handleBold}
            className={toolbarButtonClass}
            title="Bold (Ctrl+B)"
            aria-label={t('aria.richTextEditor.bold')}
          >
            <Bold className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={handleItalic}
            className={toolbarButtonClass}
            title="Italic (Ctrl+I)"
            aria-label={t('aria.richTextEditor.italic')}
          >
            <Italic className="h-4 w-4" />
          </button>

          <div className="w-px h-5 bg-lsc-border dark:bg-earth-700 mx-1" />

          <button
            type="button"
            onClick={handleBulletList}
            className={toolbarButtonClass}
            title="Bullet list"
            aria-label={t('aria.richTextEditor.bulletList')}
          >
            <List className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={handleNumberedList}
            className={toolbarButtonClass}
            title="Numbered list"
            aria-label={t('aria.richTextEditor.numberedList')}
          >
            <ListOrdered className="h-4 w-4" />
          </button>

          <div className="w-px h-5 bg-lsc-border dark:bg-earth-700 mx-1" />

          <button
            type="button"
            onClick={handleLink}
            className={toolbarButtonClass}
            title="Insert link"
            aria-label={t('aria.richTextEditor.insertLink')}
          >
            <Link className="h-4 w-4" />
          </button>

          <div className="w-px h-5 bg-lsc-border dark:bg-earth-700 mx-1" />

          <button
            type="button"
            onClick={handleUndo}
            className={toolbarButtonClass}
            title="Undo (Ctrl+Z)"
            aria-label={t('aria.richTextEditor.undo')}
          >
            <Undo className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={handleRedo}
            className={toolbarButtonClass}
            title={'Redo (Ctrl+Shift+Z)'}
            aria-label={t('aria.richTextEditor.redo')}
          >
            <Redo className="h-4 w-4" />
          </button>

          {showPreviewToggle && (
            <>
              <div className="flex-1" />
              <button
                type="button"
                onClick={() => setShowPreview(!showPreview)}
                className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                  showPreview
                    ? "bg-lsc-rose/10 text-lsc-rose"
                    : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                }`}
                title={showPreview ? "Edit mode" : "Preview mode"}
              >
                {showPreview ? <Edit3 className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                {showPreview ? "Edit" : "Preview"}
              </button>
            </>
          )}
        </div>

        {/* Editor / Preview */}
        {showPreview ? (
          <div
            className="px-3 py-2 min-h-[100px] prose prose-sm dark:prose-invert max-w-prose text-lsc-dark dark:text-lsc-cream"
            style={{ minHeight: `${rows * 1.5}rem` }}
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(value || "", DOMPURIFY_CONFIG) }}
          />
        ) : (
          <div
            ref={editorRef}
            contentEditable
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            className="px-3 py-2 min-h-[100px] outline-none text-lsc-dark dark:text-lsc-cream prose prose-sm dark:prose-invert max-w-none"
            style={{ minHeight: `${rows * 1.5}rem` }}
            data-placeholder={placeholder}
            role="textbox"
            aria-multiline="true"
            aria-label={label || "Rich text editor"}
          />
        )}
      </div>

      {/* Help text */}
      <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        Supports <strong>bold</strong>, <em>italic</em>, lists, and links. Use Ctrl+B/I for shortcuts.
      </p>

      <style>{`
        .rich-text-editor [contenteditable]:empty:before {
          content: attr(data-placeholder);
          color: #9ca3af;
          pointer-events: none;
        }
        .rich-text-editor [contenteditable] ul,
        .rich-text-editor [contenteditable] ol {
          padding-left: 1.5rem;
          margin: 0.5rem 0;
        }
        .rich-text-editor [contenteditable] li {
          margin: 0.25rem 0;
        }
        .rich-text-editor [contenteditable] a {
          color: #ca7f4c;
          text-decoration: underline;
        }
      `}</style>
    </div>
  );
}

interface RichTextDisplayProps {
  content: string | undefined | null;
  className?: string;
}

export function RichTextDisplay({ content, className = "" }: RichTextDisplayProps) {
  if (!content) return null;

  return (
    <div
      className={`prose prose-sm dark:prose-invert max-w-prose ${className}`}
      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(content, DOMPURIFY_CONFIG) }}
    />
  );
}
