'use client'

import { ReactNode } from 'react'

export type FieldSuggestion = {
  value: unknown
  confidence: number | null
  source: string | null
  warnings: string[]
}

export type VoucherData = {
  id: string
  farm_id: string
  file_name: string
  content_type: string
  status: string
  amount: number
  account_code: string | null
  mva_code: string | null
  voucher_date: string
  description: string | null
  supplier_name: string | null
  supplier_org_number: string | null
  invoice_number: string | null
  due_date: string | null
  amount_excluding_vat: number | null
  vat_amount: number | null
  currency: string
  kid: string | null
  bank_account: string | null
  document_type: string
  field_suggestions: Record<string, FieldSuggestion | null>
  ocr_warnings: string[]
  extraction_status: string | null
}

export type VoucherFormState = {
  document_type: string
  supplier_name: string
  supplier_org_number: string
  invoice_number: string
  voucher_date: string
  due_date: string
  description: string
  amount: string
  amount_excluding_vat: string
  vat_amount: string
  currency: string
  kid: string
  bank_account: string
  account_code: string
  mva_code: string
  transaction_type: 'expense' | 'income'
}

export const CONFIDENCE_THRESHOLD = 0.85

export const SUGGESTION_MAP: Partial<Record<keyof VoucherFormState, string>> = {
  supplier_name: 'supplier_name',
  supplier_org_number: 'org_number',
  invoice_number: 'invoice_number',
  voucher_date: 'invoice_date',
  due_date: 'due_date',
  amount: 'amount_total',
  vat_amount: 'amount_vat',
  currency: 'currency',
  kid: 'kid',
  bank_account: 'bank_account',
}

export const REQUIRED_FIELDS: Array<keyof VoucherFormState> = ['amount', 'voucher_date', 'description', 'account_code']

export const STATUS_LABELS: Record<string, string> = {
  mottatt: 'Mottatt',
  needs_review: 'Trenger kontroll',
  ready: 'Klar for bokføring',
  ført: 'Ført',
}

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  invoice: 'Faktura',
  receipt: 'Kvittering',
}

export const MVA_CODE_LABELS: Record<string, string> = {
  '25': '25 %',
  '15': '15 %',
  '12': '12 %',
  '0': '0 %',
  fradrag: 'Fradragsberettiget',
}

export const inputBase = 'w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-bonde-green/40'

export function inputClass(needsReview: boolean, disabled?: boolean): string {
  const base = `${inputBase} ${needsReview ? 'border-amber-400 bg-amber-50' : 'border-stone-300 bg-white'}`
  return disabled ? `${base} opacity-60 cursor-not-allowed` : base
}

export function FieldLabel({ label, needsReview }: { label: string; needsReview: boolean }) {
  return (
    <div className="flex items-center justify-between gap-2 mb-1">
      <label className="block text-xs uppercase tracking-wider text-stone-600 font-semibold">{label}</label>
      {needsReview && (
        <span className="shrink-0 text-[11px] font-semibold bg-amber-100 text-amber-800 border border-amber-300 rounded-full px-2 py-0.5">
          Kontroller
        </span>
      )}
    </div>
  )
}

export function parseAmount(value: string): number {
  const normalized = value.replace(/\s/g, '').replace(',', '.')
  if (!normalized) return NaN
  return Number(normalized)
}

export function parseOptionalNumber(value: string): number | undefined {
  const trimmed = value.trim()
  if (!trimmed) return undefined
  const parsed = parseAmount(trimmed)
  return Number.isFinite(parsed) ? parsed : undefined
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return ''
  return String(value)
}

export function formFromVoucher(voucher: VoucherData): VoucherFormState {
  return {
    document_type: voucher.document_type || 'invoice',
    supplier_name: voucher.supplier_name || '',
    supplier_org_number: voucher.supplier_org_number || '',
    invoice_number: voucher.invoice_number || '',
    voucher_date: voucher.voucher_date || new Date().toISOString().slice(0, 10),
    due_date: voucher.due_date || '',
    description: voucher.description || '',
    amount: voucher.amount ? String(voucher.amount) : formatNumber(voucher.field_suggestions?.amount_total?.value as number | null | undefined) || '',
    amount_excluding_vat: formatNumber(voucher.amount_excluding_vat),
    vat_amount: formatNumber(voucher.vat_amount),
    currency: voucher.currency || 'NOK',
    kid: voucher.kid || '',
    bank_account: voucher.bank_account || '',
    account_code: voucher.account_code || '',
    mva_code: voucher.mva_code || '25',
    transaction_type: 'expense',
  }
}

export function fieldNeedsReview(
  key: keyof VoucherFormState,
  form: VoucherFormState,
  voucher: VoucherData | null,
  touched: Set<string>,
  isBooked: boolean
): boolean {
  if (!voucher || isBooked) return false
  if (touched.has(key)) return false
  const value = String(form[key] ?? '').trim()
  const suggestionKey = SUGGESTION_MAP[key]

  if (suggestionKey) {
    const suggestion = voucher.field_suggestions?.[suggestionKey]
    if (!value) return true
    if (suggestion) {
      if (suggestion.warnings && suggestion.warnings.length > 0) return true
      if (typeof suggestion.confidence === 'number' && suggestion.confidence < CONFIDENCE_THRESHOLD) return true
    }
    return false
  }

  if (REQUIRED_FIELDS.includes(key) && !value) return true
  return false
}

export function buildPatchPayload(form: VoucherFormState): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    voucher_date: form.voucher_date,
    description: form.description,
    supplier_name: form.supplier_name,
    supplier_org_number: form.supplier_org_number,
    invoice_number: form.invoice_number,
    due_date: form.due_date,
    currency: form.currency.trim() || 'NOK',
    kid: form.kid,
    bank_account: form.bank_account,
    document_type: form.document_type,
    account_code: form.account_code,
    mva_code: form.mva_code,
  }
  const amountExcl = parseOptionalNumber(form.amount_excluding_vat)
  if (amountExcl !== undefined) payload.amount_excluding_vat = amountExcl
  const vatAmount = parseOptionalNumber(form.vat_amount)
  if (vatAmount !== undefined) payload.vat_amount = vatAmount
  return payload
}

export function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat('nb-NO', { style: 'currency', currency: currency || 'NOK' }).format(amount)
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '–'
  try {
    const date = new Date(dateStr + 'T00:00:00')
    return date.toLocaleDateString('nb-NO', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return dateStr
  }
}

export function StatusBadge({ status }: { status: string }) {
  const label = STATUS_LABELS[status] || status
  const colorClass =
    status === 'ført'
      ? 'bg-emerald-100 text-emerald-800'
      : status === 'needs_review'
        ? 'bg-amber-100 text-amber-800'
        : status === 'ready'
          ? 'bg-blue-100 text-blue-800'
          : 'bg-stone-100 text-stone-700'
  return <span className={`px-2 py-1 rounded-full text-xs font-semibold ${colorClass}`}>{label}</span>
}

export function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex justify-between items-start py-2 border-b border-stone-100 last:border-b-0">
      <span className="text-xs uppercase tracking-wider text-stone-500 font-semibold">{label}</span>
      <span className="text-sm text-stone-900 text-right">{children}</span>
    </div>
  )
}