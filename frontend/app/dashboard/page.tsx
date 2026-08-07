'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { apiErrorMessage, apiFetch } from '@/lib/api'
import { useIdentity } from '@/lib/identity'

type MonthlyRow = { month: string; income: number; expense: number; net: number }

export default function Dashboard() {
  const { status, identity, activeFarm, setActiveFarm } = useIdentity()
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [monthlyRows, setMonthlyRows] = useState<MonthlyRow[]>([])
  const [vat, setVat] = useState({ incoming_vat: 0, outgoing_vat: 0, estimated_settlement: 0 })
  const [journalCount, setJournalCount] = useState(0)

  const farmId = activeFarm?.id || ''

  // Redirect unauthenticated users
  useEffect(() => {
    if (status === 'anonymous' || status === 'error') {
      router.replace('/login')
    }
  }, [status, router])

  // Redirect users without a farm
  useEffect(() => {
    if (status === 'authenticated' && identity && !activeFarm) {
      router.replace('/farm/setup')
    }
  }, [status, identity, activeFarm, router])

  useEffect(() => {
    if (!farmId) {
      setLoading(false)
      return
    }

    const controller = new AbortController()
    const fetchData = async () => {
      setLoading(true)
      setError('')
      try {
        const [monthlyRes, vatRes, journalRes] = await Promise.all([
          apiFetch(`/api/farms/${encodeURIComponent(farmId)}/reports/monthly`, { signal: controller.signal }),
          apiFetch(`/api/farms/${encodeURIComponent(farmId)}/reports/vat`, { signal: controller.signal }),
          apiFetch(`/api/farms/${encodeURIComponent(farmId)}/reports/journal`, { signal: controller.signal }),
        ])

        if (!monthlyRes.ok || !vatRes.ok || !journalRes.ok) {
          const failedResponse = [monthlyRes, vatRes, journalRes].find((response) => !response.ok)
          throw new Error(await apiErrorMessage(failedResponse!, 'Klarte ikke hente regnskapsdata'))
        }

        const monthlyData = await monthlyRes.json()
        const vatData = await vatRes.json()
        const journalData = await journalRes.json()

        if (!controller.signal.aborted) {
          setMonthlyRows(monthlyData.rows || [])
          setVat(vatData)
          setJournalCount((journalData.rows || []).length)
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        setError(err instanceof Error ? err.message : 'Ukjent feil')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }

    fetchData()
    return () => controller.abort()
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

  if (status === 'loading' || status === 'authenticated' && !identity) {
    return (
      <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
        <Navbar />
        <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full">
          <div className="animate-pulse space-y-6">
            <div className="h-8 w-64 rounded bg-stone-200" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {[1, 2, 3, 4].map((i) => <div key={i} className="h-32 rounded-xl bg-stone-200" />)}
            </div>
          </div>
        </main>
      </div>
    )
  }

  if (!identity || !activeFarm) return null

  return (
    <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full relative">
        {/* Dashboard Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 pb-6 border-b border-stone-200/80">
          <div>
            <span className="text-xs font-bold uppercase tracking-widest text-bonde-green bg-bonde-light px-3 py-1 rounded-full mb-2 inline-block">
              Gårdsoversikt
            </span>
            <h1 className="text-3xl sm:text-4xl font-serif text-stone-900">
              {activeFarm.name}
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
          </div>
        </div>

        {identity.memberships.length > 1 && (
          <div className="mb-6 flex max-w-sm flex-col gap-1">
            <label htmlFor="active-farm" className="text-xs font-bold uppercase tracking-wider text-stone-600">Aktiv gård</label>
            <select id="active-farm" value={farmId} onChange={(event) => setActiveFarm(event.target.value)} className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm text-stone-800">
              {identity.memberships.map((m) => <option key={m.farm.id} value={m.farm.id}>{m.farm.name}</option>)}
            </select>
          </div>
        )}

        {loading && (
          <Card hoverEffect={false} className="p-6 bg-white mb-10">
            <p className="text-sm text-stone-700">Laster regnskapsdata...</p>
          </Card>
        )}

        {error && (
          <Card hoverEffect={false} className="p-6 bg-white mb-10">
            <p className="text-sm text-red-700">{error}</p>
          </Card>
        )}

        {identity.onboarding && !identity.onboarding.completed && (
          <Card hoverEffect={false} className="mb-8 border border-amber-200 bg-amber-50 p-5">
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div>
                <p className="font-semibold text-stone-900">Kom i gang med Barebonde</p>
                <p className="text-sm text-stone-700">{identity.onboarding.completed_steps.length} av 7 steg registrert. Bankkonto er valgfri og blokkerer ikke bruk.</p>
              </div>
              <Button href="/onboarding" variant="outline">Fortsett</Button>
            </div>
          </Card>
        )}

        {identity.subscription && (
          <Card hoverEffect={false} className="mb-8 flex flex-col gap-3 border border-emerald-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-stone-500">Aktiv plan</p>
              <p className="mt-1 text-lg font-semibold text-stone-900">{identity.subscription.display_name}</p>
            </div>
          </Card>
        )}

        {/* Metrics Grid */}
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

        {/* Empty state when no data */}
        {!loading && !error && journalCount === 0 && (
          <Card hoverEffect={false} className="p-8 border border-stone-200 bg-white rounded-2xl mb-10 text-center">
            <span className="text-3xl mb-4 block">📄</span>
            <h3 className="text-lg font-bold text-stone-900 mb-2">Ingen bilag registrert ennå</h3>
            <p className="text-sm text-stone-600 mb-6 max-w-md mx-auto">
              Last opp din første faktura for å komme i gang. OCR leser feltene automatisk, og du kontrollerer før bokføring.
            </p>
            <Button href="/bilag/new" variant="primary" showArrow>
              LAST OPP FØRSTE BILAG
            </Button>
          </Card>
        )}

        {/* Info banner */}
        {journalCount > 0 && (
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
        )}
      </main>
    </div>
  )
}