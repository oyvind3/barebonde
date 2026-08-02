'use client'

import { useEffect, useMemo, useState } from 'react'
import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

type MonthlyRow = { month: string; income: number; expense: number; net: number }

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const FARM_ID_KEY = 'barebonde_active_farm_id'

export default function Dashboard() {
  const [farmId, setFarmId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [monthlyRows, setMonthlyRows] = useState<MonthlyRow[]>([])
  const [vat, setVat] = useState({ incoming_vat: 0, outgoing_vat: 0, estimated_settlement: 0 })
  const [journalCount, setJournalCount] = useState(0)

  useEffect(() => {
    const storedFarmId = window.localStorage.getItem(FARM_ID_KEY) || ''
    setFarmId(storedFarmId)
  }, [])

  useEffect(() => {
    if (!farmId) {
      setLoading(false)
      return
    }

    const fetchData = async () => {
      setLoading(true)
      setError('')
      try {
        const [monthlyRes, vatRes, journalRes] = await Promise.all([
          fetch(`${API_BASE}/api/accounting/reports/monthly?farm_id=${encodeURIComponent(farmId)}`),
          fetch(`${API_BASE}/api/accounting/reports/vat?farm_id=${encodeURIComponent(farmId)}`),
          fetch(`${API_BASE}/api/accounting/reports/journal?farm_id=${encodeURIComponent(farmId)}`),
        ])

        if (!monthlyRes.ok || !vatRes.ok || !journalRes.ok) {
          throw new Error('Klarte ikke hente regnskapsdata')
        }

        const monthlyData = await monthlyRes.json()
        const vatData = await vatRes.json()
        const journalData = await journalRes.json()

        setMonthlyRows(monthlyData.rows || [])
        setVat(vatData)
        setJournalCount((journalData.rows || []).length)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ukjent feil')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [farmId])

  const totals = useMemo(() => {
    return monthlyRows.reduce(
      (acc, row) => {
        acc.income += row.income || 0
        acc.expense += row.expense || 0
        return acc
      },
      { income: 0, expense: 0 }
    )
  }, [monthlyRows])

  const money = (value: number) =>
    new Intl.NumberFormat('nb-NO', { style: 'currency', currency: 'NOK', maximumFractionDigits: 0 }).format(value)

  return (
    <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full">
        {/* Dashboard Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 pb-6 border-b border-stone-200/80">
          <div>
            <span className="text-xs font-bold uppercase tracking-widest text-bonde-green bg-bonde-light px-3 py-1 rounded-full mb-2 inline-block">
              Gårdsoversikt
            </span>
            <h1 className="text-3xl sm:text-4xl font-serif text-stone-900">
              Gårdens kontrollpanel
            </h1>
            <p className="text-stone-600 text-sm mt-1">
              Regnskap, bilag og rapporter samlet på ett sted.
            </p>
          </div>

          <div className="mt-4 md:mt-0 flex gap-3">
            <Button href="/bilag/new" variant="primary" showArrow>
              NYTT BILAG
            </Button>
            <Button href="/reports" variant="outline" showArrow>
              RAPPORTER
            </Button>
            <Button href="/farm/setup" variant="outline" showArrow>
              ENDRE GÅRD
            </Button>
          </div>
        </div>

        {!farmId && (
          <Card hoverEffect={false} className="p-6 bg-white mb-10">
            <p className="text-sm text-stone-700">Sett opp gård først for å aktivere regnskap og bilag.</p>
          </Card>
        )}

        {farmId && loading && (
          <Card hoverEffect={false} className="p-6 bg-white mb-10">
            <p className="text-sm text-stone-700">Laster regnskapsdata...</p>
          </Card>
        )}

        {farmId && error && (
          <Card hoverEffect={false} className="p-6 bg-white mb-10">
            <p className="text-sm text-red-700">{error}</p>
          </Card>
        )}

        {/* Metrics Grid */}
        {farmId && !loading && !error && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          <Card hoverEffect={false} className="p-6 border-l-4 border-l-bonde-green bg-white">
            <p className="text-xs font-bold uppercase tracking-wider text-stone-600 mb-1">Inngående penger</p>
            <p className="text-3xl font-serif text-stone-900 font-bold">{money(totals.income)}</p>
            <p className="text-xs text-stone-600 mt-1">Førte inntekter</p>
          </Card>

          <Card hoverEffect={false} className="p-6 border-l-4 border-l-bonde-green bg-white">
            <p className="text-xs font-bold uppercase tracking-wider text-stone-600 mb-1">Utgående kostnader</p>
            <p className="text-3xl font-serif text-stone-900 font-bold">{money(totals.expense)}</p>
            <p className="text-xs text-stone-600 mt-1">Førte utgifter</p>
          </Card>

          <Card hoverEffect={false} className="p-6 border-l-4 border-l-bonde-green bg-white">
            <p className="text-xs font-bold uppercase tracking-wider text-stone-600 mb-1">MVA-estimat</p>
            <p className="text-3xl font-serif text-bonde-green font-bold">{money(vat.estimated_settlement)}</p>
            <p className="text-xs text-stone-600 mt-1">Utgående minus inngående</p>
          </Card>

          <Card hoverEffect={false} className="p-6 border-l-4 border-l-bonde-green bg-white">
            <p className="text-xs font-bold uppercase tracking-wider text-stone-600 mb-1">Aktive bilag</p>
            <p className="text-3xl font-serif text-stone-900 font-bold">{journalCount}</p>
            <p className="text-xs text-stone-600 mt-1">Registrerte bilag</p>
          </Card>
          </div>
        )}

        {/* Demo info banner */}
        <Card hoverEffect={false} className="p-8 border border-amber-200/80 bg-amber-50/60 rounded-2xl mb-10">
          <div className="flex items-start space-x-4">
            <span className="text-2xl">🌱</span>
            <div>
              <h3 className="text-base font-bold text-stone-900 uppercase tracking-wide mb-1">
                Enkel flyt først
              </h3>
              <p className="text-sm text-stone-700 leading-relaxed">
                Start med bilag: last opp, velg konto, før. Rapporter oppdateres automatisk når bilag føres.
              </p>
            </div>
          </div>
        </Card>
      </main>
    </div>
  )
}
