'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { apiErrorMessage, apiFetch, bootstrapIdentity } from '@/lib/api'

type InvoiceSummary = {
  id: string
  status: string
  invoice_number: string | null
  customer_id: string
  customer_snapshot: { name?: string } | null
  invoice_date: string
  due_date: string
  total_ore: number
}

type CustomerSummary = { id: string; name: string }

const FARM_ID_KEY = 'barebonde_active_farm_id'

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

function formatDate(value: string): string {
  if (!value) return '–'
  const [year, month, day] = value.split('-')
  return `${day}.${month}.${year}`
}

function isOverdue(invoice: InvoiceSummary, today: string): boolean {
  return (invoice.status === 'issued' || invoice.status === 'sent') && invoice.due_date < today
}

function statusBadgeClass(status: string, overdue: boolean): string {
  if (overdue) return 'bg-red-100 text-red-800'
  if (status === 'draft') return 'bg-stone-100 text-stone-700'
  if (status === 'issued') return 'bg-amber-100 text-amber-800'
  if (status === 'sent') return 'bg-blue-100 text-blue-800'
  if (status === 'paid') return 'bg-green-100 text-green-800'
  return 'bg-stone-100 text-stone-500'
}

export default function FakturaPage() {
  const [farmId, setFarmId] = useState('')
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([])
  const [customers, setCustomers] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const today = new Date().toISOString().slice(0, 10)

  useEffect(() => {
    const storedFarmId = window.localStorage.getItem(FARM_ID_KEY) || ''
    bootstrapIdentity(storedFarmId)
      .then((identity) => {
        const activeFarmId = identity?.active_farm?.id || ''
        setFarmId(activeFarmId)
      })
      .catch(() => {
        setError('Kunne ikke hente den aktive gården.')
        setFarmId('')
      })
  }, [])

  useEffect(() => {
    if (!farmId) return
    const fetchInvoices = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/sales-invoices`)
        if (!response.ok) throw new Error(await apiErrorMessage(response, 'Kunne ikke hente fakturaer.'))
        const data = await response.json()
        setInvoices(data.invoices || [])
        const customerResponse = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/customers`)
        if (customerResponse.ok) {
          const customerData = await customerResponse.json()
          const map: Record<string, string> = {}
          for (const customer of (customerData.customers || []) as CustomerSummary[]) {
            map[customer.id] = customer.name
          }
          setCustomers(map)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Kunne ikke hente fakturaer.')
      } finally {
        setLoading(false)
      }
    }
    fetchInvoices()
  }, [farmId])

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-stone-900">Salgsfakturaer</h1>
            <p className="text-sm text-stone-600">Opprett, send og følg opp fakturaer.</p>
          </div>
          <div className="flex gap-2">
            <Link href="/kunder">
              <Button variant="secondary">Kunder</Button>
            </Link>
            <Link href="/faktura/ny">
              <Button>Ny faktura</Button>
            </Link>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
        )}

        <Card>
          {loading ? (
            <p className="py-8 text-center text-sm text-stone-500">Henter fakturaer …</p>
          ) : invoices.length === 0 ? (
            <div className="py-10 text-center">
              <p className="text-sm text-stone-600">Ingen fakturaer ennå.</p>
              <Link href="/faktura/ny" className="mt-3 inline-block text-sm font-semibold text-bonde-green hover:underline">
                Opprett din første faktura
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-stone-200 text-xs uppercase tracking-wide text-stone-500">
                    <th className="py-2 pr-3">Nr.</th>
                    <th className="py-2 pr-3">Kunde</th>
                    <th className="py-2 pr-3">Fakturadato</th>
                    <th className="py-2 pr-3">Forfall</th>
                    <th className="py-2 pr-3 text-right">Total</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((invoice) => {
                    const overdue = isOverdue(invoice, today)
                    return (
                      <tr key={invoice.id} className="border-b border-stone-100 last:border-0 hover:bg-stone-50">
                        <td className="py-3 pr-3">
                          <Link href={`/faktura/detalj?id=${encodeURIComponent(invoice.id)}`} className="font-semibold text-bonde-green hover:underline">
                            {invoice.invoice_number || 'Utkast'}
                          </Link>
                        </td>
                        <td className="py-3 pr-3">{invoice.customer_snapshot?.name || customers[invoice.customer_id] || '–'}</td>
                        <td className="py-3 pr-3">{formatDate(invoice.invoice_date)}</td>
                        <td className="py-3 pr-3">{formatDate(invoice.due_date)}</td>
                        <td className="py-3 pr-3 text-right whitespace-nowrap">{formatNok(invoice.total_ore)}</td>
                        <td className="py-3">
                          <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusBadgeClass(invoice.status, overdue)}`}>
                            {overdue ? 'Forfalt' : STATUS_LABELS[invoice.status] || invoice.status}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </main>
    </>
  )
}