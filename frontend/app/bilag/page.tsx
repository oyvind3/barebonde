'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

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
  blob_url: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const FARM_ID_KEY = 'barebonde_active_farm_id'

export default function BilagPage() {
  const [farmId, setFarmId] = useState('')
  const [items, setItems] = useState<Voucher[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  useEffect(() => {
    const storedFarmId = window.localStorage.getItem(FARM_ID_KEY) || ''
    setFarmId(storedFarmId)
  }, [])

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedQuery(searchQuery.trim()), 300)
    return () => window.clearTimeout(timeout)
  }, [searchQuery])

  useEffect(() => {
    if (!farmId) {
      setLoading(false)
      return
    }

    if (dateFrom && dateTo && dateFrom > dateTo) {
      setError('Fra-dato kan ikke være etter til-dato')
      setLoading(false)
      return
    }

    const fetchVouchers = async () => {
      setLoading(true)
      setError('')
      try {
        const params = new URLSearchParams({ farm_id: farmId })
        if (debouncedQuery) params.set('q', debouncedQuery)
        if (statusFilter) params.set('status', statusFilter)
        if (dateFrom) params.set('date_from', dateFrom)
        if (dateTo) params.set('date_to', dateTo)

        const response = await fetch(`${API_BASE}/api/accounting/vouchers?${params.toString()}`)
        if (!response.ok) {
          throw new Error('Klarte ikke hente bilag')
        }
        const data = (await response.json()) as Voucher[]
        setItems(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ukjent feil')
      } finally {
        setLoading(false)
      }
    }

    fetchVouchers()
  }, [farmId, debouncedQuery, statusFilter, dateFrom, dateTo])

  const hasFilters = Boolean(searchQuery || statusFilter || dateFrom || dateTo)

  const clearFilters = () => {
    setSearchQuery('')
    setDebouncedQuery('')
    setStatusFilter('')
    setDateFrom('')
    setDateTo('')
  }

  const summary = useMemo(() => {
    const total = items.reduce((sum, item) => sum + (item.amount || 0), 0)
    const booked = items.filter((item) => item.status === 'ført').length
    return {
      count: items.length,
      total,
      booked,
    }
  }, [items])

  return (
    <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-serif text-stone-900">Bilag</h1>
            <p className="text-stone-600 text-sm mt-1">Registrer, før og få oversikt over alle bilag.</p>
          </div>
          <Button href="/bilag/new" variant="primary" showArrow>
            NYTT BILAG
          </Button>
        </div>

        {!farmId && (
          <Card hoverEffect={false} className="p-6 bg-white mb-8">
            <p className="text-sm text-stone-700">
              Du må sette opp gård først for å aktivere bilag.
            </p>
            <div className="mt-4">
              <Button href="/farm/setup" variant="outline" showArrow>
                GÅ TIL OPPSETT
              </Button>
            </div>
          </Card>
        )}

        {farmId && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              <Card hoverEffect={false} className="p-5 bg-white">
                <p className="text-xs font-bold uppercase tracking-wider text-stone-500">{hasFilters ? 'Treff' : 'Bilag totalt'}</p>
                <p className="text-2xl font-serif text-stone-900 mt-1">{summary.count}</p>
              </Card>
              <Card hoverEffect={false} className="p-5 bg-white">
                <p className="text-xs font-bold uppercase tracking-wider text-stone-500">{hasFilters ? 'Førte i treff' : 'Førte bilag'}</p>
                <p className="text-2xl font-serif text-stone-900 mt-1">{summary.booked}</p>
              </Card>
              <Card hoverEffect={false} className="p-5 bg-white">
                <p className="text-xs font-bold uppercase tracking-wider text-stone-500">{hasFilters ? 'Sum treff' : 'Sum ført'}</p>
                <p className="text-2xl font-serif text-stone-900 mt-1">
                  {new Intl.NumberFormat('nb-NO', { style: 'currency', currency: 'NOK', maximumFractionDigits: 0 }).format(summary.total)}
                </p>
              </Card>
            </div>

            <Card hoverEffect={false} className="p-5 bg-white mb-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="sm:col-span-2">
                  <label htmlFor="voucher-search" className="block text-xs font-bold uppercase tracking-wider text-stone-500 mb-1">
                    Søk i bilag
                  </label>
                  <input
                    id="voucher-search"
                    type="search"
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    placeholder="Filnavn, beskrivelse, leverandør eller konto"
                    className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-900 focus:border-bonde-green focus:outline-none focus:ring-2 focus:ring-bonde-green/20"
                  />
                </div>
                <div>
                  <label htmlFor="voucher-status" className="block text-xs font-bold uppercase tracking-wider text-stone-500 mb-1">
                    Status
                  </label>
                  <select
                    id="voucher-status"
                    value={statusFilter}
                    onChange={(event) => setStatusFilter(event.target.value)}
                    className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-900 focus:border-bonde-green focus:outline-none focus:ring-2 focus:ring-bonde-green/20"
                  >
                    <option value="">Alle statuser</option>
                    <option value="mottatt">Mottatt</option>
                    <option value="ført">Ført</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    type="button"
                    onClick={clearFilters}
                    disabled={!hasFilters}
                    className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm font-semibold text-stone-700 hover:border-bonde-green hover:text-bonde-green disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Nullstill filtre
                  </button>
                </div>
                <div>
                  <label htmlFor="voucher-date-from" className="block text-xs font-bold uppercase tracking-wider text-stone-500 mb-1">
                    Fra dato
                  </label>
                  <input
                    id="voucher-date-from"
                    type="date"
                    value={dateFrom}
                    max={dateTo || undefined}
                    onChange={(event) => setDateFrom(event.target.value)}
                    className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-900 focus:border-bonde-green focus:outline-none focus:ring-2 focus:ring-bonde-green/20"
                  />
                </div>
                <div>
                  <label htmlFor="voucher-date-to" className="block text-xs font-bold uppercase tracking-wider text-stone-500 mb-1">
                    Til dato
                  </label>
                  <input
                    id="voucher-date-to"
                    type="date"
                    value={dateTo}
                    min={dateFrom || undefined}
                    onChange={(event) => setDateTo(event.target.value)}
                    className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-900 focus:border-bonde-green focus:outline-none focus:ring-2 focus:ring-bonde-green/20"
                  />
                </div>
              </div>
            </Card>

            <Card hoverEffect={false} className="p-0 bg-white overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-stone-50 border-b border-stone-200">
                    <tr>
                      <th className="text-left p-3 font-semibold text-stone-700">Dato</th>
                      <th className="text-left p-3 font-semibold text-stone-700">Bilag</th>
                      <th className="text-left p-3 font-semibold text-stone-700">Konto</th>
                      <th className="text-left p-3 font-semibold text-stone-700">Beløp</th>
                      <th className="text-left p-3 font-semibold text-stone-700">Status</th>
                      <th className="text-left p-3 font-semibold text-stone-700">Fil</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading && (
                      <tr>
                        <td colSpan={6} className="p-6 text-center text-stone-500">Laster bilag...</td>
                      </tr>
                    )}
                    {!loading && error && (
                      <tr>
                        <td colSpan={6} className="p-6 text-center text-red-700">{error}</td>
                      </tr>
                    )}
                    {!loading && !error && items.length === 0 && (
                      <tr>
                        <td colSpan={6} className="p-6 text-center text-stone-500">
                          {hasFilters ? 'Ingen bilag samsvarer med søket eller filtrene.' : 'Ingen bilag ennå. Start med å registrere et bilag.'}
                        </td>
                      </tr>
                    )}
                    {!loading && !error && items.map((item) => (
                      <tr key={item.id} className="border-b border-stone-100">
                        <td className="p-3 text-stone-700">{item.voucher_date}</td>
                        <td className="p-3 text-stone-900 font-medium">{item.description || item.file_name}</td>
                        <td className="p-3 text-stone-700">{item.account_code || 'Ikke ført'}</td>
                        <td className="p-3 text-stone-900">
                          {new Intl.NumberFormat('nb-NO', { style: 'currency', currency: 'NOK', maximumFractionDigits: 0 }).format(item.amount || 0)}
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-semibold ${item.status === 'ført' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                            {item.status}
                          </span>
                        </td>
                        <td className="p-3">
                          <Link href={item.blob_url} target="_blank" className="text-bonde-green hover:underline">
                            Åpne
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        )}
      </main>
    </div>
  )
}
