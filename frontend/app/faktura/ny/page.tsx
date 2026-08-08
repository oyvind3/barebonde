'use client'

import { Suspense, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { apiErrorMessage, apiFetch } from '@/lib/api'
import { useIdentity } from '@/lib/identity'

const UNIT_CHOICES = ['stk', 'time', 'kg', 'liter', 'daa', 'oppdrag']
const VAT_CHOICES = [0, 12, 15, 25]

type Customer = {
  id: string
  name: string
  org_number: string
  email: string
  phone: string
  address: string
  postal_code: string
  city: string
}

type BrregResult = {
  org_number: string
  name: string
  address: string
  postal_code: string
  city: string
}

type LineDraft = {
  description: string
  quantity: string
  unit: string
  priceKr: string
  vat_rate: number
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function addDaysIso(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

function parseKrToOre(value: string): number | null {
  const cleaned = value.trim().replace(/\s/g, '').replace(',', '.')
  if (!cleaned) return null
  const parsed = Number(cleaned)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return Math.round(parsed * 100)
}

function parseQuantity(value: string): number | null {
  const cleaned = value.trim().replace(',', '.')
  if (!cleaned) return null
  const parsed = Number(cleaned)
  if (!Number.isFinite(parsed) || parsed <= 0) return null
  return parsed
}

function formatNok(ore: number): string {
  return (ore / 100).toLocaleString('nb-NO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' kr'
}

function emptyLine(): LineDraft {
  return { description: '', quantity: '1', unit: 'stk', priceKr: '', vat_rate: 25 }
}

function NyFakturaPageInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const editId = searchParams.get('id') || ''
  const { status, activeFarm } = useIdentity()
  const farmId = activeFarm?.id || ''
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Customer selection
  const [customerMode, setCustomerMode] = useState<'existing' | 'new'>('existing')
  const [selectedCustomerId, setSelectedCustomerId] = useState('')
  const [newCustomer, setNewCustomer] = useState({ name: '', org_number: '', email: '', address: '', postal_code: '', city: '' })
  const [brregQuery, setBrregQuery] = useState('')
  const [brregResults, setBrregResults] = useState<BrregResult[]>([])
  const [brregSearching, setBrregSearching] = useState(false)
  const [brregError, setBrregError] = useState('')

  // Invoice fields
  const [invoiceDate, setInvoiceDate] = useState(todayIso())
  const [dueDate, setDueDate] = useState(addDaysIso(14))
  const [reference, setReference] = useState('')
  const [message, setMessage] = useState('')
  const [lines, setLines] = useState<LineDraft[]>([emptyLine()])

  const [invoiceId, setInvoiceId] = useState('')
  const [saving, setSaving] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [issuing, setIssuing] = useState(false)

  useEffect(() => {
    if (status === 'loading') return
    if (!farmId) {
      setError('Ingen aktiv gård er valgt.')
      setLoading(false)
      return
    }
    const fetchData = async () => {
      setLoading(true)
      try {
        const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/customers`)
        if (!response.ok) throw new Error(await apiErrorMessage(response, 'Kunne ikke hente kunder.'))
        const data = await response.json()
        setCustomers(data.customers || [])

        if (editId) {
          const invoiceResponse = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/sales-invoices/${encodeURIComponent(editId)}`)
          if (!invoiceResponse.ok) throw new Error(await apiErrorMessage(invoiceResponse, 'Kunne ikke hente fakturaen.'))
          const invoice = await invoiceResponse.json()
          if (invoice.status !== 'draft') {
            setError('Fakturaen er allerede utstedt og kan ikke redigeres.')
          } else {
            setInvoiceId(invoice.id)
            setSelectedCustomerId(invoice.customer_id || '')
            setCustomerMode('existing')
            setInvoiceDate(invoice.invoice_date || todayIso())
            setDueDate(invoice.due_date || addDaysIso(14))
            setReference(invoice.reference || '')
            setMessage(invoice.message || '')
            if ((invoice.lines || []).length > 0) {
              setLines(
                invoice.lines.map((line: { description: string; quantity: string; unit: string; unit_price_ex_vat_ore: number; vat_rate: number }) => ({
                  description: line.description,
                  quantity: line.quantity,
                  unit: line.unit,
                  priceKr: (line.unit_price_ex_vat_ore / 100).toFixed(2).replace('.', ','),
                  vat_rate: line.vat_rate,
                }))
              )
            }
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Kunne ikke hente kunder.')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [farmId, status, editId])

  const totals = useMemo(() => {
    let subtotal = 0
    let vatTotal = 0
    for (const line of lines) {
      const qty = parseQuantity(line.quantity)
      const priceOre = parseKrToOre(line.priceKr)
      if (qty === null || priceOre === null) continue
      const net = Math.round(qty * priceOre)
      const vat = Math.round((net * line.vat_rate) / 100)
      subtotal += net
      vatTotal += vat
    }
    return { subtotal, vatTotal, total: subtotal + vatTotal }
  }, [lines])

  const updateLine = (index: number, patch: Partial<LineDraft>) => {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, ...patch } : line)))
  }

  const removeLine = (index: number) => {
    setLines((prev) => prev.filter((_, i) => i !== index))
  }

  const searchBrreg = async () => {
    if (status === 'loading') return
    if (!farmId) {
      setError('Ingen aktiv gård er valgt.')
      return
    }
    if (brregQuery.trim().length < 2) return
    setBrregSearching(true)
    setBrregError('')
    setBrregResults([])
    try {
      const response = await apiFetch(
        `/api/farms/${encodeURIComponent(farmId)}/customers/brreg-search?query=${encodeURIComponent(brregQuery.trim())}`
      )
      if (!response.ok) throw new Error(await apiErrorMessage(response, 'Søket feilet.'))
      const data = await response.json()
      setBrregResults(data.results || [])
      if ((data.results || []).length === 0) setBrregError('Ingen treff i Enhetsregisteret.')
    } catch (err) {
      setBrregError(err instanceof Error ? err.message : 'Søket feilet.')
    } finally {
      setBrregSearching(false)
    }
  }

  const pickBrregResult = (result: BrregResult) => {
    setNewCustomer({
      name: result.name,
      org_number: result.org_number,
      email: '',
      address: result.address,
      postal_code: result.postal_code,
      city: result.city,
    })
    setBrregResults([])
    setBrregQuery(result.name)
  }

  const buildLinePayload = () =>
    lines.map((line) => ({
      description: line.description,
      quantity: line.quantity,
      unit: line.unit,
      unit_price_ex_vat_ore: parseKrToOre(line.priceKr) ?? 0,
      vat_rate: line.vat_rate,
    }))

  const normalizeOrgNumber = (value: string): string => {
    return value.replace(/[.\s]/g, '')
  }

  const ensureCustomer = async (): Promise<string> => {
    if (status === 'loading') throw new Error('Laster identitet ...')
    if (!farmId) throw new Error('Ingen aktiv gård er valgt.')
    if (customerMode === 'existing') {
      if (!selectedCustomerId) throw new Error('Velg en kunde.')
      return selectedCustomerId
    }
    if (!newCustomer.name.trim()) throw new Error('Kunden mangler navn.')
    
    // Check if an existing customer with the same org_number already exists
    const normalizedOrgNumber = normalizeOrgNumber(newCustomer.org_number || '')
    if (normalizedOrgNumber.length > 0) {
      const existingCustomer = customers.find(
        (c) => normalizeOrgNumber(c.org_number || '') === normalizedOrgNumber
      )
      if (existingCustomer) {
        setSelectedCustomerId(existingCustomer.id)
        setCustomerMode('existing')
        return existingCustomer.id
      }
    }
    
    try {
      const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/customers`, {
        method: 'POST',
        body: JSON.stringify({
          name: newCustomer.name.trim(),
          org_number: newCustomer.org_number || null,
          email: newCustomer.email || null,
          address: newCustomer.address || null,
          postal_code: newCustomer.postal_code || null,
          city: newCustomer.city || null,
          country_code: 'NO',
          brreg_verified: Boolean(newCustomer.org_number),
        }),
      })
      if (!response.ok) {
        if (response.status === 409 && normalizedOrgNumber.length > 0) {
          // Fetch updated customer list and find the existing customer
          const refreshResponse = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/customers`)
          if (refreshResponse.ok) {
            const data = await refreshResponse.json()
            const refreshedCustomers = data.customers || []
            const existingCustomer = refreshedCustomers.find(
              (c: Customer) => normalizeOrgNumber(c.org_number || '') === normalizedOrgNumber
            )
            if (existingCustomer) {
              setCustomers(refreshedCustomers)
              setSelectedCustomerId(existingCustomer.id)
              setCustomerMode('existing')
              return existingCustomer.id
            }
          }
        }
        throw new Error(await apiErrorMessage(response, 'Kunne ikke opprette kunden.'))
      }
      const created = await response.json()
      setCustomers((prev) => [...prev, created])
      return created.id
    } catch (err) {
      throw err
    }
  }

  const saveDraft = async (): Promise<string | null> => {
    if (status === 'loading') return null
    if (!farmId) {
      setError('Ingen aktiv gård er valgt.')
      return null
    }
    setError('')
    setSuccess('')
    if (dueDate < invoiceDate) {
      setError('Forfallsdato kan ikke være før fakturadato.')
      return null
    }
    setSaving(true)
    try {
      const customerId = await ensureCustomer()
      const payload = {
        customer_id: customerId,
        invoice_date: invoiceDate,
        due_date: dueDate,
        reference,
        message,
        lines: buildLinePayload(),
      }
      let response: Response
      if (invoiceId) {
        response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/sales-invoices/${encodeURIComponent(invoiceId)}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      } else {
        response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/sales-invoices`, {
          method: 'POST',
          body: JSON.stringify(payload),
        })
      }
      if (!response.ok) throw new Error(await apiErrorMessage(response, 'Kunne ikke lagre utkastet.'))
      const data = await response.json()
      setInvoiceId(data.id)
      setSelectedCustomerId(customerId)
      setCustomerMode('existing')
      setSuccess('Utkastet er lagret.')
      return data.id
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kunne ikke lagre utkastet.')
      return null
    } finally {
      setSaving(false)
    }
  }

  const previewPdf = async () => {
    if (status === 'loading') return
    const id = invoiceId || (await saveDraft())
    if (!id || !farmId) {
      setError('Ingen aktiv gård er valgt.')
      return
    }
    setPreviewing(true)
    setError('')
    try {
      const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/sales-invoices/${encodeURIComponent(id)}/preview`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error(await apiErrorMessage(response, 'Kunne ikke forhåndsvise PDF.'))
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kunne ikke forhåndsvise PDF.')
    } finally {
      setPreviewing(false)
    }
  }

  const issueInvoice = async () => {
    if (status === 'loading') return
    const id = invoiceId || (await saveDraft())
    if (!id || !farmId) {
      setError('Ingen aktiv gård er valgt.')
      return
    }
    setIssuing(true)
    setError('')
    try {
      const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/sales-invoices/${encodeURIComponent(id)}/issue`, {
        method: 'POST',
      })
      if (!response.ok) {
        // On 503, the invoice may already be issued with accounting_status=error.
        // Refetch to get the actual persisted state.
        if (response.status === 503) {
          try {
            const refetchResponse = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/sales-invoices/${encodeURIComponent(id)}`)
            if (refetchResponse.ok) {
              const invoice = await refetchResponse.json()
              if (invoice.status === 'issued' && invoice.accounting_status === 'error') {
                router.push(`/faktura/detalj?id=${encodeURIComponent(id)}&issued=1`)
                return
              }
            }
          } catch {
            // Ignore refetch error, show original error
          }
        }
        throw new Error(await apiErrorMessage(response, 'Kunne ikke utstede fakturaen.'))
      }
      router.push(`/faktura/detalj?id=${encodeURIComponent(id)}&issued=1`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kunne ikke utstede fakturaen.')
    } finally {
      setIssuing(false)
    }
  }

  if (loading) {
    return (
      <>
        <Navbar />
        <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
          <p className="text-sm text-stone-500">Henter data …</p>
        </main>
      </>
    )
  }

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-stone-900">Ny faktura</h1>
            <p className="text-sm text-stone-600">Opprett et fakturautkast, forhåndsvis og utsted.</p>
          </div>
          <Link href="/faktura" className="text-sm font-semibold text-bonde-green hover:underline">
            ← Tilbake til fakturaer
          </Link>
        </div>

        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>}
        {success && <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">{success}</div>}

        <div className="space-y-6">
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-stone-900">Kunde</h2>
            <div className="mb-4 flex gap-2">
              <button
                type="button"
                onClick={() => setCustomerMode('existing')}
                className={`rounded-lg px-4 py-2 text-sm font-semibold ${customerMode === 'existing' ? 'bg-bonde-green text-white' : 'bg-stone-100 text-stone-700'}`}
              >
                Velg eksisterende
              </button>
              <button
                type="button"
                onClick={() => setCustomerMode('new')}
                className={`rounded-lg px-4 py-2 text-sm font-semibold ${customerMode === 'new' ? 'bg-bonde-green text-white' : 'bg-stone-100 text-stone-700'}`}
              >
                Ny kunde
              </button>
            </div>

            {customerMode === 'existing' ? (
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">Kunde</label>
                <select
                  value={selectedCustomerId}
                  onChange={(event) => setSelectedCustomerId(event.target.value)}
                  className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                >
                  <option value="">Velg kunde …</option>
                  {customers.map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.name} {customer.org_number ? `(${customer.org_number})` : ''}
                    </option>
                  ))}
                </select>
                {customers.length === 0 && (
                  <p className="mt-2 text-xs text-stone-500">Ingen kunder registrert ennå. Bruk «Ny kunde».</p>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-stone-700">Søk i Enhetsregisteret (valgfritt)</label>
                  <div className="flex gap-2">
                    <input
                      value={brregQuery}
                      onChange={(event) => setBrregQuery(event.target.value)}
                      onKeyDown={(event) => event.key === 'Enter' && searchBrreg()}
                      placeholder="Søk på navn eller org.nr."
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                    />
                    <Button type="button" variant="secondary" onClick={searchBrreg} disabled={brregSearching || brregQuery.trim().length < 2}>
                      {brregSearching ? 'Søker …' : 'Søk'}
                    </Button>
                  </div>
                  {brregError && <p className="mt-1 text-xs text-red-700">{brregError}</p>}
                  {brregResults.length > 0 && (
                    <ul className="mt-2 divide-y divide-stone-100 rounded-lg border border-stone-200">
                      {brregResults.map((result) => (
                        <li key={result.org_number} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                          <div>
                            <p className="font-medium text-stone-900">{result.name}</p>
                            <p className="text-xs text-stone-500">
                              {result.org_number} · {result.address}{result.postal_code ? `, ${result.postal_code} ${result.city}` : ''}
                            </p>
                          </div>
                          <button type="button" onClick={() => pickBrregResult(result)} className="shrink-0 text-sm font-semibold text-bonde-green hover:underline">
                            Velg
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-stone-700">Navn *</label>
                    <input
                      value={newCustomer.name}
                      onChange={(event) => setNewCustomer((prev) => ({ ...prev, name: event.target.value }))}
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-stone-700">Org.nr.</label>
                    <input
                      value={newCustomer.org_number}
                      onChange={(event) => setNewCustomer((prev) => ({ ...prev, org_number: event.target.value }))}
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-stone-700">E-post (for faktura)</label>
                    <input
                      type="email"
                      value={newCustomer.email}
                      onChange={(event) => setNewCustomer((prev) => ({ ...prev, email: event.target.value }))}
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-stone-700">Adresse</label>
                    <input
                      value={newCustomer.address}
                      onChange={(event) => setNewCustomer((prev) => ({ ...prev, address: event.target.value }))}
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-stone-700">Postnummer</label>
                    <input
                      value={newCustomer.postal_code}
                      onChange={(event) => setNewCustomer((prev) => ({ ...prev, postal_code: event.target.value }))}
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-stone-700">Sted</label>
                    <input
                      value={newCustomer.city}
                      onChange={(event) => setNewCustomer((prev) => ({ ...prev, city: event.target.value }))}
                      className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm"
                    />
                  </div>
                </div>
              </div>
            )}
          </Card>

          <Card>
            <h2 className="mb-4 text-lg font-semibold text-stone-900">Fakturadetaljer</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">Fakturadato</label>
                <input type="date" value={invoiceDate} onChange={(event) => setInvoiceDate(event.target.value)} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">Forfallsdato</label>
                <input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">Referanse</label>
                <input value={reference} onChange={(event) => setReference(event.target.value)} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">Melding til kunde</label>
                <input value={message} onChange={(event) => setMessage(event.target.value)} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
              </div>
            </div>
          </Card>

          <Card>
            <h2 className="mb-4 text-lg font-semibold text-stone-900">Fakturalinjer</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-stone-200 text-xs uppercase tracking-wide text-stone-500">
                    <th className="py-2 pr-2">Beskrivelse</th>
                    <th className="w-20 py-2 pr-2">Antall</th>
                    <th className="w-28 py-2 pr-2">Enhet</th>
                    <th className="w-32 py-2 pr-2">Pris eks. MVA</th>
                    <th className="w-24 py-2 pr-2">MVA</th>
                    <th className="w-28 py-2 pr-2 text-right">Sum</th>
                    <th className="w-10 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {lines.map((line, index) => {
                    const qty = parseQuantity(line.quantity)
                    const priceOre = parseKrToOre(line.priceKr)
                    const lineTotal = qty !== null && priceOre !== null ? Math.round(qty * priceOre) + Math.round((Math.round(qty * priceOre) * line.vat_rate) / 100) : null
                    return (
                      <tr key={index} className="border-b border-stone-100 last:border-0">
                        <td className="py-2 pr-2">
                          <input value={line.description} onChange={(event) => updateLine(index, { description: event.target.value })} placeholder="Beskrivelse" className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
                        </td>
                        <td className="py-2 pr-2">
                          <input value={line.quantity} onChange={(event) => updateLine(index, { quantity: event.target.value })} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
                        </td>
                        <td className="py-2 pr-2">
                          <select value={line.unit} onChange={(event) => updateLine(index, { unit: event.target.value })} className="w-full rounded-lg border border-stone-300 px-2 py-2 text-sm">
                            {UNIT_CHOICES.map((unit) => (
                              <option key={unit} value={unit}>{unit}</option>
                            ))}
                          </select>
                        </td>
                        <td className="py-2 pr-2">
                          <input value={line.priceKr} onChange={(event) => updateLine(index, { priceKr: event.target.value })} placeholder="0,00" className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
                        </td>
                        <td className="py-2 pr-2">
                          <select value={line.vat_rate} onChange={(event) => updateLine(index, { vat_rate: Number(event.target.value) })} className="w-full rounded-lg border border-stone-300 px-2 py-2 text-sm">
                            {VAT_CHOICES.map((rate) => (
                              <option key={rate} value={rate}>{rate} %</option>
                            ))}
                          </select>
                        </td>
                        <td className="py-2 pr-2 text-right whitespace-nowrap">{lineTotal !== null ? formatNok(lineTotal) : '–'}</td>
                        <td className="py-2 text-right">
                          <button type="button" onClick={() => removeLine(index)} disabled={lines.length <= 1} className="rounded px-2 py-1 text-red-600 hover:bg-red-50 disabled:opacity-40" aria-label="Fjern linje">
                            ✕
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <button type="button" onClick={() => setLines((prev) => [...prev, emptyLine()])} className="mt-3 text-sm font-semibold text-bonde-green hover:underline">
              + Legg til linje
            </button>

            <div className="mt-6 flex justify-end">
              <div className="w-full max-w-xs space-y-1 text-sm">
                <div className="flex justify-between text-stone-600"><span>Sum eks. MVA</span><span>{formatNok(totals.subtotal)}</span></div>
                <div className="flex justify-between text-stone-600"><span>MVA</span><span>{formatNok(totals.vatTotal)}</span></div>
                <div className="flex justify-between border-t border-stone-200 pt-1 text-base font-bold text-stone-900"><span>Totalt</span><span>{formatNok(totals.total)}</span></div>
              </div>
            </div>
          </Card>

          <div className="flex flex-wrap justify-end gap-3">
            <Button type="button" variant="secondary" onClick={saveDraft} disabled={saving || previewing || issuing || status === 'loading' || !farmId}>
              {saving ? 'Lagrer …' : invoiceId ? 'Lagre utkast' : 'Lagre utkast'}
            </Button>
            <Button type="button" variant="secondary" onClick={previewPdf} disabled={saving || previewing || issuing || status === 'loading' || !farmId}>
              {previewing ? 'Genererer …' : 'Forhåndsvis PDF'}
            </Button>
            <Button type="button" onClick={issueInvoice} disabled={saving || previewing || issuing || status === 'loading' || !farmId}>
              {issuing ? 'Utsteder …' : 'Utsted faktura'}
            </Button>
          </div>
        </div>
      </main>
    </>
  )
}

export default function NyFakturaPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-bonde-oat flex flex-col font-sans items-center justify-center">
          <p className="text-sm text-stone-600">Laster fakturautkast …</p>
        </div>
      }
    >
      <NyFakturaPageInner />
    </Suspense>
  )
}
