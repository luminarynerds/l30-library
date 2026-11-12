import { useState } from "react"
import { HelpCircle } from "lucide-react"
import { KnowledgeBaseDrawer } from "./KnowledgeBaseDrawer"
import { t } from "@/i18n"

export function KnowledgeBaseHelpButton() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t("aria.knowledgeBaseDrawer.open", "Open Knowledge Base")}
        className="fixed bottom-6 right-20 z-50 flex items-center justify-center w-12 h-12 rounded-full bg-lsc-rose text-white shadow-lg hover:bg-lsc-rose/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-lsc-rose"
      >
        <HelpCircle className="w-6 h-6" aria-hidden="true" />
      </button>
      <KnowledgeBaseDrawer open={open} onClose={() => setOpen(false)} />
    </>
  )
}
