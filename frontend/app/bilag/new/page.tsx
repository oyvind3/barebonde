'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Image from 'next/image'
import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { apiErrorMessage, apiFetch, bootstrapIdentity } from '@/lib/api'

type Account = {
  code: string
  name: string
  category: string
  simple: boolean
}

type FieldSuggestion = {
  value: unknown
  confidence: number | null
  source: string | null
  warnings: string[]
}

type Voucher = {
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

type FormState = {
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

const FARM_ID_KEY = 'barebonde_active_farm_id'
const CONFIDENCE_THRESHOLD = 0.85

// Maps form fields to the corresponding OCR field_suggestions key.
const SUGGESTION_MAP: Partial<Record<keyof FormState, string>> = {
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

const REQUIRED_FIELDS: Array<keyof FormState> = ['amount', 'voucher_date', 'description', 'account_code']

const STATUS_LABELS: Record<string, string> = {
  mottatt: 'Mottatt',
  needs_review: 'Trenger kontroll',
  ready: 'Klar for bokføring',
  ført: 'Ført',
}

function emptyForm(): FormState {
  return {
    document_type: 'invoice',
    supplier_name: '',
    supplier_org_number: '',
    invoice_number: '',
    voucher_date: new Date().toISOString().slice(0, 10),
    due_date: '',
    description: '',
    amount: '',
    amount_excluding_vat: '',
    vat_amount: '',
    currency: 'NOK',
    kid: '',
    bank_account: '',
    account_code: '',
    mva_code: '25',
    transaction_type: 'expense',
  }
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return ''
  return String(value)
}

function parseAmount(value: string): number {
  const normalized = value.replace(/\s/g, '').replace(',', '.')
  if (!normalized) return NaN
  return Number(normalized)
}

function parseOptionalNumber(value: string): number | undefined {
  const trimmed = value.trim()
  if (!trimmed) return undefined
  const parsed = parseAmount(trimmed)
  return Number.isFinite(parsed) ? parsed : undefined
}

function formFromVoucher(voucher: Voucher): FormState {
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

const inputBase = 'w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-bonde-green/40'

function inputClass(needsReview: boolean): string {
  return `${inputBase} ${needsReview ? 'border-amber-400 bg-amber-50' : 'border-stone-300 bg-white'}`
}

function FieldLabel({ label, needsReview }: { label: string; needsReview: boolean }) {
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

export default function NewVoucherPage() {
  const [authReady, setAuthReady] = useState(false)
  const [farmId, setFarmId] = useState('')
  const [simpleMode, setSimpleMode] = useState(true)
  const [accountSearch, setAccountSearch] = useState('')
  const [accounts, setAccounts] = useState<Account[]>([])

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [localPreviewUrl, setLocalPreviewUrl] = useState('')
  const [documentUrl, setDocumentUrl] = useState('')
  const [documentContentType, setDocumentContentType] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)

  const [voucher, setVoucher] = useState<Voucher | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm())
  const [touched, setTouched] = useState<Set<string>>(new Set())
  const [counterAccount, setCounterAccount] = useState('2400')

  const [uploading, setUploading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [booking, setBooking] = useState(false)
  const [booked, setBooked] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const [cameraOpen, setCameraOpen] = useState(false)
  const [cameraReady, setCameraReady] = useState(false)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const busy = uploading || saving || booking

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

  // --- Account catalog ---
  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        const response = await apiFetch(
          `/api/accounting/accounts?query=${encodeURIComponent(accountSearch)}&simple_mode=${simpleMode}`
        )
        if (!response.ok) return
        const data = await response.json()
        if (cancelled) return
        const list: Account[] = data.accounts || []
        setAccounts(list)
        setForm((prev) => (prev.account_code || !list.length ? prev : { ...prev, account_code: list[0].code }))
      } catch {
        // Account catalog is supplementary; ignore fetch errors here.
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [accountSearch, simpleMode])

  // --- Cleanup ---
  useEffect(() => {
    return () => {
      stopCamera()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    return () => {
      if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl)
    }
  }, [localPreviewUrl])

  useEffect(() => {
    return () => {
      if (documentUrl) URL.revokeObjectURL(documentUrl)
    }
  }, [documentUrl])

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    setCameraOpen(false)
    setCameraReady(false)
  }, [])

  const handleFileChange = (file: File | null) => {
    setSelectedFile(file)
    setVoucher(null)
    setBooked(false)
    setMessage('')
    setError('')
    setTouched(new Set())

    if (localPreviewUrl) {
      URL.revokeObjectURL(localPreviewUrl)
      setLocalPreviewUrl('')
    }
    if (documentUrl) {
      URL.revokeObjectURL(documentUrl)
      setDocumentUrl('')
      setDocumentContentType('')
    }

    if (file && file.type.startsWith('image/')) {
      setLocalPreviewUrl(URL.createObjectURL(file))
    }
  }

  const startCamera = async () => {
    setError('')
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Kamera støttes ikke i denne nettleseren.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      setCameraOpen(true)
      setCameraReady(true)
    } catch {
      setError('Klarte ikke åpne kamera. Bruk filopplasting i stedet.')
    }
  }

  const capturePhoto = async () => {
    if (!videoRef.current || !canvasRef.current) return
    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob((result) => resolve(result), 'image/jpeg', 0.9))
    if (!blob) {
      setError('Klarte ikke ta bilde.')
      return
    }
    const file = new File([blob], `kamera-${Date.now()}.jpg`, { type: 'image/jpeg' })
    handleFileChange(file)
    stopCamera()
  }

  const loadDocumentPreview = useCallback(
    async (farm: string, voucherId: string) => {
      setPreviewLoading(true)
      try {
        const response = await apiFetch(`/api/farms/${encodeURIComponent(farm)}/documents/${encodeURIComponent(voucherId)}/download`)
        if (!response.ok) return
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        setDocumentUrl((previous) => {
          if (previous) URL.revokeObjectURL(previous)
          return url
        })
        setDocumentContentType(blob.type || '')
      } catch {
        // Preview is best-effort; the form still works without it.
      } finally {
        setPreviewLoading(false)
      }
    },
    []
  )

  // --- Step 2: Upload ---
  const uploadVoucher = async () => {
    if (busy) return
    if (!farmId) {
      setError('Du må sette opp gård før opplasting.')
      return
    }
    if (!selectedFile) {
      setError('Velg en PDF eller et bilde først.')
      return
    }

    setUploading(true)
    setError('')
    setMessage('')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('simple_mode', String(simpleMode))

      const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/vouchers`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(await apiErrorMessage(response, 'Opplasting feilet.'))
      }

      const data = (await response.json()) as Voucher
      setVoucher(data)
      setForm(formFromVoucher(data))
      setCounterAccount(data.document_type === 'receipt' ? '1920' : '2400')
      setTouched(new Set())
      setBooked(false)
      setMessage('Dokumentet er lastet opp. Kontroller forslagene før bokføring.')
      void loadDocumentPreview(farmId, data.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ukjent feil ved opplasting.')
    } finally {
      setUploading(false)
    }
  }

  // --- "Kontroller" markers ---
  const fieldNeedsReview = useCallback(
    (key: keyof FormState): boolean => {
      if (!voucher || booked) return false
      if (touched.has(key)) return false
      const value = String(form[key] ?? '').trim()
      const suggestionKey = SUGGESTION_MAP[key]

      if (suggestionKey) {
        const suggestion = voucher.field_suggestions?.[suggestionKey]
        if (!value) return true // OCR found nothing here – user must fill it in
        if (suggestion) {
          if (suggestion.warnings && suggestion.warnings.length > 0) return true
          if (typeof suggestion.confidence === 'number' && suggestion.confidence < CONFIDENCE_THRESHOLD) return true
        }
        return false
      }

      // Fields without OCR suggestions: flag required empties only.
      if (REQUIRED_FIELDS.includes(key) && !value) return true
      return false
    },
    [voucher, booked, touched, form]
  )

  const reviewCount = useMemo(() => {
    if (!voucher || booked) return 0
    return (Object.keys(form) as Array<keyof FormState>).filter((key) => fieldNeedsReview(key)).length
  }, [voucher, booked, form, fieldNeedsReview])

  const setField = (key: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setTouched((prev) => {
      const next = new Set(prev)
      next.add(key)
      return next
    })
  }

  const buildPatchPayload = () => {
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

  // --- Step 8: Save user-confirmed values ---
  const handleSave = async () => {
    if (busy || !voucher || !farmId) return
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const parsedAmount = parseAmount(form.amount)
      const payload = buildPatchPayload()
      if (Number.isFinite(parsedAmount) && parsedAmount > 0) {
        payload.amount = parsedAmount
      }
      const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/vouchers/${encodeURIComponent(voucher.id)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) {
        throw new Error(await apiErrorMessage(response, 'Kunne ikke lagre verdiene.'))
      }
      const updated = (await response.json()) as Voucher
      setVoucher(updated)
      setMessage('Verdiene er lagret.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ukjent feil ved lagring.')
    } finally {
      setSaving(false)
    }
  }

  // --- Step 9: Book ---
  const handleBook = async () => {
    if (busy || !voucher || !farmId) return

    const validationErrors: string[] = []
    const parsedAmount = parseAmount(form.amount)
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      validationErrors.push('Totalbeløp må være et tall større enn 0.')
    }
    if (!form.voucher_date) validationErrors.push('Fakturadato er påkrevd.')
    if (!form.description.trim()) validationErrors.push('Beskrivelse er påkrevd.')
    if (!form.account_code) validationErrors.push('Regnskapskonto er påkrevd.')
    if (validationErrors.length) {
      setError(validationErrors.join(' '))
      return
    }

    setBooking(true)
    setError('')
    setMessage('')

    try {
      // 1) Persist all user-confirmed values (authoritative).
      const patchResponse = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/vouchers/${encodeURIComponent(voucher.id)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...buildPatchPayload(), amount: parsedAmount }),
      })
      if (!patchResponse.ok) {
        throw new Error(await apiErrorMessage(patchResponse, 'Kunne ikke lagre verdiene før bokføring.'))
      }

      // 2) Book the voucher.
      const bookResponse = await apiFetch(
        `/api/farms/${encodeURIComponent(farmId)}/vouchers/${encodeURIComponent(voucher.id)}/book`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            amount: parsedAmount,
            account_code: form.account_code,
            mva_code: form.mva_code,
            transaction_type: form.transaction_type,
            counter_account_code: counterAccount,
            category: 'Drift',
            description: form.description,
          }),
        }
      )
      if (!bookResponse.ok) {
        throw new Error(await apiErrorMessage(bookResponse, 'Bokføring feilet.'))
      }

      const updated = (await bookResponse.json()) as Voucher
      setVoucher(updated)
      setBooked(true)
      setMessage('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ukjent feil ved bokføring.')
    } finally {
      setBooking(false)
    }
  }

  const resetFlow = () => {
    handleFileChange(null)
    setForm(emptyForm())
    setTouched(new Set())
    setVoucher(null)
    setBooked(false)
    setMessage('')
    setError('')
    if (selectedFile) setSelectedFile(null)
  }

  const statusLabel = voucher ? STATUS_LABELS[voucher.status] || voucher.status : ''
  const isPdfPreview = documentContentType === 'application/pdf'
  const ocrFailed = voucher?.extraction_status === 'failed'

  return (
    <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-serif text-stone-900">Nytt bilag</h1>
            <p className="text-stone-600 text-sm mt-1">Last opp faktura eller kvittering, kontroller forslagene og bokfør bilaget.</p>
          </div>
          <Button href="/bilag" variant="outline" showArrow>
            TIL BILAGSLISTE
          </Button>
        </div>

        {!authReady && (
          <Card hoverEffect={false} className="p-6 bg-white">
            <p className="text-sm text-stone-600">Henter sesjon...</p>
          </Card>
        )}

        {authReady && !farmId && (
          <Card hoverEffect={false} className="p-6 bg-white">
            <p className="text-sm text-stone-700">Du må sette opp gård før du kan føre bilag.</p>
            <div className="mt-4">
              <Button href="/farm/setup" variant="outline" showArrow>
                GÅ TIL OPPSETT
              </Button>
            </div>
          </Card>
        )}

        {authReady && farmId && booked && voucher && (
          <Card hoverEffect={false} className="p-8 bg-white max-w-2xl mx-auto text-center">
            <div className="mx-auto w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center mb-4">
              <span className="text-emerald-700 text-2xl" aria-hidden>
                ✓
              </span>
            </div>
            <h2 className="text-2xl font-serif text-stone-900 mb-2">Bilaget er ført</h2>
            <p className="text-sm text-stone-600 mb-6">
              {voucher.file_name} ble bokført på konto {voucher.account_code} med beløp{' '}
              {new Intl.NumberFormat('nb-NO', { style: 'currency', currency: voucher.currency || 'NOK' }).format(voucher.amount)}.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button href="/bilag" variant="primary" showArrow>
                SE BILAGSLISTEN
              </Button>
              <Button variant="outline" onClick={resetFlow}>
                FØR NYTT BILAG
              </Button>
            </div>
          </Card>
        )}

        {authReady && farmId && !booked && (
          <div className="space-y-6">
            {/* Step 1: Upload */}
            <Card hoverEffect={false} className="p-6 bg-white">
              <div className="flex items-center justify-between gap-3 mb-4">
                <h2 className="text-lg font-semibold text-stone-900">1. Last opp bilag</h2>
                {voucher && (
                  <span className="text-xs font-semibold bg-bonde-light text-bonde-earth rounded-full px-3 py-1">
                    {statusLabel}
                  </span>
                )}
              </div>

              <div className="flex flex-wrap gap-3">
                <label className="inline-flex">
                  <input
                    type="file"
                    accept="image/*,application/pdf"
                    className="hidden"
                    disabled={busy}
                    onChange={(event) => handleFileChange(event.target.files?.[0] || null)}
                  />
                  <span
                    className={`cursor-pointer bg-white border border-stone-300 hover:border-bonde-green px-4 py-2 rounded-lg text-sm font-semibold text-stone-800 ${busy ? 'opacity-50 pointer-events-none' : ''}`}
                  >
                    Velg PDF eller bilde
                  </span>
                </label>

                <button
                  type="button"
                  onClick={cameraOpen ? stopCamera : startCamera}
                  disabled={busy}
                  className="bg-bonde-light text-bonde-earth hover:bg-emerald-100 px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-50"
                >
                  {cameraOpen ? 'Stopp kamera' : 'Ta bilde med kamera'}
                </button>
              </div>

              {cameraOpen && (
                <div className="mt-4 border border-stone-200 rounded-xl p-4 bg-stone-50">
                  <video ref={videoRef} autoPlay playsInline className="w-full rounded-lg bg-black max-h-[420px]" />
                  <div className="mt-3">
                    <button
                      type="button"
                      onClick={capturePhoto}
                      disabled={!cameraReady || busy}
                      className="bg-bonde-green text-white px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-50"
                    >
                      Ta bilde nå
                    </button>
                  </div>
                </div>
              )}

              <canvas ref={canvasRef} className="hidden" />

              {selectedFile && !voucher && (
                <div className="mt-4 border border-stone-200 rounded-xl p-4">
                  <p className="text-sm text-stone-700">
                    Valgt fil: <span className="font-semibold">{selectedFile.name}</span>
                  </p>
                  {localPreviewUrl && (
                    <Image
                      src={localPreviewUrl}
                      alt="Forhåndsvisning bilag"
                      width={720}
                      height={480}
                      unoptimized
                      className="mt-3 max-h-72 rounded-lg object-contain"
                    />
                  )}
                </div>
              )}

              {selectedFile && !voucher && (
                <div className="mt-4">
                  <button
                    type="button"
                    onClick={uploadVoucher}
                    disabled={busy}
                    className="bg-bonde-green text-white px-5 py-2.5 rounded-lg text-sm font-semibold disabled:opacity-50"
                  >
                    {uploading ? 'Laster opp og leser dokumentet...' : 'Last opp bilag'}
                  </button>
                  {uploading && (
                    <p className="text-xs text-stone-500 mt-2" role="status">
                      Behandler dokumentet. OCR leser leverandør, beløp og datoer – dette kan ta noen sekunder.
                    </p>
                  )}
                </div>
              )}
            </Card>

            {voucher && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                {/* Document preview */}
                <Card hoverEffect={false} className="p-6 bg-white lg:sticky lg:top-6">
                  <div className="flex items-center justify-between gap-3 mb-4">
                    <h2 className="text-lg font-semibold text-stone-900">2. Dokument</h2>
                    <a
                      href="#"
                      onClick={(event) => {
                        event.preventDefault()
                        void loadDocumentPreview(farmId, voucher.id)
                      }}
                      className="text-xs font-semibold text-bonde-green hover:underline"
                    >
                      Last inn dokument på nytt
                    </a>
                  </div>

                  <p className="text-sm text-stone-600 mb-3 truncate">{voucher.file_name}</p>

                  {previewLoading && (
                    <div className="border border-stone-200 rounded-xl p-8 text-center" role="status">
                      <p className="text-sm text-stone-500">Henter dokument...</p>
                    </div>
                  )}

                  {!previewLoading && documentUrl && isPdfPreview && (
                    <iframe src={documentUrl} title={voucher.file_name} className="w-full h-[560px] rounded-xl border border-stone-200" />
                  )}

                  {!previewLoading && documentUrl && !isPdfPreview && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={documentUrl} alt={voucher.file_name} className="w-full max-h-[560px] object-contain rounded-xl border border-stone-200 bg-stone-50" />
                  )}

                  {!previewLoading && !documentUrl && localPreviewUrl && (
                    <Image
                      src={localPreviewUrl}
                      alt="Forhåndsvisning bilag"
                      width={720}
                      height={480}
                      unoptimized
                      className="w-full max-h-[560px] rounded-xl object-contain border border-stone-200 bg-stone-50"
                    />
                  )}

                  {!previewLoading && !documentUrl && !localPreviewUrl && (
                    <div className="border border-dashed border-stone-300 rounded-xl p-8 text-center">
                      <p className="text-sm text-stone-500">Forhåndsvisning er ikke tilgjengelig for denne filtypen.</p>
                    </div>
                  )}

                  {ocrFailed && (
                    <div className="mt-4 rounded-lg bg-amber-50 border border-amber-300 p-3">
                      <p className="text-sm text-amber-800">
                        OCR kunne ikke lese dokumentet automatisk. Fyll inn feltene manuelt på grunnlag av dokumentet.
                      </p>
                    </div>
                  )}

                  {!ocrFailed && voucher.ocr_warnings.length > 0 && (
                    <div className="mt-4 rounded-lg bg-amber-50 border border-amber-300 p-3">
                      <p className="text-sm text-amber-800">OCR er usikker på enkelte felt. Kontroller feltene merket med «Kontroller».</p>
                    </div>
                  )}
                </Card>

                {/* Review form */}
                <Card hoverEffect={false} className="p-6 bg-white">
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <h2 className="text-lg font-semibold text-stone-900">3. Kontroller og korriger</h2>
                  </div>
                  <p className="text-xs text-stone-500 mb-4">
                    Feltene er forhåndsutfylt med forslag fra OCR. Forslagene er veiledende – verdiene du lagrer er de som gjelder.
                  </p>

                  {reviewCount > 0 && (
                    <div className="mb-4 rounded-lg bg-amber-50 border border-amber-300 p-3">
                      <p className="text-sm text-amber-800">
                        {reviewCount} felt {reviewCount === 1 ? 'trenger' : 'trenger'} kontroll før bokføring.
                      </p>
                    </div>
                  )}

                  <fieldset disabled={busy} className="space-y-5">
                    {/* Supplier and invoice */}
                    <div>
                      <h3 className="text-sm font-semibold text-stone-800 mb-3">Leverandør og faktura</h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <FieldLabel label="Dokumenttype" needsReview={fieldNeedsReview('document_type')} />
                          <select
                            value={form.document_type}
                            onChange={(event) => setField('document_type', event.target.value)}
                            className={inputClass(fieldNeedsReview('document_type'))}
                          >
                            <option value="invoice">Faktura</option>
                            <option value="receipt">Kvittering</option>
                          </select>
                        </div>
                        <div>
                          <FieldLabel label="Leverandør" needsReview={fieldNeedsReview('supplier_name')} />
                          <input
                            value={form.supplier_name}
                            onChange={(event) => setField('supplier_name', event.target.value)}
                            className={inputClass(fieldNeedsReview('supplier_name'))}
                            placeholder="F.eks. Felleskjøpet"
                          />
                        </div>
                        <div>
                          <FieldLabel label="Organisasjonsnummer" needsReview={fieldNeedsReview('supplier_org_number')} />
                          <input
                            value={form.supplier_org_number}
                            onChange={(event) => setField('supplier_org_number', event.target.value)}
                            className={inputClass(fieldNeedsReview('supplier_org_number'))}
                            placeholder="9 siffer"
                            inputMode="numeric"
                          />
                        </div>
                        <div>
                          <FieldLabel label="Fakturanummer" needsReview={fieldNeedsReview('invoice_number')} />
                          <input
                            value={form.invoice_number}
                            onChange={(event) => setField('invoice_number', event.target.value)}
                            className={inputClass(fieldNeedsReview('invoice_number'))}
                          />
                        </div>
                        <div>
                          <FieldLabel label="Fakturadato" needsReview={fieldNeedsReview('voucher_date')} />
                          <input
                            type="date"
                            value={form.voucher_date}
                            onChange={(event) => setField('voucher_date', event.target.value)}
                            className={inputClass(fieldNeedsReview('voucher_date'))}
                          />
                        </div>
                        <div>
                          <FieldLabel label="Forfallsdato" needsReview={fieldNeedsReview('due_date')} />
                          <input
                            type="date"
                            value={form.due_date}
                            onChange={(event) => setField('due_date', event.target.value)}
                            className={inputClass(fieldNeedsReview('due_date'))}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Amounts */}
                    <div>
                      <h3 className="text-sm font-semibold text-stone-800 mb-3">Beløp</h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <FieldLabel label="Totalbeløp" needsReview={fieldNeedsReview('amount')} />
                          <input
                            value={form.amount}
                            onChange={(event) => setField('amount', event.target.value)}
                            className={inputClass(fieldNeedsReview('amount'))}
                            placeholder="0,00"
                            inputMode="decimal"
                          />
                        </div>
                        <div>
                          <FieldLabel label="Valuta" needsReview={fieldNeedsReview('currency')} />
                          <input
                            value={form.currency}
                            onChange={(event) => setField('currency', event.target.value)}
                            className={inputClass(fieldNeedsReview('currency'))}
                            placeholder="NOK"
                          />
                        </div>
                        <div>
                          <FieldLabel label="Beløp eks. MVA" needsReview={fieldNeedsReview('amount_excluding_vat')} />
                          <input
                            value={form.amount_excluding_vat}
                            onChange={(event) => setField('amount_excluding_vat', event.target.value)}
                            className={inputClass(fieldNeedsReview('amount_excluding_vat'))}
                            placeholder="0,00"
                            inputMode="decimal"
                          />
                        </div>
                        <div>
                          <FieldLabel label="MVA-beløp" needsReview={fieldNeedsReview('vat_amount')} />
                          <input
                            value={form.vat_amount}
                            onChange={(event) => setField('vat_amount', event.target.value)}
                            className={inputClass(fieldNeedsReview('vat_amount'))}
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
                          <FieldLabel label="KID" needsReview={fieldNeedsReview('kid')} />
                          <input
                            value={form.kid}
                            onChange={(event) => setField('kid', event.target.value)}
                            className={inputClass(fieldNeedsReview('kid'))}
                            inputMode="numeric"
                          />
                        </div>
                        <div>
                          <FieldLabel label="Kontonummer" needsReview={fieldNeedsReview('bank_account')} />
                          <input
                            value={form.bank_account}
                            onChange={(event) => setField('bank_account', event.target.value)}
                            className={inputClass(fieldNeedsReview('bank_account'))}
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
                          <FieldLabel label="Beskrivelse" needsReview={fieldNeedsReview('description')} />
                          <input
                            value={form.description}
                            onChange={(event) => setField('description', event.target.value)}
                            className={inputClass(fieldNeedsReview('description'))}
                            placeholder="F.eks. Gjødsel kjøpt hos Felleskjøpet"
                          />
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <FieldLabel label="Regnskapskonto" needsReview={fieldNeedsReview('account_code')} />
                            <select
                              value={form.account_code}
                              onChange={(event) => setField('account_code', event.target.value)}
                              className={inputClass(fieldNeedsReview('account_code'))}
                            >
                              <option value="">Velg konto</option>
                              {accounts.map((account) => (
                                <option key={account.code} value={account.code}>
                                  {account.code} – {account.name}
                                </option>
                              ))}
                            </select>
                            <input
                              value={accountSearch}
                              onChange={(event) => setAccountSearch(event.target.value)}
                              className={`${inputBase} border-stone-300 bg-white mt-2`}
                              placeholder="Søk på kontonummer eller navn"
                            />
                          </div>
                          <div>
                            <FieldLabel label="MVA-kode" needsReview={fieldNeedsReview('mva_code')} />
                            <select
                              value={form.mva_code}
                              onChange={(event) => setField('mva_code', event.target.value)}
                              className={inputClass(fieldNeedsReview('mva_code'))}
                            >
                              <option value="25">25 %</option>
                              <option value="15">15 %</option>
                              <option value="12">12 %</option>
                              <option value="0">0 %</option>
                              <option value="fradrag">Fradragsberettiget</option>
                            </select>
                          </div>
                        </div>

                        <div>
                          <FieldLabel label="Transaksjonstype" needsReview={false} />
                          <select
                            value={form.transaction_type}
                            onChange={(event) => setField('transaction_type', event.target.value)}
                            className={inputClass(false)}
                          >
                            <option value="expense">Utgift</option>
                            <option value="income">Inntekt</option>
                          </select>
                        </div>

                        <div>
                          <FieldLabel label="Hvordan ble kjøpet håndtert?" needsReview={false} />
                          <select
                            value={counterAccount}
                            onChange={(event) => setCounterAccount(event.target.value)}
                            className={inputClass(false)}
                          >
                            <option value="2400">Leverandørfaktura → Leverandørgjeld (2400)</option>
                            <option value="1920">Betalt direkte → Bank (1920)</option>
                          </select>
                        </div>

                        <label className="inline-flex items-center gap-2 text-sm text-stone-700">
                          <input
                            type="checkbox"
                            checked={simpleMode}
                            onChange={(event) => setSimpleMode(event.target.checked)}
                          />
                          Enkel kontoliste
                        </label>
                      </div>
                    </div>
                  </fieldset>

                  <div className="mt-6 flex flex-col sm:flex-row gap-3">
                    <button
                      type="button"
                      onClick={handleSave}
                      disabled={busy}
                      className="bg-white border border-stone-300 hover:border-bonde-green text-stone-800 px-5 py-2.5 rounded-lg text-sm font-semibold disabled:opacity-50"
                    >
                      {saving ? 'Lagrer...' : 'Lagre verdier'}
                    </button>
                    <button
                      type="button"
                      onClick={handleBook}
                      disabled={busy}
                      className="bg-bonde-earth text-white px-5 py-2.5 rounded-lg text-sm font-semibold disabled:opacity-50"
                    >
                      {booking ? 'Bokfører...' : 'Bokfør bilag'}
                    </button>
                  </div>
                </Card>
              </div>
            )}

            {(message || error) && (
              <Card hoverEffect={false} className={`p-4 bg-white border-l-4 ${error ? 'border-red-500' : 'border-emerald-500'}`}>
                {message && <p className="text-emerald-700 text-sm">{message}</p>}
                {error && <p className="text-red-700 text-sm">{error}</p>}
              </Card>
            )}
          </div>
        )}
      </main>
    </div>
  )
}