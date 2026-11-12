/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Common legal glossary terms and definitions
export interface GlossaryTerm {
  term: string
  definition: string
  abbreviation?: string
}

const LEGAL_GLOSSARY_TERMS: GlossaryTerm[] = [
  {
    term: 'Plaintiff',
    definition:
      'The person or party who initiates a lawsuit by filing a complaint against another party (the defendant).',
  },
  {
    term: 'Defendant',
    definition:
      'The person or party being sued or accused in a court of law; the party being prosecuted in a criminal case.',
  },
  {
    term: 'Eviction',
    definition:
      'The legal process by which a landlord removes a tenant from a rental property, typically for non-payment of rent or lease violation.',
  },
  {
    term: 'Lease',
    definition:
      'A legal contract between a landlord and tenant that outlines the terms and conditions of rental, including rent amount, duration, and rules.',
  },
  {
    term: 'Damages',
    definition:
      'Money compensation awarded by a court to a party who has suffered loss or injury due to the unlawful actions of another.',
  },
  {
    term: 'Settlement',
    definition:
      'An agreement reached between parties in a dispute to resolve the matter outside of court, often involving payment or concessions.',
  },
  {
    term: 'Jurisdiction',
    definition:
      'The legal authority of a court to hear and decide a case; determined by factors like location, subject matter, and parties involved.',
  },
  {
    term: 'Liability',
    definition:
      'Legal responsibility for one\'s actions or omissions; the state of being held accountable for damages or injuries caused.',
  },
  {
    term: 'Affidavit',
    definition:
      'A written statement made under oath before a notary public or authorized officer, used as evidence in legal proceedings.',
  },
  {
    term: 'Due Process',
    definition:
      'The legal requirement that the state must respect all legal rights owed to a person, including fair treatment and proper procedures.',
  },
  {
    term: 'Summons',
    definition:
      'A court order notifying a defendant that they have been sued and must appear in court to respond to the charges.',
  },
  {
    term: 'Subpoena',
    definition:
      'A court order requiring a person to testify in court or produce documents and other evidence for use in legal proceedings.',
  },
  {
    term: 'Perjury',
    definition:
      'The act of intentionally lying or providing false testimony under oath in court or in a legal proceeding.',
  },
  {
    term: 'Testimony',
    definition:
      'A statement made under oath by a witness in court describing what they know about the facts of a case.',
  },
  {
    term: 'Appeal',
    definition:
      'A formal request to a higher court to review and reconsider a decision made by a lower court.',
  },
  {
    term: 'Pro Bono',
    definition:
      'Professional work undertaken voluntarily and without charge, often referring to legal services provided for the public good.',
  },
  {
    term: 'Mediation',
    definition:
      'A dispute resolution process where a neutral third party (mediator) helps two parties reach a mutual agreement.',
  },
  {
    term: 'Arbitration',
    definition:
      'A dispute resolution process where a neutral arbitrator hears evidence and makes a binding decision to resolve a dispute.',
  },
  {
    term: 'Custody',
    definition:
      'Legal responsibility for the care and control of a child or incompetent person, including decisions about upbringing and welfare.',
  },
  {
    term: 'Child Support',
    definition:
      'Court-ordered payments made by a non-custodial parent to the custodial parent to help support the financial needs of a child.',
  },
]

export function useGlossaryTerms() {
  const getTermDefinition = (termName: string): string | undefined => {
    const term = LEGAL_GLOSSARY_TERMS.find(
      (t) => t.term.toLowerCase() === termName.toLowerCase()
    )
    return term?.definition
  }

  const getAllTerms = () => LEGAL_GLOSSARY_TERMS

  const searchTerms = (query: string) => {
    const lowerQuery = query.toLowerCase()
    return LEGAL_GLOSSARY_TERMS.filter(
      (t) =>
        t.term.toLowerCase().includes(lowerQuery) ||
        t.definition.toLowerCase().includes(lowerQuery) ||
        t.abbreviation?.toLowerCase().includes(lowerQuery)
    )
  }

  return {
    getTermDefinition,
    getAllTerms,
    searchTerms,
  }
}
