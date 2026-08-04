'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
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

type GlossaryTerm = {
  term: string
  description: string
}

type UploadedVoucher = {
  id: string
  file_name: string
  status: string
  amount: number
  account_code: string | null
  voucher_date: string
  description?: string | null
  ocr_text_preview?: string | null
  ocr_provider?: string | null
  ocr_confidence?: number | null
  ocr_suggested_amount?: number | null
  ocr_suggested_date?: string | null
  ocr_suggested_supplier?: string | null
}

const FARM_ID_KEY = 'barebonde_active_farm_id'

export default function NewVoucherPage() {
  const [farmId, setFarmId] = useState('')
  const [simpleMode, setSimpleMode] = useState(true)
  const [search, setSearch] = useState('')
  const [accounts, setAccounts] = useState<Account[]>([])
  const [glossary, setGlossary] = useState<GlossaryTerm[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [description, setDescription] = useState('')
  const [voucherDate, setVoucherDate] = useState(new Date().toISOString().slice(0, 10))
  const [amount, setAmount] = useState('')
  const [transactionType, setTransactionType] = useState<'expense' | 'income'>('expense')
  const [accountCode, setAccountCode] = useState('')
  const [mvaCode, setMvaCode] = useState('25')
  const [uploading, setUploading] = useState(false)
  const [booking, setBooking] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [uploadedVoucher, setUploadedVoucher] = useState<UploadedVoucher | null>(null)

  const [cameraReady, setCameraReady] = useState(false)
  const [cameraOpen, setCameraOpen] = useState(false)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

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
  }, [])

  useEffect(() => {
    const run = async () => {
      try {
        const response = await apiFetch(`/api/accounting/accounts?query=${encodeURIComponent(search)}&simple_mode=${simpleMode}`)
        if (!response.ok) {
          throw new Error(await apiErrorMessage(response, 'Klarte ikke hente kontoforslag'))
        }
        const data = await response.json()
        setAccounts(data.accounts || [])
        setGlossary(data.glossary || [])
        if (!accountCode && data.accounts?.length) {
          setAccountCode(data.accounts[0].code)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ukjent feil')
      }
    }
    run()
  }, [search, simpleMode, accountCode])

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
      stopCamera()
    }
  }, [previewUrl])

  const imagePreview = useMemo(() => {
    if (!selectedFile) {
      return false
    }
    return selectedFile.type.startsWith('image/')
  }, [selectedFile])

  const handleFileChange = (file: File | null) => {
    setSelectedFile(file)
    setUploadedVoucher(null)
    setMessage('')
    setError('')

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
      setPreviewUrl('')
    }

    if (file && file.type.startsWith('image/')) {
      setPreviewUrl(URL.createObjectURL(file))
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
    } catch (err) {
      setError('Klarte ikke åpne kamera. Bruk filopplasting i stedet.')
    }
  }

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    setCameraOpen(false)
    setCameraReady(false)
  }

  const capturePhoto = async () => {
    if (!videoRef.current || !canvasRef.current) {
      return
    }

    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      return
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob((result) => resolve(result), 'image/jpeg', 0.9))
    if (!blob) {
      setError('Klarte ikke ta bilde')
      return
    }

    const file = new File([blob], `kamera-${Date.now()}.jpg`, { type: 'image/jpeg' })
    handleFileChange(file)
    stopCamera()
  }

  const uploadVoucher = async () => {
    if (!farmId) {
      setError('Du må sette opp gård før opplasting.')
      return
    }
    if (!selectedFile) {
      setError('Velg en fil eller ta et bilde først.')
      return
    }

    setUploading(true)
    setError('')
    setMessage('')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('description', description)
      formData.append('voucher_date', voucherDate)
      formData.append('simple_mode', String(simpleMode))

      const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/vouchers`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail || 'Opplasting feilet')
      }

      const data = (await response.json()) as UploadedVoucher
      setUploadedVoucher(data)
      if (!amount && data.ocr_suggested_amount) {
        setAmount(String(data.ocr_suggested_amount))
      }
      if (data.ocr_suggested_date) {
        setVoucherDate(data.ocr_suggested_date)
      }
      if (!description && data.ocr_suggested_supplier) {
        setDescription(data.ocr_suggested_supplier)
      }
      setMessage('Bilag lastet opp. Fyll inn konto og beløp for å føre.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ukjent feil')
    } finally {
      setUploading(false)
    }
  }

  const bookVoucher = async () => {
    if (!uploadedVoucher) {
      setError('Last opp bilag først.')
      return
    }

    const parsedAmount = Number(amount.replace(',', '.'))
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setError('Beløp må være større enn 0.')
      return
    }

    setBooking(true)
    setError('')
    setMessage('')

    try {
      const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/vouchers/${encodeURIComponent(uploadedVoucher.id)}/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: parsedAmount,
          account_code: accountCode,
          mva_code: mvaCode,
          transaction_type: transactionType,
          description,
          category: 'Drift',
        }),
      })

      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail || 'Føring feilet')
      }

      setMessage('Bilaget er ført. Du finner det i bilagslisten.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ukjent feil')
    } finally {
      setBooking(false)
    }
  }

  return (
    <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-serif text-stone-900">Nytt bilag</h1>
            <p className="text-stone-600 text-sm mt-1">Ta bilde, last opp fil og før bilaget i samme flyt.</p>
          </div>
          <Button href="/bilag" variant="outline" showArrow>
            TIL BILAGSLISTE
          </Button>
        </div>

        {!farmId && (
          <Card hoverEffect={false} className="p-6 bg-white mb-8">
            <p className="text-sm text-stone-700">Du må sette opp gård før du kan føre bilag.</p>
            <div className="mt-4">
              <Button href="/farm/setup" variant="outline" showArrow>
                GÅ TIL OPPSETT
              </Button>
            </div>
          </Card>
        )}

        {farmId && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <div className="xl:col-span-2 space-y-6">
              <Card hoverEffect={false} className="p-6 bg-white">
                <h2 className="text-lg font-semibold text-stone-900 mb-4">1. Legg ved bilag</h2>

                <div className="flex flex-wrap gap-3 mb-4">
                  <label className="inline-flex">
                    <input
                      type="file"
                      accept="image/*,application/pdf,text/plain,text/csv,application/json,application/xml,.txt,.csv,.json,.xml"
                      className="hidden"
                      onChange={(event) => handleFileChange(event.target.files?.[0] || null)}
                    />
                    <span className="cursor-pointer bg-white border border-stone-300 hover:border-bonde-green px-4 py-2 rounded-lg text-sm font-semibold text-stone-800">
                      Velg bilde/PDF/tekstfil
                    </span>
                  </label>

                  <button
                    type="button"
                    onClick={cameraOpen ? stopCamera : startCamera}
                    className="bg-bonde-light text-bonde-earth hover:bg-emerald-100 px-4 py-2 rounded-lg text-sm font-semibold"
                  >
                    {cameraOpen ? 'Stopp kamera' : 'Ta bilde med kamera'}
                  </button>
                </div>

                {cameraOpen && (
                  <div className="border border-stone-200 rounded-xl p-4 bg-stone-50">
                    <video ref={videoRef} autoPlay playsInline className="w-full rounded-lg bg-black max-h-[420px]" />
                    <div className="mt-3">
                      <button
                        type="button"
                        onClick={capturePhoto}
                        disabled={!cameraReady}
                        className="bg-bonde-green text-white px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-50"
                      >
                        Ta bilde nå
                      </button>
                    </div>
                  </div>
                )}

                <canvas ref={canvasRef} className="hidden" />

                {selectedFile && (
                  <div className="mt-4 border border-stone-200 rounded-xl p-4">
                    <p className="text-sm text-stone-700">
                      Valgt fil: <span className="font-semibold">{selectedFile.name}</span>
                    </p>
                    {imagePreview && previewUrl && (
                      <img src={previewUrl} alt="Forhåndsvisning bilag" className="mt-3 rounded-lg max-h-72 object-contain" />
                    )}
                  </div>
                )}

                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-stone-600 font-semibold mb-1">Beskrivelse</label>
                    <input
                      value={description}
                      onChange={(event) => setDescription(event.target.value)}
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                      placeholder="F.eks. Gjødsel kjøpt Felleskjøpet"
                    />
                  </div>
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-stone-600 font-semibold mb-1">Bilagsdato</label>
                    <input
                      type="date"
                      value={voucherDate}
                      onChange={(event) => setVoucherDate(event.target.value)}
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                    />
                  </div>
                </div>

                <div className="mt-4">
                  <button
                    type="button"
                    onClick={uploadVoucher}
                    disabled={uploading}
                    className="bg-bonde-green text-white px-5 py-2.5 rounded-lg text-sm font-semibold disabled:opacity-50"
                  >
                    {uploading ? 'Laster opp...' : 'Last opp bilag'}
                  </button>
                </div>
              </Card>

              <Card hoverEffect={false} className="p-6 bg-white">
                <h2 className="text-lg font-semibold text-stone-900 mb-4">2. Før bilaget</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-stone-600 font-semibold mb-1">Beløp (NOK)</label>
                    <input
                      value={amount}
                      onChange={(event) => setAmount(event.target.value)}
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                      placeholder="0"
                    />
                  </div>

                  <div>
                    <label className="block text-xs uppercase tracking-wider text-stone-600 font-semibold mb-1">Type</label>
                    <select
                      value={transactionType}
                      onChange={(event) => setTransactionType(event.target.value as 'expense' | 'income')}
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                    >
                      <option value="expense">Utgift</option>
                      <option value="income">Inntekt</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs uppercase tracking-wider text-stone-600 font-semibold mb-1">MVA-kode</label>
                    <select
                      value={mvaCode}
                      onChange={(event) => setMvaCode(event.target.value)}
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                    >
                      <option value="25">25%</option>
                      <option value="15">15%</option>
                      <option value="12">12%</option>
                      <option value="0">0%</option>
                      <option value="fradrag">Fradragsberettiget</option>
                    </select>
                  </div>

                  <div className="flex items-end">
                    <label className="inline-flex items-center gap-2 text-sm text-stone-700">
                      <input
                        type="checkbox"
                        checked={simpleMode}
                        onChange={(event) => setSimpleMode(event.target.checked)}
                      />
                      Enkel modus
                    </label>
                  </div>
                </div>

                <div className="mt-4">
                  <label className="block text-xs uppercase tracking-wider text-stone-600 font-semibold mb-1">Søk konto</label>
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                    placeholder="Søk på kontonummer eller navn"
                  />
                </div>

                <div className="mt-4">
                  <label className="block text-xs uppercase tracking-wider text-stone-600 font-semibold mb-1">Konto</label>
                  <select
                    value={accountCode}
                    onChange={(event) => setAccountCode(event.target.value)}
                    className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                  >
                    {accounts.map((account) => (
                      <option key={account.code} value={account.code}>
                        {account.code} - {account.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="mt-5">
                  <button
                    type="button"
                    onClick={bookVoucher}
                    disabled={booking || !uploadedVoucher}
                    className="bg-bonde-earth text-white px-5 py-2.5 rounded-lg text-sm font-semibold disabled:opacity-50"
                  >
                    {booking ? 'Fører...' : 'Før bilag'}
                  </button>
                </div>
              </Card>

              {(message || error) && (
                <Card hoverEffect={false} className="p-4 bg-white">
                  {message && <p className="text-emerald-700 text-sm">{message}</p>}
                  {error && <p className="text-red-700 text-sm">{error}</p>}
                </Card>
              )}

              {uploadedVoucher && uploadedVoucher.ocr_text_preview && (
                <Card hoverEffect={false} className="p-6 bg-white">
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <h3 className="text-base font-semibold text-stone-900">OCR-forslag</h3>
                    <span className="text-xs text-stone-500">
                      {uploadedVoucher.ocr_provider || 'ukjent motor'}
                      {typeof uploadedVoucher.ocr_confidence === 'number' ? ` • ${(uploadedVoucher.ocr_confidence * 100).toFixed(0)}%` : ''}
                    </span>
                  </div>
                  <p className="text-xs text-stone-600 mb-2">
                    Forslagene er brukt til å forhåndsfylle feltene over. Kontroller før føring.
                  </p>
                  <pre className="text-xs leading-relaxed whitespace-pre-wrap bg-stone-50 border border-stone-200 rounded-lg p-3 max-h-56 overflow-y-auto">
                    {uploadedVoucher.ocr_text_preview}
                  </pre>
                </Card>
              )}
            </div>

            <div className="space-y-6">
              <Card hoverEffect={false} className="p-6 bg-white">
                <h3 className="text-base font-semibold text-stone-900 mb-3">Kontohjelp</h3>
                <p className="text-sm text-stone-600 mb-4">Rask forklaring av vanlige kontoer for gårdsdrift.</p>
                <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
                  {accounts.slice(0, 10).map((account) => (
                    <div key={account.code} className="rounded-lg border border-stone-200 p-2.5">
                      <p className="text-sm font-semibold text-stone-900">{account.code} - {account.name}</p>
                      <p className="text-xs text-stone-600">{account.category}</p>
                    </div>
                  ))}
                </div>
              </Card>

              <Card hoverEffect={false} className="p-6 bg-white">
                <h3 className="text-base font-semibold text-stone-900 mb-3">Nøkkelbegreper</h3>
                <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
                  {glossary.map((term) => (
                    <div key={term.term}>
                      <p className="text-sm font-semibold text-stone-900">{term.term}</p>
                      <p className="text-xs text-stone-600">{term.description}</p>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
