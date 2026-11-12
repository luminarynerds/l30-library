/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useId } from "react"
import { Plus, Edit, X, Check } from "lucide-react"
import toast from "react-hot-toast"
import AcquisitionErrorBoundary from "../../components/acquisition/AcquisitionErrorBoundary"
import BudgetIntelligence from "../../components/acquisition/BudgetIntelligence"
import { type Fund, apiFetch, formatMoney } from "./types"
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface FundsTabProps {
  token: string
  funds: Fund[]
  loadData: () => void
}

export default function FundsTab({ token, funds, loadData }: FundsTabProps) {
  const [showFundForm, setShowFundForm] = useState(false)
  const [editingFund, setEditingFund] = useState<Fund | null>(null)
  const [fundForm, setFundForm] = useState({ code: "", name: "", fiscal_year: 2026, allocated_amount: 0 })
  const codeId = useId()
  const nameId = useId()
  const fiscalYearId = useId()
  const allocatedId = useId()

  const handleSaveFund = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    try {
      if (editingFund) {
        await apiFetch(token, "/funds/" + editingFund.id, { method: "PATCH", body: JSON.stringify(fundForm) })
        toast.success(t('toast.acquisitionFunds.fundUpdated'))
      } else {
        await apiFetch(token, "/funds", { method: "POST", body: JSON.stringify(fundForm) })
        toast.success(t('toast.acquisitionFunds.fundCreated'))
      }
      setShowFundForm(false)
      setEditingFund(null)
      loadData()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  return (
    <>
      <div className="space-y-4">
        <div className="flex justify-between items-center"><h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Budget Funds</h2><button onClick={() => { setEditingFund(null); setFundForm({ code: "", name: "", fiscal_year: 2026, allocated_amount: 0 }); setShowFundForm(true) }} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"><Plus aria-hidden="true" className="w-4 h-4" />Add Fund</button></div>
        {funds.length === 0 ? <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">No funds yet</p> : <div className="grid gap-4">{funds.map((fund) => (<div key={fund.id} className="border border-lsc-border dark:border-earth-700 rounded-xl p-4"><div className="flex justify-between items-start"><div><div className="flex items-center gap-2"><span className="font-mono text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{fund.code}</span><span className="px-2 py-0.5 text-xs font-medium rounded bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700">{fund.status}</span></div><h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{fund.name}</h3><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">FY {fund.fiscal_year}</p></div><button onClick={() => { setEditingFund(fund); setFundForm({ code: fund.code, name: fund.name, fiscal_year: fund.fiscal_year, allocated_amount: fund.allocated_amount }); setShowFundForm(true) }} className="p-2 text-lsc-dark/70 hover:text-lsc-rose rounded-xl" aria-label={`Edit fund ${fund.name}`}><Edit aria-hidden="true" className="w-4 h-4" /></button></div><div className="mt-4 grid grid-cols-4 gap-4 text-sm"><div><p className="text-lsc-dark/70 dark:text-lsc-cream/70">Allocated</p><p className="font-semibold text-lsc-dark dark:text-lsc-cream">{formatMoney(fund.allocated_amount)}</p></div><div><p className="text-lsc-dark/70 dark:text-lsc-cream/70">Encumbered</p><p className="font-semibold text-lsc-rose">{formatMoney(fund.encumbered_amount)}</p></div><div><p className="text-lsc-dark/70 dark:text-lsc-cream/70">Spent</p><p className="font-semibold text-lsc-rose">{formatMoney(fund.spent_amount)}</p></div><div><p className="text-lsc-dark/70 dark:text-lsc-cream/70">Available</p><p className="font-semibold text-lsc-rose dark:text-lsc-rose-light">{formatMoney(fund.available_amount)}</p></div></div><div className="mt-3 h-2 bg-lsc-cream rounded-full overflow-hidden" role="progressbar" aria-label={`Budget usage for ${fund.name}`} aria-valuenow={Number(fund.allocated_amount) > 0 ? Math.round(((Number(fund.spent_amount) + Number(fund.encumbered_amount)) / Number(fund.allocated_amount)) * 100) : 0} aria-valuemin={0} aria-valuemax={100}><div className="h-full flex"><div className="bg-lsc-rose/30" style={{ width: (Number(fund.allocated_amount) > 0 ? (Number(fund.spent_amount) / Number(fund.allocated_amount)) * 100 : 0) + "%" }} /><div className="bg-lsc-rose" style={{ width: (Number(fund.allocated_amount) > 0 ? (Number(fund.encumbered_amount) / Number(fund.allocated_amount)) * 100 : 0) + "%" }} /></div></div></div>))}</div>}
        <AcquisitionErrorBoundary fallbackMessage="Failed to load budget intelligence">
          <BudgetIntelligence token={token || ""} formatMoney={formatMoney} />
        </AcquisitionErrorBoundary>
      </div>

      {showFundForm && <ModalBackdrop onClose={() => setShowFundForm(false)} labelledBy="fund-modal-title"><div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md"><div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between"><h2 id="fund-modal-title" className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{editingFund ? "Edit Fund" : "Add Fund"}</h2><button onClick={() => setShowFundForm(false)} className="p-2 text-lsc-dark/70 hover:text-lsc-dark/70 rounded-xl" aria-label={t('aria.fundsTab.closeFundForm')}><X aria-hidden="true" className="w-5 h-5" /></button></div><form onSubmit={handleSaveFund} className="p-6 space-y-4"><div><label htmlFor={codeId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Code *</label><input id={codeId} type="text" value={fundForm.code} onChange={(e) => setFundForm({ ...fundForm, code: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required /></div><div><label htmlFor={nameId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Name *</label><input id={nameId} type="text" value={fundForm.name} onChange={(e) => setFundForm({ ...fundForm, name: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required /></div><div className="grid grid-cols-2 gap-4"><div><label htmlFor={fiscalYearId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Fiscal Year</label><input id={fiscalYearId} type="number" value={fundForm.fiscal_year} onChange={(e) => setFundForm({ ...fundForm, fiscal_year: parseInt(e.target.value) })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /></div><div><label htmlFor={allocatedId} className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Allocated</label><input id={allocatedId} type="number" step="0.01" value={fundForm.allocated_amount} onChange={(e) => setFundForm({ ...fundForm, allocated_amount: parseFloat(e.target.value) })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /></div></div><div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700"><button type="button" onClick={() => setShowFundForm(false)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl font-medium">Cancel</button><button type="submit" className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2"><Check aria-hidden="true" className="w-4 h-4" />Save</button></div></form></div></ModalBackdrop>}
    </>
  )
}
