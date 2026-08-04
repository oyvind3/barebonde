'use client'

import { useEffect, useState } from 'react'
import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { apiErrorMessage, apiFetch, bootstrapIdentity } from '@/lib/api'

const FARM_ID_KEY = 'barebonde_active_farm_id'

type MonthlyRow = { month: string; income: number; expense: number; net: number }
type GrantRow = { voucher_date: string; amount: number; description: string; period: string }
type JournalRow = { voucher_id: string; date: string; file_name: string; status: string; account_code: string | null; mva_code: string | null; amount: number }
type LiquidityPoint = { date: string; description: string; balance: number }

export default function ReportsPage() {
  const [farmId, setFarmId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [monthly, setMonthly] = useState<MonthlyRow[]>([])
  const [vat, setVat] = useState({ incoming_vat: 0, outgoing_vat: 0, estimated_settlement: 0 })
  const [grants, setGrants] = useState<GrantRow[]>([])
  const [journal, setJournal] = useState<JournalRow[]>([])
  const [liquidity, setLiquidity] = useState<{ opening_balance: number; closing_balance: number; points: LiquidityPoint[] }>({
    opening_balance: 0,
    closing_balance: 0,
    points: [],
  })

  useEffect(() => {
    const storedFarmId = window.localStorage.getItem(FARM_ID_KEY) || ''
    bootstrapIdentity(storedFarmId)
      .then((identity) => {
        const activeFarmId = identity?.active_farm?.id || ''
        setFarmId(activeFarmId)
        if (activeFarmId) window.localStorage.setItem(FARM_ID_KEY, activeFarmId)
        else window.localStorage.removeItem(FARM_ID_KEY)
      })
      .catch(() => {
        setError('Kunne ikke hente den aktive gården.')
        setFarmId('')
      })
  }, [])

  useEffect(() => {
    if (!farmId) {
      setLoading(false)
      return
    }

    const run = async () => {
      setLoading(true)
      setError('')
      try {
        const [monthlyRes, vatRes, grantsRes, journalRes, liquidityRes] = await Promise.all([
          apiFetch(`/api/farms/${encodeURIComponent(farmId)}/reports/monthly`),
          apiFetch(`/api/farms/${encodeURIComponent(farmId)}/reports/vat`),
          apiFetch(`/api/farms/${encodeURIComponent(farmId)}/reports/grants`),
          apiFetch(`/api/farms/${encodeURIComponent(farmId)}/reports/journal`),
          apiFetch(`/api/farms/${encodeURIComponent(farmId)}/reports/liquidity?opening_balance=0`),
        ])

        if (!monthlyRes.ok || !vatRes.ok || !grantsRes.ok || !journalRes.ok || !liquidityRes.ok) {
          const failedResponse = [monthlyRes, vatRes, grantsRes, journalRes, liquidityRes].find((response) => !response.ok)
          throw new Error(await apiErrorMessage(failedResponse!, 'Klarte ikke hente rapportdata'))
        }

        const monthlyData = await monthlyRes.json()
        const vatData = await vatRes.json()
        const grantsData = await grantsRes.json()
        const journalData = await journalRes.json()
        const liquidityData = await liquidityRes.json()

        setMonthly(monthlyData.rows || [])
        setVat(vatData)
        setGrants(grantsData.rows || [])
        setJournal(journalData.rows || [])
        setLiquidity(liquidityData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Ukjent feil')
      } finally {
        setLoading(false)
      }
    }

    run()
  }, [farmId])

  const money = (value: number) =>
    new Intl.NumberFormat('nb-NO', { style: 'currency', currency: 'NOK', maximumFractionDigits: 0 }).format(value)

  return (
    <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full">
        <div className="mb-8">
          <h1 className="text-3xl sm:text-4xl font-serif text-stone-900">Rapporter</h1>
          <p className="text-stone-600 text-sm mt-1">Resultat, MVA, tilskudd, journal og likviditet samlet.</p>
        </div>

        {!farmId && (
          <Card hoverEffect={false} className="p-6 bg-white mb-8">
            <p className="text-sm text-stone-700">Sett opp gård først for å se rapporter.</p>
          </Card>
        )}

        {farmId && loading && (
          <Card hoverEffect={false} className="p-6 bg-white mb-8">
            <p className="text-sm text-stone-700">Laster rapporter...</p>
          </Card>
        )}

        {farmId && error && (
          <Card hoverEffect={false} className="p-6 bg-white mb-8">
            <p className="text-sm text-red-700">{error}</p>
          </Card>
        )}

        {farmId && !loading && !error && (
          <div className="space-y-6">
            <Card hoverEffect={false} className="p-6 bg-white">
              <h2 className="text-lg font-semibold text-stone-900 mb-3">Resultat per måned</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-stone-200">
                      <th className="text-left p-2">Måned</th>
                      <th className="text-left p-2">Inntekt</th>
                      <th className="text-left p-2">Kostnad</th>
                      <th className="text-left p-2">Netto</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthly.map((row) => (
                      <tr key={row.month} className="border-b border-stone-100">
                        <td className="p-2">{row.month}</td>
                        <td className="p-2">{money(row.income)}</td>
                        <td className="p-2">{money(row.expense)}</td>
                        <td className="p-2 font-semibold">{money(row.net)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card hoverEffect={false} className="p-5 bg-white">
                <p className="text-xs uppercase tracking-wider font-semibold text-stone-500">Inngående MVA</p>
                <p className="text-2xl font-serif text-stone-900 mt-1">{money(vat.incoming_vat)}</p>
              </Card>
              <Card hoverEffect={false} className="p-5 bg-white">
                <p className="text-xs uppercase tracking-wider font-semibold text-stone-500">Utgående MVA</p>
                <p className="text-2xl font-serif text-stone-900 mt-1">{money(vat.outgoing_vat)}</p>
              </Card>
              <Card hoverEffect={false} className="p-5 bg-white">
                <p className="text-xs uppercase tracking-wider font-semibold text-stone-500">Estimat MVA-oppgjør</p>
                <p className="text-2xl font-serif text-stone-900 mt-1">{money(vat.estimated_settlement)}</p>
              </Card>
            </div>

            <Card hoverEffect={false} className="p-6 bg-white">
              <h2 className="text-lg font-semibold text-stone-900 mb-3">Tilskudd og periodisering</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-stone-200">
                      <th className="text-left p-2">Dato</th>
                      <th className="text-left p-2">Beskrivelse</th>
                      <th className="text-left p-2">Periode</th>
                      <th className="text-left p-2">Beløp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {grants.map((row, index) => (
                      <tr key={`${row.voucher_date}-${index}`} className="border-b border-stone-100">
                        <td className="p-2">{row.voucher_date}</td>
                        <td className="p-2">{row.description}</td>
                        <td className="p-2">{row.period}</td>
                        <td className="p-2">{money(row.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card hoverEffect={false} className="p-6 bg-white">
              <h2 className="text-lg font-semibold text-stone-900 mb-3">Bilagsjournal</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-stone-200">
                      <th className="text-left p-2">Dato</th>
                      <th className="text-left p-2">Fil</th>
                      <th className="text-left p-2">Status</th>
                      <th className="text-left p-2">Konto</th>
                      <th className="text-left p-2">MVA</th>
                      <th className="text-left p-2">Beløp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {journal.map((row) => (
                      <tr key={row.voucher_id} className="border-b border-stone-100">
                        <td className="p-2">{row.date}</td>
                        <td className="p-2">{row.file_name}</td>
                        <td className="p-2">{row.status}</td>
                        <td className="p-2">{row.account_code || '-'}</td>
                        <td className="p-2">{row.mva_code || '-'}</td>
                        <td className="p-2">{money(row.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card hoverEffect={false} className="p-6 bg-white">
              <h2 className="text-lg font-semibold text-stone-900 mb-3">Likviditetsoversikt</h2>
              <p className="text-sm text-stone-700 mb-4">
                Startsaldo: {money(liquidity.opening_balance)} | Sluttsaldo: {money(liquidity.closing_balance)}
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-stone-200">
                      <th className="text-left p-2">Dato</th>
                      <th className="text-left p-2">Beskrivelse</th>
                      <th className="text-left p-2">Balanse</th>
                    </tr>
                  </thead>
                  <tbody>
                    {liquidity.points.map((point, index) => (
                      <tr key={`${point.date}-${index}`} className="border-b border-stone-100">
                        <td className="p-2">{point.date}</td>
                        <td className="p-2">{point.description}</td>
                        <td className="p-2">{money(point.balance)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}
      </main>
    </div>
  )
}
