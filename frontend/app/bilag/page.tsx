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

  useEffect(() => {
    const storedFarmId = window.localStorage.getItem(FARM_ID_KEY) || ''
    setFarmId(storedFarmId)
  }, [])

  useEffect(() => {
    if (!farmId) {
      setLoading(false)
      return
    }

    const fetchVouchers = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await fetch(`${API_BASE}/api/accounting/vouchers?farm_id=${encodeURIComponent(farmId)}`)
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
  }, [farmId])

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
                <p className="text-xs font-bold uppercase tracking-wider text-stone-500">Bilag totalt</p>
                <p className="text-2xl font-serif text-stone-900 mt-1">{summary.count}</p>
              </Card>
              <Card hoverEffect={false} className="p-5 bg-white">
                <p className="text-xs font-bold uppercase tracking-wider text-stone-500">Førte bilag</p>
                <p className="text-2xl font-serif text-stone-900 mt-1">{summary.booked}</p>
              </Card>
              <Card hoverEffect={false} className="p-5 bg-white">
                <p className="text-xs font-bold uppercase tracking-wider text-stone-500">Sum ført</p>
                <p className="text-2xl font-serif text-stone-900 mt-1">
                  {new Intl.NumberFormat('nb-NO', { style: 'currency', currency: 'NOK', maximumFractionDigits: 0 }).format(summary.total)}
                </p>
              </Card>
            </div>

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
                        <td colSpan={6} className="p-6 text-center text-stone-500">Ingen bilag ennå. Start med å registrere et bilag.</td>
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
