/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test as setup } from "@playwright/test"
import fs from "fs"
import path from "path"
import { fileURLToPath } from "url"
import { API_BASE, API_PREFIX, PERSONAS } from "./smoke.config"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const AUTH_DIR = path.join(__dirname, ".auth")

setup("authenticate smoke personas", async () => {
  fs.mkdirSync(AUTH_DIR, { recursive: true })

  const entries = Object.entries(PERSONAS)
  for (let i = 0; i < entries.length; i++) {
    const [name, creds] = entries[i]
    // Stagger logins to avoid rate limiting (10/min on login endpoint)
    if (i > 0) await new Promise((r) => setTimeout(r, 1500))
    try {
      const res = await fetch(`${API_BASE}${API_PREFIX}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: creds.email, password: creds.password }),
      })

      if (!res.ok) {
        console.warn(`Smoke auth for ${name} failed: ${res.status}`)
        fs.writeFileSync(
          path.join(AUTH_DIR, `${name}.json`),
          JSON.stringify({ cookies: [], origins: [] }),
        )
        continue
      }

      const data = await res.json()
      const cookies: Array<Record<string, unknown>> = []

      const setCookies = res.headers.getSetCookie?.() || []
      for (const cookie of setCookies) {
        const [nameValue] = cookie.split(";")
        const [cookieName, cookieValue] = nameValue.split("=")
        cookies.push({
          name: cookieName.trim(),
          value: cookieValue.trim(),
          domain: "localhost",
          path: "/",
          httpOnly: true,
          secure: false,
          sameSite: "Lax",
        })
      }

      const storageState = {
        cookies,
        origins: [
          {
            origin: API_BASE,
            localStorage: [
              { name: "access_token", value: data.access_token || "" },
              { name: "user", value: JSON.stringify(data.user || {}) },
            ],
          },
        ],
      }

      fs.writeFileSync(
        path.join(AUTH_DIR, `${name}.json`),
        JSON.stringify(storageState, null, 2),
      )
      console.log(`Smoke auth for ${name}: OK`)
    } catch (err) {
      console.warn(`Smoke auth for ${name} error: ${err}`)
      fs.writeFileSync(
        path.join(AUTH_DIR, `${name}.json`),
        JSON.stringify({ cookies: [], origins: [] }),
      )
    }
  }
})
