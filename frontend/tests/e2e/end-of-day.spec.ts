/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"

/**
 * End-of-Day Closing Workflow E2E Tests
 *
 * Tests the complete end-of-day closing workflow from session creation
 * through task execution to auto-logout scheduling.
 */

test.describe("End-of-Day Automation", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app and login as staff
    await page.goto("http://localhost:5173")

    // Login (assuming auth page)
    await page.fill('input[type="email"]', "staff@library.local")
    await page.fill('input[type="password"]', "testpassword")
    await page.click('button:has-text("Login")')

    // Wait for staff dashboard
    await page.waitForURL("**/staff", { waitUntil: "networkidle" })
  })

  test("should navigate to End-of-Day page from sidebar", async ({ page }) => {
    // Find and click the "Close Library" link in sidebar
    await page.click('a:has-text("Close Library")')

    // Verify we're on the EOD page
    await expect(page).toHaveURL("**/staff/end-of-day")
    await expect(page.locator("text=End-of-Day Closing")).toBeVisible()
  })

  test("should start a closing session", async ({ page }) => {
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Click "Start Session" button
    await page.click('button:has-text("Start Session")')

    // Wait for session to be created
    await page.waitForSelector("text=Closing Tasks", { timeout: 5000 })

    // Verify session code is displayed
    const sessionCode = page.locator("text=Session Code").locator("..").locator("span").last()
    await expect(sessionCode).toContainText("EOD-")
  })

  test("should execute individual tasks", async ({ page }) => {
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Start session
    await page.click('button:has-text("Start Session")')
    await page.waitForSelector("text=Closing Tasks", { timeout: 5000 })

    // Find and execute first task
    const firstTaskButton = page.locator('button:has-text("Execute Task")').first()
    await expect(firstTaskButton).toBeVisible()

    // Click execute task
    await firstTaskButton.click()

    // Wait for task to complete
    await page.waitForTimeout(2000)

    // Verify task status changed
    const taskStatus = page.locator("text=Completed").first()
    await expect(taskStatus).toBeVisible()
  })

  test("should show confirmation dialog for quick close", async ({ page }) => {
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Start session
    await page.click('button:has-text("Start Session")')
    await page.waitForSelector("text=Closing Tasks", { timeout: 5000 })

    // Click quick close button
    await page.click('button:has-text("Quick Close")')

    // Verify confirmation dialog appears
    const dialog = page.locator("text=Quick Close")
    await expect(dialog).toBeVisible()

    // Verify dialog has cancel and confirm buttons
    await expect(page.locator('button:has-text("Cancel")')).toBeVisible()
    await expect(page.locator('button:has-text("Yes, Quick Close")')).toBeVisible()
  })

  test("should cancel quick close from confirmation dialog", async ({ page }) => {
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Start session
    await page.click('button:has-text("Start Session")')
    await page.waitForSelector("text=Closing Tasks", { timeout: 5000 })

    // Click quick close
    await page.click('button:has-text("Quick Close")')

    // Wait for dialog
    await page.waitForSelector("text=Quick Close?")

    // Click cancel
    await page.click('button:has-text("Cancel")')

    // Dialog should be gone
    await expect(page.locator("text=Quick Close?")).not.toBeVisible()

    // Still on EOD page
    await expect(page).toHaveURL("**/staff/end-of-day")
  })

  test("should complete session after all tasks", async ({ page }) => {
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Start session
    await page.click('button:has-text("Start Session")')
    await page.waitForSelector("text=Closing Tasks", { timeout: 5000 })

    // Get task count
    const taskCountText = page.locator("text=tasks").first()
    const content = await taskCountText.textContent()
    const [completed, total] = content?.match(/\d+/g) || ["0", "0"]

    // If tasks are incomplete, use quick close
    if (parseInt(completed) < parseInt(total)) {
      await page.click('button:has-text("Execute Remaining")')
      await page.click('button:has-text("Yes, Quick Close")')
      await page.waitForTimeout(3000)
    }

    // Complete session
    await page.click('button:has-text("Complete Session")')

    // Confirm dialog
    await page.click('button:has-text("Complete")')

    // Wait for session completion
    await page.waitForTimeout(2000)

    // Verify auto-logout button appears
    await expect(page.locator('button:has-text("Schedule Auto-Logout")')).toBeVisible()
  })

  test("should schedule auto-logout", async ({ page }) => {
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Quick setup: Start and complete session
    await page.click('button:has-text("Start Session")')
    await page.waitForSelector("text=Closing Tasks", { timeout: 5000 })

    // Quick close
    await page.click('button:has-text("Quick Close")')
    await page.click('button:has-text("Yes, Quick Close")')
    await page.waitForTimeout(3000)

    // Complete session
    await page.click('button:has-text("Complete Session")')
    await page.click('button:has-text("Complete")')
    await page.waitForTimeout(2000)

    // Click schedule logout
    await page.click('button:has-text("Schedule Auto-Logout")')

    // Confirm dialog
    await page.click('button:has-text("Schedule Logout")')

    // Verify success message
    await expect(page.locator("text=Auto-logout scheduled")).toBeVisible()
  })

  test("should track elapsed time during closing", async ({ page }) => {
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Start session
    await page.click('button:has-text("Start Session")')
    await page.waitForSelector("text=Closing Tasks", { timeout: 5000 })

    // Get initial time
    const timeDisplay = page.locator("text=Elapsed Time").locator("..").locator("p").first()
    const initialTime = await timeDisplay.textContent()

    // Wait a few seconds
    await page.waitForTimeout(3000)

    // Get updated time - should have increased
    const updatedTime = await timeDisplay.textContent()

    // Times should be different (elapsed time increased)
    expect(initialTime).not.toEqual(updatedTime)
  })

  test("should display task details when expanded", async ({ page }) => {
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Start session
    await page.click('button:has-text("Start Session")')
    await page.waitForSelector("text=Closing Tasks", { timeout: 5000 })

    // Click to expand first task
    const firstTask = page.locator('[class*="border rounded-lg"]').first()
    await firstTask.click()

    // Verify task details are visible
    await expect(page.locator('button:has-text("Execute Task")')).toBeVisible()
  })

  test("should show progress bar updating", async ({ page }) => {
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Start session
    await page.click('button:has-text("Start Session")')
    await page.waitForSelector("text=Closing Tasks", { timeout: 5000 })

    // Get initial progress
    const progressBar = page.locator('[style*="width"]').first()
    const initialWidth = await progressBar.evaluate(el => window.getComputedStyle(el).width)

    // Execute a task
    await page.click('button:has-text("Execute Task")').first()
    await page.waitForTimeout(2000)

    // Get updated progress
    const updatedWidth = await progressBar.evaluate(el => window.getComputedStyle(el).width)

    // Progress should have increased
    expect(parseFloat(updatedWidth as string)).toBeGreaterThan(parseFloat(initialWidth as string))
  })

  test("should display session summary", async ({ page }) => {
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Start session
    await page.click('button:has-text("Start Session")')
    await page.waitForSelector("text=Closing Tasks", { timeout: 5000 })

    // Look for session summary section
    const summary = page.locator("text=Session Summary")
    await expect(summary).toBeVisible()

    // Verify summary contains required info
    await expect(page.locator("text=Session Code")).toBeVisible()
    await expect(page.locator("text=Status")).toBeVisible()
    await expect(page.locator("text=Completed")).toBeVisible()
  })

  test("should handle network errors gracefully", async ({ page }) => {
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Simulate network issue
    await page.context().setOffline(true)

    // Try to start session
    await page.click('button:has-text("Start Session")')

    // Should show error message
    await expect(page.locator("text=Failed").or(page.locator("text=Error"))).toBeVisible({ timeout: 5000 })

    // Re-enable network
    await page.context().setOffline(false)
  })

  test("should require authentication", async ({ context }) => {
    // Create new page without authentication
    const page = await context.newPage()

    // Try to access EOD page directly
    await page.goto("http://localhost:5173/staff/end-of-day")

    // Should redirect to login
    await expect(page).toHaveURL("**/login")
  })

  test("should show mobile responsive layout", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    await page.goto("http://localhost:5173/staff/end-of-day")

    // Start session
    await page.click('button:has-text("Start Session")')
    await page.waitForSelector("text=Closing Tasks", { timeout: 5000 })

    // Verify layout is responsive (sidebar hidden, etc)
    // This depends on your responsive design, but check that content is still accessible
    await expect(page.locator("text=Closing Tasks")).toBeVisible()
    await expect(page.locator("text=Session Summary")).toBeVisible()
  })
})
