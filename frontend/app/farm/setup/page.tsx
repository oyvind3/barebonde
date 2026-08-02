'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { getOrCreateOnboardingUserId } from '@/lib/onboardingUser'

interface FarmFormData {
  name: string
  org_number: string
}

interface BrregLookupResult {
  org_number: string
  name: string
  organization_form: string
  postal_code: string
  city: string
  municipality: string
  address: string
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function FarmSetupPage() {
  const router = useRouter()
  const [formData, setFormData] = useState<FarmFormData>({
    name: '',
    org_number: '',
  })
  const [lookupLoading, setLookupLoading] = useState(false)
  const [lookupResult, setLookupResult] = useState<BrregLookupResult | null>(null)
  const [lookupError, setLookupError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    const nextValue = name === 'org_number' ? value.replace(/\D/g, '').slice(0, 9) : value

    if (name === 'org_number') {
      setLookupResult(null)
      setLookupError(null)
    }

    setFormData(prev => ({
      ...prev,
      [name]: nextValue,
    }))
  }

  const handleLookup = async () => {
    setLookupError(null)
    setError(null)

    if (!/^\d{9}$/.test(formData.org_number)) {
      setLookupError('Skriv inn 9 sifre først')
      return
    }

    setLookupLoading(true)
    try {
      const response = await axios.get<BrregLookupResult>(
        `${API_BASE_URL}/api/farms/lookup/${formData.org_number}`
      )

      setLookupResult(response.data)
      setFormData(prev => ({
        ...prev,
        name: prev.name || response.data.name,
      }))
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setLookupError(err.response.data.detail)
      } else {
        setLookupError('Klarte ikke slå opp akkurat nå. Prøv igjen.')
      }
    } finally {
      setLookupLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      if (!/^\d{9}$/.test(formData.org_number)) {
        setError('Organisasjonsnummeret må være 9 sifre')
        setLoading(false)
        return
      }

      const onboardingUserId = getOrCreateOnboardingUserId()

      await axios.post(
        `${API_BASE_URL}/api/farms`,
        {
          name: formData.name.trim(),
          org_number: formData.org_number,
        }
        ,
        {
          headers: {
            'x-onboarding-user-id': onboardingUserId,
          },
        }
      )

      router.push('/dashboard')
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setError('Denne gården er allerede registrert i systemet')
      } else if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Feil ved opprettelse av gård. Prøv igjen.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow py-16 px-4">
        <div className="max-w-xl mx-auto">
          <Card hoverEffect={false} className="p-8 sm:p-12 border border-stone-200/80 rounded-2xl shadow-card">
            <div className="text-center mb-8">
              <span className="text-xs font-bold uppercase tracking-widest text-bonde-green bg-bonde-light px-3 py-1 rounded-full mb-3 inline-block">
                Onboarding
              </span>
              <h1 className="text-3xl sm:text-4xl font-serif text-stone-900 mb-2">
                Registrer gården din
              </h1>
              <p className="text-stone-600 text-sm">
                Start med gårdens organisasjonsnummer. Vi henter resten fra Brønnøysund.
              </p>
            </div>

            {error && (
              <div className="bg-rose-50 border-l-4 border-rose-500 text-rose-800 p-4 text-sm rounded-r-lg mb-6">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="name" className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-2">
                  Gårdsnavn
                </label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-bonde-green text-sm bg-white"
                  placeholder="Fylles automatisk etter oppslag"
                />
              </div>

              <div>
                <label htmlFor="org_number" className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-2">
                  Organisasjonsnummer *
                </label>
                <input
                  type="text"
                  id="org_number"
                  name="org_number"
                  value={formData.org_number}
                  onChange={handleInputChange}
                  required
                  maxLength={9}
                  className="w-full px-4 py-3 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-bonde-green text-sm bg-white"
                  placeholder="9 siffer (f.eks. 123456789)"
                />
                <p className="text-xs text-stone-500 mt-2">
                  Bruk nummeret som står i Enhetsregisteret.
                </p>
              </div>

              <div className="space-y-3">
                <Button
                  type="button"
                  variant="secondary"
                  fullWidth
                  onClick={handleLookup}
                  disabled={lookupLoading}
                >
                  {lookupLoading ? 'SLÅR OPP...' : 'SLÅ OPP I BRØNNØYSUND'}
                </Button>

                {lookupError && (
                  <div className="bg-amber-50 border-l-4 border-amber-400 text-amber-900 p-4 text-sm rounded-r-lg">
                    {lookupError}
                  </div>
                )}

                {lookupResult && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-sm text-emerald-900">
                    <p className="font-semibold">Fant: {lookupResult.name}</p>
                    <p>{lookupResult.address}{lookupResult.address ? ', ' : ''}{lookupResult.postal_code} {lookupResult.city}</p>
                    <p className="text-emerald-700 text-xs mt-1">Kommune: {lookupResult.municipality}</p>
                  </div>
                )}
              </div>

              <Button
                type="submit"
                disabled={loading}
                variant="primary"
                fullWidth
                showArrow
              >
                {loading ? 'OPPRETTER GÅRD...' : 'OPPRETT GÅRD OG FORTSETT'}
              </Button>
            </form>
          </Card>
        </div>
      </main>
    </div>
  )
}
