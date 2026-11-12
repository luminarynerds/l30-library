import { useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import FocusTrap from "focus-trap-react"
import { X, Maximize2, Minimize2, BookOpen } from "lucide-react"
import QuickAnswers from "./QuickAnswers"
import { t } from "@/i18n"

interface KnowledgeBaseDrawerProps {
  open: boolean
  onClose: () => void
}

export function KnowledgeBaseDrawer({ open, onClose }: KnowledgeBaseDrawerProps) {
  const closeRef = useRef<HTMLButtonElement | null>(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.overflow = prevOverflow
    }
  }, [open])

  if (!open) return null

  const drawerLabel = t("aria.knowledgeBaseDrawer.title", "Knowledge Base")

  return (
    <div className="fixed inset-0 z-[60]">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <FocusTrap
        focusTrapOptions={{
          escapeDeactivates: true,
          onDeactivate: onClose,
          allowOutsideClick: true,
          returnFocusOnDeactivate: true,
          initialFocus: () => closeRef.current!,
          fallbackFocus: () => closeRef.current ?? document.body,
        }}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-label={drawerLabel}
          className={`absolute right-0 top-0 h-full w-full ${expanded ? "max-w-3xl" : "max-w-md"} bg-lsc-white dark:bg-earth-900 shadow-lg overflow-y-auto transition-[max-width] duration-200 motion-reduce:transition-none`}
        >
          <div className="flex items-center justify-between gap-2 p-4 border-b border-lsc-border dark:border-earth-700 sticky top-0 bg-inherit z-10">
            <h2 className="font-serif text-lg truncate">{drawerLabel}</h2>
            <div className="flex items-center gap-1 flex-shrink-0">
              <Link
                to="/staff/knowledge-base"
                onClick={onClose}
                className="hidden sm:inline-flex items-center gap-1.5 h-11 px-3 rounded-lg text-sm font-medium text-lsc-rose hover:bg-earth-100 dark:hover:bg-earth-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
              >
                <BookOpen className="w-4 h-4" aria-hidden="true" />
                {t("aria.knowledgeBaseDrawer.openFull", "Full knowledge base")}
              </Link>
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                aria-pressed={expanded}
                aria-label={
                  expanded
                    ? t("aria.knowledgeBaseDrawer.collapse", "Narrow panel")
                    : t("aria.knowledgeBaseDrawer.expand", "Widen panel")
                }
                className="inline-flex items-center justify-center w-11 h-11 rounded-lg hover:bg-earth-100 dark:hover:bg-earth-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
              >
                {expanded ? (
                  <Minimize2 className="w-5 h-5" aria-hidden="true" />
                ) : (
                  <Maximize2 className="w-5 h-5" aria-hidden="true" />
                )}
              </button>
              <button
                ref={closeRef}
                type="button"
                onClick={onClose}
                aria-label={t("common.close", "Close")}
                className="inline-flex items-center justify-center w-11 h-11 -mr-2 rounded-lg hover:bg-earth-100 dark:hover:bg-earth-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
              >
                <X className="w-5 h-5" aria-hidden="true" />
              </button>
            </div>
          </div>
          <div className="p-4">
            <Link
              to="/staff/knowledge-base"
              onClick={onClose}
              className="sm:hidden mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-lsc-rose hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded"
            >
              <BookOpen className="w-4 h-4" aria-hidden="true" />
              {t("aria.knowledgeBaseDrawer.openFull", "Full knowledge base")}
            </Link>
            <QuickAnswers />
          </div>
        </div>
      </FocusTrap>
    </div>
  )
}
