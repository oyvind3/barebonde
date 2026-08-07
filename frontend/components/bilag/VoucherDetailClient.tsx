'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { apiErrorMessage, apiFetch, bootstrapIdentity } from '@/lib/api'
import {
  VoucherData,
  VoucherFormState,
  formFromVoucher,
  fieldNeedsReview,
  buildPatchPayload,
  parseAmount,
  formatCurrency,
  formatDate,
  inputClass,
  FieldLabel,
  StatusBadge,
  DetailRow,
  DOCUMENT_TYPE_LABELS,
  MVA_CODE_LABELS,
} from '@/components/bilag/VoucherFields'

type Account = {
  code: string
  name: string
  category: string
  simple: boolean
}

const FARM_ID_KEY = 'barebonde_active_farm_id'

type VoucherDetailClientProps = {
  voucherId: string
}

export default function VoucherDetailClient({ voucherId }: VoucherDetailClientProps) {

  const [authReady, setAuthReady] = useState(false)
  const [farmId, setFarmId] = useState('')
  const [voucher, setVoucher] = useState<VoucherData | null>(null)
  const [form, setForm] = useState<VoucherFormState | null>(null)
  const [touched, setTouched] = useState<Set<string>>(new Set())

  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const [documentUrl, setDocumentUrl] = useState('')
  const [documentContentType, setDocumentContentType] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState('')

  const [accounts, setAccounts] = useState<Account[]>([])
  const [simpleMode] = useState(true)

  const isBooked = voucher?.status === 'ført'

  const [correctionOpen, setCorrectionOpen] = useState(false)
  const [correctionSaving, setCorrectionSaving] = useState(false)
  const [correctionError, setCorrectionError] = useState('')
  const [correction, setCorrection] = useState({
    account_code: '',
    mva_code: '25',
    amount: '',
    correction_date: new Date().toISOString().slice(0, 10),
    reason: '',
  })

  const submitCorrection = async () => {
    if (!voucher || !farmId || correctionSaving) return
    setCorrectionError('')
    const parsedAmount = parseAmount(correction.amount)
    if (!correction.account_code || !Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setCorrectionError('Konto og gyldig beløp er påkrevd.')
      return
    }
    if (!correction.reason.trim()) {
      setCorrectionError('Begrunnelse er påkrevd.')
      return
    }
    setCorrectionSaving(true)
    try {
      const response = await apiFetch(
        `/api/farms/${encodeURIComponent(farmId)}/vouchers/${encodeURIComponent(voucherId)}/correct-booking`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            account_code: correction.account_code,
            mva_code: correction.mva_code,
            transaction_type: 'expense',
            amount: parsedAmount,
            correction_date: correction.correction_date,
            reason: correction.reason.trim(),
          }),
        }
      )
      if (!response.ok) {
        throw new Error(await apiErrorMessage(response, 'Kunne ikke korrigere bokføringen.'))
      }
      const updated = (await response.json()) as VoucherData
      setVoucher(updated)
      setForm(formFromVoucher(updated))
      setCorrectionOpen(false)
      setMessage('Bokføringen er korrigert med en ny journalpost.')
    } catch (err) {
      setCorrectionError(err instanceof Error ? err.message : 'Ukjent feil ved korrigering.')
    } finally {
      setCorrectionSaving(false)
    }
  }

  // --- Identity / Farm scope ---
  useEffect(() => {
    const storedFarmId = window.localStorage.getItem(FARM_ID_KEY) || ''
    bootstrapIdentity(storedFarmId)
      .then((identity) => {
        const activeFarmId = identity?.active_farm?.id || ''
        setFarmId(activeFarmId)
        if (activeFarmId) window.localStorage.setItem(FARM_ID_KEY, activeFarmId)
        else window.localStorage.removeItem(FARM_ID_KEY)
      })
      .catch(() => setFarmId(''))
      .finally(() => setAuthReady(true))
  }, [])

  // --- Account catalog (for edit mode) ---
  useEffect(() => {
    if (!editing && !correctionOpen) return
    let cancelled = false
    const run = async () => {
      try {
        const response = await apiFetch(`/api/accounting/accounts?query=&simple_mode=${simpleMode}`)
        if (!response.ok) return
        const data = await response.json()
        if (cancelled) return
        setAccounts(data.accounts || [])
      } catch {
        // Account catalog is supplementary.
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [editing, correctionOpen, simpleMode])

  // --- Fetch voucher ---
  useEffect(() => {
    if (!farmId || !voucherId) return
    const controller = new AbortController()
    const run = async () => {
      setLoading(true)
      setLoadError('')
      try {
        const response = await apiFetch(
          `/api/farms/${encodeURIComponent(farmId)}/vouchers/${encodeURIComponent(voucherId)}`,
          { signal: controller.signal }
        )
        if (!response.ok) {
          throw new Error(await apiErrorMessage(response, 'Kunne ikke hente bilaget.'))
        }
        const data = (await response.json()) as VoucherData
        setVoucher(data)
        setForm(formFromVoucher(data))
        setTouched(new Set())
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        setLoadError(err instanceof Error ? err.message : 'Ukjent feil')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    run()
    return () => controller.abort()
  }, [farmId, voucherId])

  // --- Document preview ---
  const loadDocumentPreview = useCallback(
    async (farm: string, id: string) => {
      setPreviewLoading(true)
      setPreviewError('')
      try {
        const response = await apiFetch(`/api/farms/${encodeURIComponent(farm)}/documents/${encodeURIComponent(id)}/download`)
        if (!response.ok) {
          setPreviewError(await apiErrorMessage(response, 'Kunne ikke hente dokumentet.'))
          return
        }
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        setDocumentUrl((previous) => {
          if (previous) URL.revokeObjectURL(previous)
          return url
        })
        setDocumentContentType(blob.type || '')
      } catch (err) {
        setPreviewError(err instanceof Error ? err.message : 'Kunne ikke hente dokumentet.')
      } finally {
        setPreviewLoading(false)
      }
    },
    []
  )

  useEffect(() => {
    if (farmId && voucherId) {
      void loadDocumentPreview(farmId, voucherId)
    }
  }, [farmId, voucherId, loadDocumentPreview])

  useEffect(() => {
    return () => {
      if (documentUrl) URL.revokeObjectURL(documentUrl)
    }
  }, [documentUrl])

  const setField = (key: keyof VoucherFormState, value: string) => {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev))
    setTouched((prev) => {
      const next = new Set(prev)
      next.add(key)
      return next
    })
  }

  const reviewCount = useMemo(() => {
    if (!voucher || !form || isBooked) return 0
    return (Object.keys(form) as Array<keyof VoucherFormState>).filter((key) =>
      fieldNeedsReview(key, form, voucher, touched, isBooked)
    ).length
  }, [voucher, form, touched, isBooked])

  const startEditing = () => {
    if (!voucher) return
    setForm(formFromVoucher(voucher))
    setTouched(new Set())
    setEditing(true)
    setMessage('')
    setError('')
  }

  const cancelEditing = () => {
    if (voucher) setForm(formFromVoucher(voucher))
    setTouched(new Set())
    setEditing(false)
    setMessage('')
    setError('')
  }

  const handleSave = async () => {
    if (!voucher || !form || !farmId || saving) return
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const payload = buildPatchPayload(form)

      // Only include amount for unbooked vouchers (locked when booked).
      if (!isBooked) {
        const parsedAmount = parseAmount(form.amount)
        if (Number.isFinite(parsedAmount) && parsedAmount > 0) {
          payload.amount = parsedAmount
        }
      }

      // For booked vouchers, do not send locked fields at all to avoid 409.
      if (isBooked) {
        delete payload.voucher_date
        delete payload.account_code
        delete payload.mva_code
      }

      const response = await apiFetch(
        `/api/farms/${encodeURIComponent(farmId)}/vouchers/${encodeURIComponent(voucherId)}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        }
      )
      if (!response.ok) {
        throw new Error(await apiErrorMessage(response, 'Kunne ikke lagre endringene.'))
      }
      const updated = (await response.json()) as VoucherData
      setVoucher(updated)
      setForm(formFromVoucher(updated))
      setTouched(new Set())
      setEditing(false)
      setMessage('Endringene er lagret.')
    } catch (err) {
      // Keep the user's edits in the form on failure – do not reset.
      setError(err instanceof Error ? err.message : 'Ukjent feil ved lagring.')
    } finally {
      setSaving(false)
    }
  }

  const isPdfPreview = documentContentType === 'application/pdf'
  const ocrFailed = voucher?.extraction_status === 'failed'

  if (!authReady) {
    return (
      <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
        <Navbar />
        <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full">
          <Card hoverEffect={false} className="p-6 bg-white">
            <p className="text-sm text-stone-600">Henter sesjon...</p>
          </Card>
        </main>
      </div>
    )
  }

  if (!farmId) {
    return (
      <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
        <Navbar />
        <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full">
          <Card hoverEffect={false} className="p-6 bg-white">
            <p className="text-sm text-stone-700">Du må sette opp gård for å se bilag.</p>
            <div className="mt-4">
              <Button href="/farm/setup" variant="outline" showArrow>
                GÅ TIL OPPSETT
              </Button>
            </div>
          </Card>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-serif text-stone-900">Bilag</h1>
            <p className="text-stone-600 text-sm mt-1">{voucher?.file_name || voucherId}</p>
          </div>
          <div className="flex gap-3">
            <Button href="/bilag" variant="outline">
              TIL BILAGSLISTE
            </Button>
          </div>
        </div>

        {loading && (
          <Card hoverEffect={false} className="p-6 bg-white">
            <p className="text-sm text-stone-600">Laster bilag...</p>
          </Card>
        )}

        {!loading && loadError && (
          <Card hoverEffect={false} className="p-6 bg-white">
            <p className="text-sm text-red-700">{loadError}</p>
            <div className="mt-4">
              <Button href="/bilag" variant="outline">
                TILBAKE TIL BILAGSLISTE
              </Button>
            </div>
          </Card>
        )}

        {!loading && !loadError && voucher && form && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
            {/* Document preview */}
            <Card hoverEffect={false} className="p-6 bg-white lg:sticky lg:top-6">
              <div className="flex items-center justify-between gap-3 mb-4">
                <h2 className="text-lg font-semibold text-stone-900">Dokument</h2>
                <StatusBadge status={voucher.status} />
              </div>

              <p className="text-sm text-stone-600 mb-3 truncate">{voucher.file_name}</p>

              {previewLoading && (
                <div className="border border-stone-200 rounded-xl p-8 text-center" role="status">
                  <p className="text-sm text-stone-500">Henter dokument...</p>
                </div>
              )}

              {!previewLoading && previewError && (
                <div className="border border-red-200 bg-red-50 rounded-xl p-6 text-center">
                  <p className="text-sm text-red-700 mb-3">{previewError}</p>
                  <button
                    type="button"
                    onClick={() => farmId && voucherId && void loadDocumentPreview(farmId, voucherId)}
                    className="text-sm font-semibold text-bonde-green hover:underline"
                  >
                    Prøv igjen
                  </button>
                </div>
              )}

              {!previewLoading && !previewError && documentUrl && isPdfPreview && (
                <iframe src={documentUrl} title={voucher.file_name} className="w-full h-[560px] rounded-xl border border-stone-200" />
              )}

              {!previewLoading && !previewError && documentUrl && !isPdfPreview && documentContentType.startsWith('image/') && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={documentUrl} alt={voucher.file_name} className="w-full max-h-[560px] object-contain rounded-xl border border-stone-200 bg-stone-50" />
              )}

              {!previewLoading && !previewError && !documentUrl && (
                <div className="border border-dashed border-stone-300 rounded-xl p-8 text-center">
                  <p className="text-sm text-stone-500">Forhåndsvisning er ikke tilgjengelig for denne filtypen.</p>
                </div>
              )}

              {!previewLoading && !previewError && documentUrl && !isPdfPreview && !documentContentType.startsWith('image/') && (
                <div className="border border-dashed border-stone-300 rounded-xl p-8 text-center">
                  <p className="text-sm text-stone-500 mb-3">Forhåndsvisning er ikke tilgjengelig for denne filtypen.</p>
                  <a
                    href={documentUrl}
                    download={voucher.file_name}
                    className="text-sm font-semibold text-bonde-green hover:underline"
                  >
                    Last ned dokument
                  </a>
                </div>
              )}

              {ocrFailed && (
                <div className="mt-4 rounded-lg bg-amber-50 border border-amber-300 p-3">
                  <p className="text-sm text-amber-800">
                    OCR kunne ikke lese dokumentet automatisk. Feltene må fylles inn manuelt.
                  </p>
                </div>
              )}

              {!ocrFailed && voucher.ocr_warnings.length > 0 && (
                <div className="mt-4 rounded-lg bg-amber-50 border border-amber-300 p-3">
                  <p className="text-sm text-amber-800">OCR er usikker på enkelte felt. Kontroller feltene merket med «Kontroller».</p>
                </div>
              )}
            </Card>

            {/* Details / Edit form */}
            <Card hoverEffect={false} className="p-6 bg-white">
              <div className="flex items-center justify-between gap-3 mb-4">
                <h2 className="text-lg font-semibold text-stone-900">
                  {editing ? 'Rediger bilag' : 'Detaljer'}
                </h2>
                {!editing && (
                  <button
                    type="button"
                    onClick={startEditing}
                    className="text-sm font-semibold text-bonde-green hover:underline"
                  >
                    Rediger
                  </button>
                )}
              </div>

              {isBooked && (
                <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 p-3 space-y-2">
                  <p className="text-sm text-blue-800">
                    Bokført{voucher.journal_number ? ` – journalnr ${voucher.journal_number}` : ''}
                    {typeof voucher.accounting_revision === 'number' && voucher.accounting_revision > 1
                      ? ` (revisjon ${voucher.accounting_revision})`
                      : ''}
                  </p>
                  <p className="text-sm text-blue-800">
                    Dokumentinformasjon kan endres, men beløp, konto og MVA korrigeres med en egen korrigeringspost.
                  </p>
                  <button
                    type="button"
                    onClick={() => setCorrectionOpen((open) => !open)}
                    className="text-sm font-semibold text-blue-800 underline"
                  >
                    {correctionOpen ? 'Lukk korrigering' : 'Korriger bokføring'}
                  </button>
                </div>
              )}

              {isBooked && correctionOpen && (
                <div className="mb-4 rounded-lg border border-stone-200 p-4 space-y-4">
                  <h3 className="text-sm font-semibold text-stone-800">Korriger bokføring</h3>
                  <p className="text-xs text-stone-500">
                    Korrigeringen endrer ikke den opprinnelige journalposten. Barebonde lager en ny
                    korrigeringspost slik at historikken beholdes.
                  </p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <FieldLabel label="Konto" needsReview={false} />
                      <select
                        className={inputClass(false)}
                        value={correction.account_code}
                        onChange={(e) => setCorrection((c) => ({ ...c, account_code: e.target.value }))}
                      >
                        <option value="">Velg konto</option>
                        {accounts.map((account) => (
                          <option key={account.code} value={account.code}>
                            {account.code} – {account.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <FieldLabel label="MVA-kode" needsReview={false} />
                      <select
                        className={inputClass(false)}
                        value={correction.mva_code}
                        onChange={(e) => setCorrection((c) => ({ ...c, mva_code: e.target.value }))}
                      >
                        {Object.entries(MVA_CODE_LABELS).map(([code, label]) => (
                          <option key={code} value={code}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <FieldLabel label="Totalbeløp" needsReview={false} />
                      <input
                        className={inputClass(false)}
                        value={correction.amount}
                        onChange={(e) => setCorrection((c) => ({ ...c, amount: e.target.value }))}
                      />
                    </div>
                    <div>
                      <FieldLabel label="Korrigeringsdato" needsReview={false} />
                      <input
                        type="date"
                        className={inputClass(false)}
                        value={correction.correction_date}
                        onChange={(e) => setCorrection((c) => ({ ...c, correction_date: e.target.value }))}
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <FieldLabel label="Begrunnelse (påkrevd)" needsReview={false} />
                      <input
                        className={inputClass(false)}
                        value={correction.reason}
                        onChange={(e) => setCorrection((c) => ({ ...c, reason: e.target.value }))}
                      />
                    </div>
                  </div>
                  {correctionError && <p className="text-sm text-red-600">{correctionError}</p>}
                  <Button variant="secondary" onClick={submitCorrection} disabled={correctionSaving}>
                    {correctionSaving ? 'Korrigerer…' : 'Send korrigering'}
                  </Button>
                </div>
              )}

              {editing && reviewCount > 0 && !isBooked && (
                <div className="mb-4 rounded-lg bg-amber-50 border border-amber-300 p-3">
                  <p className="text-sm text-amber-800">
                    {reviewCount} felt trenger kontroll.
                  </p>
                </div>
              )}

              {/* View mode */}
              {!editing && (
                <div>
                  <h3 className="text-sm font-semibold text-stone-800 mb-2">Leverandør og faktura</h3>
                  <DetailRow label="Dokumenttype">{DOCUMENT_TYPE_LABELS[voucher.document_type] || voucher.document_type}</DetailRow>
                  <DetailRow label="Leverandør">{voucher.supplier_name || '–'}</DetailRow>
                  <DetailRow label="Organisasjonsnummer">{voucher.supplier_org_number || '–'}</DetailRow>
                  <DetailRow label="Fakturanummer">{voucher.invoice_number || '–'}</DetailRow>
                  <DetailRow label="Fakturadato">{formatDate(voucher.voucher_date)}</DetailRow>
                  <DetailRow label="Forfallsdato">{formatDate(voucher.due_date)}</DetailRow>
                  <DetailRow label="Beskrivelse">{voucher.description || '–'}</DetailRow>

                  <h3 className="text-sm font-semibold text-stone-800 mb-2 mt-6">Beløp</h3>
                  <DetailRow label="Totalbeløp">{formatCurrency(voucher.amount, voucher.currency)}</DetailRow>
                  <DetailRow label="Beløp eks. MVA">
                    {voucher.amount_excluding_vat !== null ? formatCurrency(voucher.amount_excluding_vat, voucher.currency) : '–'}
                  </DetailRow>
                  <DetailRow label="MVA-beløp">
                    {voucher.vat_amount !== null ? formatCurrency(voucher.vat_amount, voucher.currency) : '–'}
                  </DetailRow>
                  <DetailRow label="Valuta">{voucher.currency || 'NOK'}</DetailRow>

                  <h3 className="text-sm font-semibold text-stone-800 mb-2 mt-6">Betaling</h3>
                  <DetailRow label="KID">{voucher.kid || '–'}</DetailRow>
                  <DetailRow label="Bankkonto">{voucher.bank_account || '–'}</DetailRow>

                  <h3 className="text-sm font-semibold text-stone-800 mb-2 mt-6">Bokføring</h3>
                  <DetailRow label="Regnskapskonto">{voucher.account_code || 'Ikke ført'}</DetailRow>
                  <DetailRow label="MVA-kode">{voucher.mva_code ? MVA_CODE_LABELS[voucher.mva_code] || voucher.mva_code : '–'}</DetailRow>
                  <DetailRow label="OCR-kontrollstatus">
                    {voucher.extraction_status === 'completed' ? 'Fullført' : voucher.extraction_status === 'failed' ? 'Feilet' : '–'}
                  </DetailRow>
                </div>
              )}

              {/* Edit mode */}
              {editing && (
                <fieldset disabled={saving} className="space-y-5">
                  {/* Supplier and invoice */}
                  <div>
                    <h3 className="text-sm font-semibold text-stone-800 mb-3">Leverandør og faktura</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <FieldLabel label="Dokumenttype" needsReview={fieldNeedsReview('document_type', form, voucher, touched, isBooked)} />
                        <select
                          value={form.document_type}
                          onChange={(event) => setField('document_type', event.target.value)}
                          className={inputClass(fieldNeedsReview('document_type', form, voucher, touched, isBooked))}
                        >
                          <option value="invoice">Faktura</option>
                          <option value="receipt">Kvittering</option>
                        </select>
                      </div>
                      <div>
                        <FieldLabel label="Leverandør" needsReview={fieldNeedsReview('supplier_name', form, voucher, touched, isBooked)} />
                        <input
                          value={form.supplier_name}
                          onChange={(event) => setField('supplier_name', event.target.value)}
                          className={inputClass(fieldNeedsReview('supplier_name', form, voucher, touched, isBooked))}
                          placeholder="F.eks. Felleskjøpet"
                        />
                      </div>
                      <div>
                        <FieldLabel label="Organisasjonsnummer" needsReview={fieldNeedsReview('supplier_org_number', form, voucher, touched, isBooked)} />
                        <input
                          value={form.supplier_org_number}
                          onChange={(event) => setField('supplier_org_number', event.target.value)}
                          className={inputClass(fieldNeedsReview('supplier_org_number', form, voucher, touched, isBooked))}
                          placeholder="9 siffer"
                          inputMode="numeric"
                        />
                      </div>
                      <div>
                        <FieldLabel label="Fakturanummer" needsReview={fieldNeedsReview('invoice_number', form, voucher, touched, isBooked)} />
                        <input
                          value={form.invoice_number}
                          onChange={(event) => setField('invoice_number', event.target.value)}
                          className={inputClass(fieldNeedsReview('invoice_number', form, voucher, touched, isBooked))}
                        />
                      </div>
                      <div>
                        <FieldLabel label="Fakturadato" needsReview={fieldNeedsReview('voucher_date', form, voucher, touched, isBooked)} />
                        <input
                          type="date"
                          value={form.voucher_date}
                          onChange={(event) => setField('voucher_date', event.target.value)}
                          disabled={isBooked}
                          className={inputClass(fieldNeedsReview('voucher_date', form, voucher, touched, isBooked), isBooked)}
                        />
                        {isBooked && <p className="text-[11px] text-stone-500 mt-1">Låst (bokført)</p>}
                      </div>
                      <div>
                        <FieldLabel label="Forfallsdato" needsReview={fieldNeedsReview('due_date', form, voucher, touched, isBooked)} />
                        <input
                          type="date"
                          value={form.due_date}
                          onChange={(event) => setField('due_date', event.target.value)}
                          className={inputClass(fieldNeedsReview('due_date', form, voucher, touched, isBooked))}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Amounts */}
                  <div>
                    <h3 className="text-sm font-semibold text-stone-800 mb-3">Beløp</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <FieldLabel label="Totalbeløp" needsReview={fieldNeedsReview('amount', form, voucher, touched, isBooked)} />
                        <input
                          value={form.amount}
                          onChange={(event) => setField('amount', event.target.value)}
                          disabled={isBooked}
                          className={inputClass(fieldNeedsReview('amount', form, voucher, touched, isBooked), isBooked)}
                          placeholder="0,00"
                          inputMode="decimal"
                        />
                        {isBooked && <p className="text-[11px] text-stone-500 mt-1">Låst (bokført)</p>}
                      </div>
                      <div>
                        <FieldLabel label="Valuta" needsReview={fieldNeedsReview('currency', form, voucher, touched, isBooked)} />
                        <input
                          value={form.currency}
                          onChange={(event) => setField('currency', event.target.value)}
                          className={inputClass(fieldNeedsReview('currency', form, voucher, touched, isBooked))}
                          placeholder="NOK"
                        />
                      </div>
                      <div>
                        <FieldLabel label="Beløp eks. MVA" needsReview={fieldNeedsReview('amount_excluding_vat', form, voucher, touched, isBooked)} />
                        <input
                          value={form.amount_excluding_vat}
                          onChange={(event) => setField('amount_excluding_vat', event.target.value)}
                          className={inputClass(fieldNeedsReview('amount_excluding_vat', form, voucher, touched, isBooked))}
                          placeholder="0,00"
                          inputMode="decimal"
                        />
                      </div>
                      <div>
                        <FieldLabel label="MVA-beløp" needsReview={fieldNeedsReview('vat_amount', form, voucher, touched, isBooked)} />
                        <input
                          value={form.vat_amount}
                          onChange={(event) => setField('vat_amount', event.target.value)}
                          className={inputClass(fieldNeedsReview('vat_amount', form, voucher, touched, isBooked))}
                          placeholder="0,00"
                          inputMode="decimal"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Payment */}
                  <div>
                    <h3 className="text-sm font-semibold text-stone-800 mb-3">Betaling</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <FieldLabel label="KID" needsReview={fieldNeedsReview('kid', form, voucher, touched, isBooked)} />
                        <input
                          value={form.kid}
                          onChange={(event) => setField('kid', event.target.value)}
                          className={inputClass(fieldNeedsReview('kid', form, voucher, touched, isBooked))}
                          inputMode="numeric"
                        />
                      </div>
                      <div>
                        <FieldLabel label="Kontonummer" needsReview={fieldNeedsReview('bank_account', form, voucher, touched, isBooked)} />
                        <input
                          value={form.bank_account}
                          onChange={(event) => setField('bank_account', event.target.value)}
                          className={inputClass(fieldNeedsReview('bank_account', form, voucher, touched, isBooked))}
                          placeholder="XXXX.XX.XXXXX"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Booking */}
                  <div>
                    <h3 className="text-sm font-semibold text-stone-800 mb-3">Bokføring</h3>
                    <div className="space-y-4">
                      <div>
                        <FieldLabel label="Beskrivelse" needsReview={fieldNeedsReview('description', form, voucher, touched, isBooked)} />
                        <input
                          value={form.description}
                          onChange={(event) => setField('description', event.target.value)}
                          className={inputClass(fieldNeedsReview('description', form, voucher, touched, isBooked))}
                          placeholder="F.eks. Gjødsel kjøpt hos Felleskjøpet"
                        />
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <FieldLabel label="Regnskapskonto" needsReview={fieldNeedsReview('account_code', form, voucher, touched, isBooked)} />
                          <select
                            value={form.account_code}
                            onChange={(event) => setField('account_code', event.target.value)}
                            disabled={isBooked}
                            className={inputClass(fieldNeedsReview('account_code', form, voucher, touched, isBooked), isBooked)}
                          >
                            <option value="">Velg konto</option>
                            {accounts.map((account) => (
                              <option key={account.code} value={account.code}>
                                {account.code} – {account.name}
                              </option>
                            ))}
                          </select>
                          {isBooked && <p className="text-[11px] text-stone-500 mt-1">Låst (bokført)</p>}
                        </div>
                        <div>
                          <FieldLabel label="MVA-kode" needsReview={fieldNeedsReview('mva_code', form, voucher, touched, isBooked)} />
                          <select
                            value={form.mva_code}
                            onChange={(event) => setField('mva_code', event.target.value)}
                            disabled={isBooked}
                            className={inputClass(fieldNeedsReview('mva_code', form, voucher, touched, isBooked), isBooked)}
                          >
                            <option value="25">25 %</option>
                            <option value="15">15 %</option>
                            <option value="12">12 %</option>
                            <option value="0">0 %</option>
                            <option value="fradrag">Fradragsberettiget</option>
                          </select>
                          {isBooked && <p className="text-[11px] text-stone-500 mt-1">Låst (bokført)</p>}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-3 pt-2">
                    <button
                      type="button"
                      onClick={handleSave}
                      disabled={saving}
                      className="bg-bonde-green text-white px-5 py-2.5 rounded-lg text-sm font-semibold disabled:opacity-50"
                    >
                      {saving ? 'Lagrer...' : 'Lagre'}
                    </button>
                    <button
                      type="button"
                      onClick={cancelEditing}
                      disabled={saving}
                      className="bg-white border border-stone-300 hover:border-bonde-green text-stone-800 px-5 py-2.5 rounded-lg text-sm font-semibold disabled:opacity-50"
                    >
                      Avbryt
                    </button>
                  </div>
                </fieldset>
              )}

              {(message || error) && (
                <div className={`mt-4 rounded-lg border-l-4 p-3 ${error ? 'border-red-500 bg-red-50' : 'border-emerald-500 bg-emerald-50'}`}>
                  {message && <p className="text-emerald-700 text-sm">{message}</p>}
                  {error && <p className="text-red-700 text-sm">{error}</p>}
                </div>
              )}
            </Card>
          </div>
        )}
      </main>
    </div>
  )
}