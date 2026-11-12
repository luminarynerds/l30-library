/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface LibraryContact {
  address_line1: string
  address_line2: string
  city: string
  state: string
  zip_code: string
  phone: string
}

export interface BranchContact extends Partial<Record<keyof LibraryContact, string | null>> {
  branch_type: string
}

/** Branch records describe the place patrons visit. Keep its address together,
 * rather than combining a branch street with a different branding locality. */
export function resolveLibraryContact(branding: LibraryContact, branches?: BranchContact[]): LibraryContact {
  const branch = branches?.find((item) => item.branch_type === 'main') ?? branches?.[0]
  if (!branch) return branding
  const address = branch.address_line1 ? branch : branding
  return {
    address_line1: address.address_line1 ?? '',
    address_line2: address.address_line2 ?? '',
    city: address.city ?? '',
    state: address.state ?? '',
    zip_code: address.zip_code ?? '',
    phone: branch.phone || branding.phone,
  }
}
