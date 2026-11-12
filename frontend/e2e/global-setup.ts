/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { type FullConfig } from '@playwright/test'
import fs from 'fs'
import path from 'path'

const API_BASE = process.env.VITE_API_BASE

const TEST_USERS = {
  admin: { email: 'admin@l30.org', password: 'Admin123!' },
  staff: { email: 'staff.main@l30.org', password: 'Admin123!' },
  patron: { email: 'patron.good-standing@l30.org', password: 'Admin123!' },
}

async function globalSetup(config: FullConfig) {
  // Skip global auth setup when VITE_API_BASE is not set (e.g., smoke-only runs)
  if (!API_BASE) {
    console.warn('VITE_API_BASE not set — skipping global auth setup')
    return
  }

  const baseURL = config.projects[0]?.use?.baseURL || 'http://localhost:5173'
  const apiBase = process.env.API_URL || 'http://localhost:8000'
  const authDir = path.join(process.cwd(), 'e2e', '.auth')
  fs.mkdirSync(authDir, { recursive: true })

  for (const [role, creds] of Object.entries(TEST_USERS)) {
    try {
      const res = await fetch(`${apiBase}${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: creds.email, password: creds.password }),
      })

      if (!res.ok) {
        console.warn(`Auth setup for ${role} failed: ${res.status}`)
        fs.writeFileSync(
          path.join(authDir, `${role}.json`),
          JSON.stringify({ cookies: [], origins: [] })
        )
        continue
      }

      const data = await res.json()
      const cookies: any[] = []

      const setCookies = res.headers.getSetCookie?.() || []
      for (const cookie of setCookies) {
        const [nameValue] = cookie.split(';')
        const [name, value] = nameValue.split('=')
        cookies.push({
          name: name.trim(),
          value: value.trim(),
          domain: new URL(baseURL).hostname,
          path: '/',
          httpOnly: true,
          secure: false,
          sameSite: 'Lax' as const,
        })
      }

      const storageState = {
        cookies,
        origins: [
          {
            origin: baseURL,
            localStorage: [
              { name: 'access_token', value: data.access_token || '' },
              { name: 'user', value: JSON.stringify(data.user || {}) },
            ],
          },
        ],
      }

      fs.writeFileSync(
        path.join(authDir, `${role}.json`),
        JSON.stringify(storageState, null, 2)
      )
      console.log(`Auth setup for ${role}: OK`)
    } catch (err) {
      console.warn(`Auth setup for ${role} error: ${err}`)
      fs.writeFileSync(
        path.join(authDir, `${role}.json`),
        JSON.stringify({ cookies: [], origins: [] })
      )
    }
  }
}

export default globalSetup
