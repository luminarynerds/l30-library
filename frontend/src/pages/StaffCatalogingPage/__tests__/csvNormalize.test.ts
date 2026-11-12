/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from "vitest"
import { normalizeItemType, normalizeStatus } from "../CsvImportExportPanel"

describe("normalizeItemType", () => {
  it("accepts canonical lowercase values", () => {
    expect(normalizeItemType("book")).toBe("book")
    expect(normalizeItemType("dvd")).toBe("dvd")
  })
  it("lowercases mixed/upper case", () => {
    expect(normalizeItemType("Book")).toBe("book")
    expect(normalizeItemType("DVD")).toBe("dvd")
  })
  it("maps common aliases", () => {
    expect(normalizeItemType("Blu-ray")).toBe("bluray")
    expect(normalizeItemType("e-book")).toBe("ebook")
    expect(normalizeItemType("Paperback")).toBe("book")
    expect(normalizeItemType("Video Game")).toBe("game")
  })
  it("returns empty string for blank so the caller can default", () => {
    expect(normalizeItemType("")).toBe("")
    expect(normalizeItemType("   ")).toBe("")
  })
  it("returns null for genres / unmappable values (e.g. Fiction)", () => {
    expect(normalizeItemType("Fiction")).toBeNull()
    expect(normalizeItemType("Nonfiction")).toBeNull()
  })
})

describe("normalizeStatus", () => {
  it("lowercases canonical values", () => {
    expect(normalizeStatus("Available")).toBe("available")
    expect(normalizeStatus("available")).toBe("available")
  })
  it("collapses spaces and hyphens to underscores", () => {
    expect(normalizeStatus("On Hold")).toBe("on_hold")
    expect(normalizeStatus("checked-out")).toBe("checked_out")
  })
  it("returns empty string for blank", () => {
    expect(normalizeStatus("")).toBe("")
  })
  it("returns null for unmappable values", () => {
    expect(normalizeStatus("Borrowed")).toBeNull()
  })
})
