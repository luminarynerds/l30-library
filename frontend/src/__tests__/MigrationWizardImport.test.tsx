import { describe, it, expect } from 'vitest'
import { mergeMappingFromPlan } from '@/pages/MigrationWizardPage'

describe('mergeMappingFromPlan', () => {
  it('applies plan mapping for present columns and reports drift', () => {
    const detected = ['cardnumber', 'surname', 'new_col']
    const planMapping = { cardnumber: 'barcode', surname: 'last_name', gone_col: 'email' }
    const { mapping, missingFromFile, unmappedColumns } = mergeMappingFromPlan(detected, planMapping)
    expect(mapping).toEqual({ cardnumber: 'barcode', surname: 'last_name' })
    expect(missingFromFile).toEqual(['gone_col'])
    expect(unmappedColumns).toEqual(['new_col'])
  })
})
