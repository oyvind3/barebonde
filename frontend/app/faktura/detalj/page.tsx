'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { apiErrorMessage, apiFetch, bootstrapIdentity } from '@/lib/api'

const FARM_ID_KEY = 'barebonde_active_farm_id'

type InvoiceLine = {
  id: string
  description: string
  quantity: string
  unit: string
  unit_price_ex_vat_ore: number
  vat_rate: number
  line_net_ore: number
  line_vat_ore: number
  line_total_ore: number
}

type Delivery = {
  recipient_email: string | null
  send_count: number
  last_attempt_at: string | null
  last_success_at: string | null
  provider_message_id: string | null
  last_error: string | null
}

type Invoice = {
  id: string
  status: string
  invoice_number: string | null
  invoice_date: string
  due_date: string
  customer_id: string
  customer_snapshot: Record<string, string> | null
  seller_snapshot: Record<string, string> | null
  payment_account_snapshot: Record<string, string> | null
  lines: InvoiceLine[]
  subtotal_ore: number
  vat_total_ore: number
  total_ore: number
  reference: string
  message: string
  has_pdf: boolean
  issued_at: string | null
  sent_at: string | null
  paid_at: string | null
  delivery: Delivery
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Utkast',
  issued: 'Utstedt',
  sent: 'Sendt',
  paid: 'Betalt',
  cancelled: 'Kansellert',
}

