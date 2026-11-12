import { render, screen, userEvent } from "@/__tests__/utils/test-utils"
import { KnowledgeBaseHelpButton } from "@/components/knowledge-base/KnowledgeBaseHelpButton"

it("opens a labeled dialog with quick answers when the help button is clicked", async () => {
  const user = userEvent.setup()
  render(<KnowledgeBaseHelpButton />)
  await user.click(screen.getByRole("button", { name: /open knowledge base/i }))
  expect(await screen.findByRole("dialog", { name: /knowledge base/i })).toBeInTheDocument()
})

it("closes on Escape", async () => {
  const user = userEvent.setup()
  render(<KnowledgeBaseHelpButton />)
  await user.click(screen.getByRole("button", { name: /open knowledge base/i }))
  await screen.findByRole("dialog")
  await user.keyboard("{Escape}")
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
})
