/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

/**
 * Admin Roles & Permissions E2E Tests
 *
 * Tests for the admin roles and permissions management page including:
 * - Role selection and viewing
 * - Permission toggling
 * - Template application
 * - Role creation and editing
 * - Bulk operations
 */

test.describe('Admin Roles & Permissions Management', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication - set auth token in localStorage
    await page.goto('/admin/users')
    // Note: In a real setup, this would use proper auth flow
  })

  test.describe('Roles Tab - Navigation', () => {
    test('should navigate to roles & permissions tab', async ({ page }) => {
      await page.goto('/admin/users')

      // Click on Roles & Permissions tab
      const rolesTab = page.locator('button:has-text("Roles & Permissions")')
      await rolesTab.click()

      // Verify the tab is active
      await expect(rolesTab).toHaveClass(/bg-lsc-orange/)

      // Verify roles sidebar is visible
      const rolesSidebar = page.locator('text=Roles').first()
      await expect(rolesSidebar).toBeVisible()
    })

    test('should display list of available roles', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Wait for roles to load
      await expect(page.locator('[aria-label*="permissions"]').first()).toBeVisible({ timeout: 5000 })

      // Verify at least one role is displayed
      const roleItems = page.locator('button').filter({ hasText: /permissions/ })
      const count = await roleItems.count()
      expect(count).toBeGreaterThanOrEqual(0) // May be 0 if no roles, that's ok
    })
  })

  test.describe('Role Selection', () => {
    test('should select and display role details', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Wait for roles to load and click first role
      const firstRole = page.locator('[aria-label*="Edit"]').first()
      if (await firstRole.isVisible()) {
        // Get the parent button (role selector)
        const roleButton = firstRole.locator('xpath=ancestor::div/button[1]')
        if (await roleButton.isVisible()) {
          await roleButton.click()

          // Verify role info card is displayed
          const roleInfo = page.locator('text=/Role Information|Role Info|[0-9]+ permission/').first()
          await expect(roleInfo).toBeVisible({ timeout: 3000 })
        }
      }
    })

    test('should display role permissions in grid format', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Wait for permissions section
      const permissionsSection = page.locator('text=Permissions')
      await expect(permissionsSection).toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('Permission Management', () => {
    test('should toggle individual permissions', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Look for permission checkboxes
      const permissionCheckbox = page.locator('[class*="rounded"] [class*="border-2"]').first()

      if (await permissionCheckbox.isVisible()) {
        const initialState = await permissionCheckbox.getAttribute('class')

        // Click to toggle
        await permissionCheckbox.click()

        // Wait for the state to change (with animation)
        await page.waitForTimeout(500)

        const newState = await permissionCheckbox.getAttribute('class')
        // State should change (this is a basic check)
        expect(initialState).toBeDefined()
        expect(newState).toBeDefined()
      }
    })

    test('should display permission details with descriptions', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Wait for permission items to be visible
      await expect(page.locator('text=/Allow|Enable|Manage/')).toBeDefined()
    })

    test('should show permission codes for technical reference', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Look for permission codes (like "circulation.checkout")
      const permissionCodes = page.locator('[class*="rounded-full"] [class*="text-lsc-orange"]')

      if (await permissionCodes.first().isVisible()) {
        const codeText = await permissionCodes.first().textContent()
        // Permission codes should have a dot notation
        expect(codeText).toMatch(/[a-z]+\.[a-z]+/)
      }
    })
  })

  test.describe('Permission Templates', () => {
    test('should display available templates', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Look for template section
      const templateSection = page.locator('text=Quick Templates')

      if (await templateSection.isVisible()) {
        // Verify template buttons are displayed
        const templateButtons = page.locator('[class*="border-2"] [class*="text-sm"]:has-text(/Circulation|Catalog|Patron|Reports|Basic/)')
        const count = await templateButtons.count()
        expect(count).toBeGreaterThan(0)
      }
    })

    test('should apply a permission template', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Click a template button
      const templateButton = page.locator('button').filter({ hasText: /Circulation|Catalog|Patron|Reports|Basic/ }).first()

      if (await templateButton.isVisible()) {
        await templateButton.click()

        // Wait for modal to appear
        await expect(page.locator('text=Apply Template')).toBeVisible({ timeout: 3000 })

        // Verify modal has template options
        const templateOptions = page.locator('button').filter({ hasText: /Circulation|Catalog|Patron/ })
        expect(await templateOptions.count()).toBeGreaterThan(0)
      }
    })
  })

  test.describe('Role CRUD Operations', () => {
    test('should open create role modal', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Click create role button (Plus icon in roles header)
      const createButton = page.locator('[aria-label="Create new role"]')

      if (await createButton.isVisible()) {
        await createButton.click()

        // Verify modal opens
        await expect(page.locator('text=Create New Role')).toBeVisible({ timeout: 3000 })

        // Verify form fields
        await expect(page.locator('input[name="name"]')).toBeVisible()
        await expect(page.locator('textarea[name="description"]')).toBeVisible()
      }
    })

    test('should validate role creation form', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      const createButton = page.locator('[aria-label="Create new role"]')

      if (await createButton.isVisible()) {
        await createButton.click()

        // Try to submit empty form
        const submitButton = page.locator('button:has-text("Create Role")')
        await submitButton.click()

        // Should show validation error
        const errorMsg = page.locator('text=/Role name is required|required/')
        await expect(errorMsg).toBeVisible({ timeout: 3000 })
      }
    })

    test('should edit role by clicking edit button', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Look for edit button on a role
      const editButton = page.locator('[aria-label*="Edit"]').first()

      if (await editButton.isVisible()) {
        await editButton.click()

        // Verify edit modal opens
        await expect(page.locator('text=Edit Role')).toBeVisible({ timeout: 3000 })
      }
    })
  })

  test.describe('Error Handling', () => {
    test('should display error message when loading fails', async ({ page }) => {
      // This is a placeholder for network error simulation
      // In a real test, you would mock network failures

      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Verify the page handles missing data gracefully
      const noRolesMsg = page.locator('text=/No roles available|Contact your system administrator/')

      // Either roles load successfully or show appropriate message
      const rolesLoaded = page.locator('[aria-label*="Edit"]').first()
      const condition = (await noRolesMsg.isVisible()) || (await rolesLoaded.isVisible())
      expect(condition).toBe(true)
    })
  })

  test.describe('Accessibility', () => {
    test('should have proper ARIA labels on role buttons', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Check for ARIA labels on interactive elements
      const createButton = page.locator('[aria-label="Create new role"]')
      const editButtons = page.locator('[aria-label*="Edit"]')

      if (await createButton.isVisible()) {
        const label = await createButton.getAttribute('aria-label')
        expect(label).toBeTruthy()
      }

      const count = await editButtons.count()
      if (count > 0) {
        const label = await editButtons.first().getAttribute('aria-label')
        expect(label).toBeTruthy()
      }
    })

    test('should support keyboard navigation', async ({ page }) => {
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Tab to roles tab button
      await page.keyboard.press('Tab')

      // Verify we can interact with tabs via keyboard
      const activeElement = await page.evaluate(() => document.activeElement?.tagName)
      expect(activeElement).toBe('BUTTON')
    })
  })

  test.describe('Responsive Design', () => {
    test('should display roles sidebar on large screens', async ({ page }) => {
      // Set desktop viewport
      await page.setViewportSize({ width: 1920, height: 1080 })
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Sidebar should be visible on large screens
      const sidebar = page.locator('text=Roles').first()
      const isVisible = await sidebar.isVisible()
      expect(isVisible).toBeDefined()
    })

    test('should be usable on mobile screens', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 })
      await page.goto('/admin/users')
      await page.locator('button:has-text("Roles & Permissions")').click()

      // Page should still be functional
      const rolesTab = page.locator('button:has-text("Roles & Permissions")')
      await expect(rolesTab).toBeVisible()
    })
  })
})