function formatNok(ore: number): string {
  return (ore / 100).toLocaleString('nb-NO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' kr'
}

function formatDate(value: string | null): string {
  if (!value) return '–'
  const datePart = value.slice(0, 10)
  const [year, month, day] = datePart.split('-')
  if (!year || !month || !day) return value
  return `${day}.${month}.${year}`
}

function statusBadgeClass(status: string): string {
  if (status === 'draft') return 'bg-stone-100 text-stone-700'
  if (status === 'issued') return 'bg-amber-100 text-amber-800'
  if (status === 'sent') return 'bg-blue-100 text-blue-800'
  if (status === 'paid') return 'bg-green-100 text-green-800'
  return 'bg-stone-100 text-stone-500'
}

export default function FakturaDetaljPage() {
  const searchParams = useSearchParams()
  const invoiceId = searchParams.get('id') || ''
  const justIssued = searchParams.get('issued') === '1'

  const [farmId, setFarmId] = useState('')
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [customerName, setCustomerName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(justIssued ? 'Fakturaen er utstedt.' : '')
  const [busy, setBusy] = useState<'' | 'send' | 'resend' | 'paid' | 'cancel' | 'pdf'>('')

  const loadInvoice = useCallback(async (activeFarmId: string) => {
    if (!activeFarmId || !invoiceId) return
    setLoading(true)
    setError('')
    try {
      const response = await apiFetch(`/api/farms/${encodeURIComponent(activeFarmId)}/sales-invoices/${encodeURIComponent(invoiceId)}`)
      if (!response.ok) throw new Error(await apiErrorMessage(response, 'Kunne ikke hente fakturaen.'))
      const data = await response.json()
      setInvoice(data)
      if (data.customer_id) {
        const customerResponse = await apiFetch(`/api/farms/${encodeURIComponent(activeFarmId)}/customers/${encodeURIComponent(data.customer_id)}`)
        if (customerResponse.ok) {
          const customer = await customerResponse.json()
          setCustomerName(customer.name || '')
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kunne ikke hente fakturaen.')
    } finally {
      setLoading(false)
    }
  }, [invoiceId])

  useEffect(() => {
    const storedFarmId = window.localStorage.getItem(FARM_ID_KEY) || ''
    bootstrapIdentity(storedFarmId)
      .then((identity) => {
        const activeFarmId = identity?.active_farm?.id || ''
        setFarmId(activeFarmId)
        loadInvoice(activeFarmId)
      })
      .catch(() => {
        setError('Kunne ikke hente den aktive gården.')
        setLoading(false)
      })
  }, [loadInvoice])

  const runAction = async (path: string, action: 'send' | 'resend' | 'paid' | 'cancel', successMessage: string, errorMessage: string) => {
    if (!farmId || !invoiceId) return
    setBusy(action)
    setError('')
    setSuccess('')
    try {
      const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/sales-invoices/${encodeURIComponent(invoiceId)}${path}`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error(await apiErrorMessage(response, errorMessage))
      setSuccess(successMessage)
      await loadInvoice(farmId)
    } catch (err) {
      setError(err instanceof Error ? err.message : errorMessage)
    } finally {
      setBusy('')
    }
  }

  const openPdf = async (mode: 'preview' | 'download') => {
    if (!farmId || !invoiceId) return
    setBusy('pdf')
    setError('')
    try {
      let url: string
      if (invoice?.status === 'draft') {
        const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/sales-invoices/${encodeURIComponent(invoiceId)}/preview`, { method: 'POST' })
        if (!response.ok) throw new Error(await apiErrorMessage(response, 'Kunne ikke generere PDF.'))
        const blob = await response.blob()
        url = URL.createObjectURL(blob)
      } else {
        const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/sales-invoices/${encodeURIComponent(invoiceId)}/pdf`)
        if (!response.ok) throw new Error(await apiErrorMessage(response, 'Kunne ikke hente PDF.'))
        const blob = await response.blob()
        url = URL.createObjectURL(blob)
        if (mode === 'download') {
          const anchor = document.createElement('a')
          anchor.href = url
          anchor.download = `faktura-${invoice?.invoice_number || invoiceId.slice(-8)}.pdf`
          anchor.click()
          setTimeout(() => URL.revokeObjectURL(url), 60000)
          return
        }
      }
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kunne ikke hente PDF.')
    } finally {
      setBusy('')
    }
  }

  const displayName = invoice?.customer_snapshot?.name || customerName || '–'

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-stone-900">
              {invoice?.invoice_number ? `Faktura ${invoice.invoice_number}` : 'Fakturautkast'}
            </h1>
            <p className="text-sm text-stone-600">{displayName}</p>
          </div>
          <Link href="/faktura" className="text-sm font-semibold text-bonde-green hover:underline">
            ← Tilbake til fakturaer
          </Link>
        </div>

        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>}
        {success && <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">{success}</div>}

        {loading ? (
          <p className="text-sm text-stone-500">Henter faktura …</p>
        ) : invoice ? (
          <div className="space-y-6">
            <Card>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <span className={`inline-block rounded-full px-3 py-1 text-sm font-semibold ${statusBadgeClass(invoice.status)}`}>
                  {STATUS_LABELS[invoice.status] || invoice.status}
                </span>
                <div className="flex flex-wrap gap-2">
                  {invoice.status === 'draft' && (
                    <>
                      <Link href={`/faktura/ny?id=${encodeURIComponent(invoice.id)}`}>
                        <Button variant="secondary">Rediger</Button>
                      </Link>
                      <Button variant="secondary" onClick={() => openPdf('preview')} disabled={busy !== ''}>
                        {busy === 'pdf' ? 'Genererer …' : 'Forhåndsvis PDF'}
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() => runAction('/cancel', 'cancel', 'Utkastet er kansellert.', 'Kunne ikke kansellere utkastet.')}
                        disabled={busy !== ''}
                      >
                        {busy === 'cancel' ? 'Kansellerer …' : 'Kanseller utkast'}
                      </Button>
                    </>
                  )}
                  {invoice.status === 'issued' && (
                    <>
                      <Button variant="secondary" onClick={() => openPdf('download')} disabled={busy !== ''}>
                        {busy === 'pdf' ? 'Henter …' : 'Last ned PDF'}
                      </Button>
                      <Button onClick={() => runAction('/send', 'send', 'Fakturaen er sendt.', 'Fakturaen er utstedt, men e-posten kunne ikke sendes. Du kan prøve igjen.')} disabled={busy !== ''}>
                        {busy === 'send' ? 'Sender …' : 'Send faktura'}
                      </Button>
                      <Button variant="secondary" onClick={() => runAction('/mark-paid', 'paid', 'Fakturaen er markert som betalt.', 'Kunne ikke markere fakturaen som betalt.')} disabled={busy !== ''}>
                        {busy === 'paid' ? 'Oppdaterer …' : 'Marker betalt'}
                      </Button>
                    </>
                  )}
                  {invoice.status === 'sent' && (
                    <>
                      <Button variant="secondary" onClick={() => openPdf('download')} disabled={busy !== ''}>
                        {busy === 'pdf' ? 'Henter …' : 'Last ned PDF'}
                      </Button>
                      <Button variant="secondary" onClick={() => runAction('/resend', 'resend', 'Fakturaen er sendt på nytt.', 'Kunne ikke sende fakturaen på nytt.')} disabled={busy !== ''}>
                        {busy === 'resend' ? 'Sender …' : 'Send på nytt'}
                      </Button>
                      <Button onClick={() => runAction('/mark-paid', 'paid', 'Fakturaen er markert som betalt.', 'Kunne ikke markere fakturaen som betalt.')} disabled={busy !== ''}>
                        {busy === 'paid' ? 'Oppdaterer …' : 'Marker betalt'}
                      </Button>
                    </>
                  )}
                  {invoice.status === 'paid' && (
                    <Button variant="secondary" onClick={() => openPdf('download')} disabled={busy !== ''}>
                      {busy === 'pdf' ? 'Henter …' : 'Last ned PDF'}
                    </Button>
                  )}
                </div>
              </div>

              <div className="mt-6 grid gap-6 sm:grid-cols-2">
                <div>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">Kunde</h3>
                  <p className="text-sm font-semibold text-stone-900">{displayName}</p>
                  {invoice.customer_snapshot?.org_number && <p className="text-sm text-stone-600">Org.nr. {invoice.customer_snapshot.org_number}</p>}
                  {invoice.customer_snapshot?.address && <p className="text-sm text-stone-600">{invoice.customer_snapshot.address}</p>}
                  {(invoice.customer_snapshot?.postal_code || invoice.customer_snapshot?.city) && (
                    <p className="text-sm text-stone-600">{invoice.customer_snapshot.postal_code} {invoice.customer_snapshot.city}</p>
                  )}
                  {invoice.customer_snapshot?.email && <p className="text-sm text-stone-600">{invoice.customer_snapshot.email}</p>}
                </div>
                <div>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">Selger</h3>
                  {invoice.seller_snapshot ? (
                    <>
                      <p className="text-sm font-semibold text-stone-900">{invoice.seller_snapshot.name}</p>
                      {invoice.seller_snapshot.org_number && <p className="text-sm text-stone-600">Org.nr. {invoice.seller_snapshot.org_number}</p>}
                      {invoice.seller_snapshot.address && <p className="text-sm text-stone-600">{invoice.seller_snapshot.address}</p>}
                      {(invoice.seller_snapshot.postal_code || invoice.seller_snapshot.city) && (
                        <p className="text-sm text-stone-600">{invoice.seller_snapshot.postal_code} {invoice.seller_snapshot.city}</p>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-stone-500">Snapshottes ved utstedelse.</p>
                  )}
                </div>
                <div>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">Faktura</h3>
                  <dl className="space-y-1 text-sm text-stone-600">
                    <div className="flex justify-between"><dt>Fakturadato</dt><dd>{formatDate(invoice.invoice_date)}</dd></div>
                    <div className="flex justify-between"><dt>Forfall</dt><dd>{formatDate(invoice.due_date)}</dd></div>
                    {invoice.reference && <div className="flex justify-between"><dt>Referanse</dt><dd>{invoice.reference}</dd></div>}
                    {invoice.issued_at && <div className="flex justify-between"><dt>Utstedt</dt><dd>{formatDate(invoice.issued_at)}</dd></div>}
                    {invoice.sent_at && <div className="flex justify-between"><dt>Sendt</dt><dd>{formatDate(invoice.sent_at)}</dd></div>}
                    {invoice.paid_at && <div className="flex justify-between"><dt>Betalt</dt><dd>{formatDate(invoice.paid_at)}</dd></div>}
                  </dl>
                </div>
                <div>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">Betaling</h3>
                  {invoice.payment_account_snapshot?.account_number ? (
                    <p className="text-sm text-stone-600">Kontonummer: {invoice.payment_account_snapshot.account_number}</p>
                  ) : (
                    <p className="text-sm text-stone-500">Snapshottes ved utstedelse.</p>
                  )}
                  {invoice.delivery.send_count > 0 && (
                    <p className="mt-2 text-xs text-stone-500">
                      Sendt {invoice.delivery.send_count} gang{invoice.delivery.send_count === 1 ? '' : 'er'}
                      {invoice.delivery.recipient_email ? ` til ${invoice.delivery.recipient_email}` : ''}
                    </p>
                  )}
                  {invoice.delivery.last_error && (
                    <p className="mt-1 text-xs text-red-700">Siste utsending feilet: {invoice.delivery.last_error}</p>
                  )}
                </div>
              </div>
            </Card>

            <Card>
              <h2 className="mb-4 text-lg font-semibold text-stone-900">Linjer</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-stone-200 text-xs uppercase tracking-wide text-stone-500">
                      <th className="py-2 pr-3">Beskrivelse</th>
                      <th className="py-2 pr-3 text-right">Antall</th>
                      <th className="py-2 pr-3">Enhet</th>
                      <th className="py-2 pr-3 text-right">Pris eks. MVA</th>
                      <th className="py-2 pr-3 text-right">MVA</th>
                      <th className="py-2 text-right">Sum</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoice.lines.map((line) => (
                      <tr key={line.id} className="border-b border-stone-100 last:border-0">
                        <td className="py-2 pr-3">{line.description}</td>
                        <td className="py-2 pr-3 text-right">{line.quantity}</td>
                        <td className="py-2 pr-3">{line.unit}</td>
                        <td className="py-2 pr-3 text-right whitespace-nowrap">{formatNok(line.unit_price_ex_vat_ore)}</td>
                        <td className="py-2 pr-3 text-right">{line.vat_rate} %</td>
                        <td className="py-2 text-right whitespace-nowrap">{formatNok(line.line_total_ore)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-6 flex justify-end">
                <div className="w-full max-w-xs space-y-1 text-sm">
                  <div className="flex justify-between text-stone-600"><span>Sum eks. MVA</span><span>{formatNok(invoice.subtotal_ore)}</span></div>
                  <div className="flex justify-between text-stone-600"><span>MVA</span><span>{formatNok(invoice.vat_total_ore)}</span></div>
                  <div className="flex justify-between border-t border-stone-200 pt-1 text-base font-bold text-stone-900"><span>Totalt</span><span>{formatNok(invoice.total_ore)}</span></div>
                </div>
              </div>
              {invoice.message && (
                <div className="mt-4 rounded-lg bg-stone-50 px-4 py-3 text-sm text-stone-700">{invoice.message}</div>
              )}
            </Card>
          </div>
        ) : (
          !error && <p className="text-sm text-stone-500">Fant ikke fakturaen.</p>
        )}
      </main>
    </>
  )
}