'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { apiErrorMessage, apiFetch } from '@/lib/api'
import { useIdentity } from '@/lib/identity'

type Customer = {
  id: string
  name: string
  org_number: string
  email: string
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

export default function KunderPage() {
  const { status, activeFarm } = useIdentity()
  const farmId = activeFarm?.id || ''
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [search, setSearch] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [editingId, setEditingId] = useState('')

  const [form, setForm] = useState({ name: '', org_number: '', email: '', address: '', postal_code: '', city: '' })
  const [brregQuery, setBrregQuery] = useState('')
  const [brregResults, setBrregResults] = useState<BrregResult[]>([])
  const [brregSearching, setBrregSearching] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (status === 'loading') return
    if (!farmId) {
      setError('Ingen aktiv gård er valgt.')
      setLoading(false)
      return
    }
    const fetchCustomers = async () => {
      setLoading(true)
      try {
        const response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/customers`)
        if (!response.ok) throw new Error(await apiErrorMessage(response, 'Kunne ikke hente kunder.'))
        const data = await response.json()
        setCustomers(data.customers || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Kunne ikke hente kunder.')
      } finally {
        setLoading(false)
      }
    }
    fetchCustomers()
  }, [farmId, status])

  const filtered = customers.filter((customer) => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    return (
      customer.name.toLowerCase().includes(q) ||
      (customer.org_number || '').includes(q) ||
      (customer.email || '').toLowerCase().includes(q) ||
      (customer.city || '').toLowerCase().includes(q)
    )
  })

  const searchBrreg = async () => {
    if (status === 'loading') return
    if (!farmId) {
      setError('Ingen aktiv gård er valgt.')
      return
    }
    if (brregQuery.trim().length < 2) return
    setBrregSearching(true)
    setBrregResults([])
    try {
      const response = await apiFetch(
        `/api/farms/${encodeURIComponent(farmId)}/customers/brreg-search?query=${encodeURIComponent(brregQuery.trim())}`
      )
      if (!response.ok) throw new Error(await apiErrorMessage(response, 'Søket feilet.'))
      const data = await response.json()
      setBrregResults(data.results || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Søket feilet.')
    } finally {
      setBrregSearching(false)
    }
  }

  const pickBrregResult = (result: BrregResult) => {
    setForm({ name: result.name, org_number: result.org_number, email: '', address: result.address, postal_code: result.postal_code, city: result.city })
    setBrregResults([])
  }

  const saveCustomer = async () => {
    if (status === 'loading') return
    if (!farmId) {
      setError('Ingen aktiv gård er valgt.')
      return
    }
    if (!form.name.trim()) {
      setError('Kunden mangler navn.')
      return
    }
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      const payload = {
        name: form.name.trim(),
        org_number: form.org_number || null,
        email: form.email || null,
        address: form.address || null,
        postal_code: form.postal_code || null,
        city: form.city || null,
        country_code: 'NO',
      }
      let response: Response
      if (editingId) {
        response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/customers/${encodeURIComponent(editingId)}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      } else {
        response = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/customers`, {
          method: 'POST',
          body: JSON.stringify({ ...payload, brreg_verified: Boolean(form.org_number) }),
        })
      }
      if (!response.ok) throw new Error(await apiErrorMessage(response, 'Kunne ikke lagre kunden.'))
      setSuccess(editingId ? 'Kunden er oppdatert.' : 'Kunden er opprettet.')
      setShowNew(false)
      setEditingId('')
      setForm({ name: '', org_number: '', email: '', address: '', postal_code: '', city: '' })
      const listResponse = await apiFetch(`/api/farms/${encodeURIComponent(farmId)}/customers`)
      if (listResponse.ok) {
        const data = await listResponse.json()
        setCustomers(data.customers || [])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kunne ikke lagre kunden.')
    } finally {
      setSaving(false)
    }
  }

  const startEdit = (customer: Customer) => {
    setEditingId(customer.id)
    setShowNew(true)
    setForm({
      name: customer.name,
      org_number: customer.org_number || '',
      email: customer.email || '',
      address: customer.address || '',
      postal_code: customer.postal_code || '',
      city: customer.city || '',
    })
  }

  return (
    <>
      <Navbar />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-stone-900">Kunder</h1>
            <p className="text-sm text-stone-600">Kunderegister for gården.</p>
          </div>
          <div className="flex gap-2">
            <Link href="/faktura" className="text-sm font-semibold text-bonde-green hover:underline">
              ← Til fakturaer
            </Link>
            <Button onClick={() => { setShowNew((prev) => !prev); setEditingId(''); setForm({ name: '', org_number: '', email: '', address: '', postal_code: '', city: '' }) }}>
              {showNew ? 'Lukk' : 'Ny kunde'}
            </Button>
          </div>
        </div>

        {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>}
        {success && <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">{success}</div>}

        {showNew && (
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-stone-900">{editingId ? 'Rediger kunde' : 'Ny kunde'}</h2>
            {!editingId && (
              <div className="mb-4">
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
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">Navn *</label>
                <input value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">Org.nr.</label>
                <input value={form.org_number} onChange={(event) => setForm((prev) => ({ ...prev, org_number: event.target.value }))} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">E-post</label>
                <input type="email" value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">Adresse</label>
                <input value={form.address} onChange={(event) => setForm((prev) => ({ ...prev, address: event.target.value }))} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">Postnummer</label>
                <input value={form.postal_code} onChange={(event) => setForm((prev) => ({ ...prev, postal_code: event.target.value }))} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-stone-700">Sted</label>
                <input value={form.city} onChange={(event) => setForm((prev) => ({ ...prev, city: event.target.value }))} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm" />
              </div>
            </div>
            <div className="mt-4 flex justify-end">
              <Button type="button" onClick={saveCustomer} disabled={saving || status === 'loading' || !farmId}>
                {saving ? 'Lagrer …' : editingId ? 'Lagre endringer' : 'Opprett kunde'}
              </Button>
            </div>
          </Card>
        )}

        <div className="mt-6">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Søk i kunder …"
            className="mb-4 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm sm:max-w-sm"
          />
          {loading ? (
            <p className="text-sm text-stone-500">Henter kunder …</p>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-stone-500">Ingen kunder funnet.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-stone-200 bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
                    <th className="px-4 py-3">Navn</th>
                    <th className="px-4 py-3">Org.nr.</th>
                    <th className="px-4 py-3">E-post</th>
                    <th className="px-4 py-3">Sted</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((customer) => (
                    <tr key={customer.id} className="border-b border-stone-100 last:border-0">
                      <td className="px-4 py-3 font-medium text-stone-900">{customer.name}</td>
                      <td className="px-4 py-3 text-stone-600">{customer.org_number || '–'}</td>
                      <td className="px-4 py-3 text-stone-600">{customer.email || '–'}</td>
                      <td className="px-4 py-3 text-stone-600">{customer.city || '–'}</td>
                      <td className="px-4 py-3 text-right">
                        <button type="button" onClick={() => startEdit(customer)} className="text-sm font-semibold text-bonde-green hover:underline">
                          Rediger
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </>
  )
}