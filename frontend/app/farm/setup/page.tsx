'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { getOrCreateOnboardingUserId } from '@/lib/onboardingUser'

interface BrregCompany {
  org_number: string
  name: string
  organization_form: string
  postal_code: string
  city: string
  municipality: string
  address: str
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function FarmSetupPage() {
  const router = useRouter()

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCompany, setSelectedCompany] = useState<BrregCompany | null>(null)
  const [searchResults, setSearchResults] = useState<BrregCompany[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Debounce search query to BRREG API
  useEffect(() => {
    const trimmed = searchQuery.trim()
    if (!trimmed || trimmed.length < 2) {
      setSearchResults([])
      setIsSearching(false)
      return
    }

    // If user typed custom text while a company is selected, clear selection unless it matches org_number
    if (selectedCompany && trimmed !== selectedCompany.name && trimmed !== selectedCompany.org_number) {
      setSelectedCompany(null)
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      setSearchError(null)

      try {
        const response = await axios.get<BrregCompany[]>(
          `${API_BASE_URL}/api/farms/search`,
          { params: { q: trimmed } }
        )
        setSearchResults(response.data)

        // If exact 9 digits and returned single result, auto-select
        if (/^\d{9}$/.test(trimmed) && response.data.length === 1) {
          setSelectedCompany(response.data[0])
        }
      } catch (err: unknown) {
        console.error('Brreg search error:', err)
        setSearchError('Klarte ikke søke i Brønnøysund. Sjekk nettilkoblingen.')
      } finally {
        setIsSearching(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery])

  const handleSelectCompany = (company: BrregCompany) => {
    setSelectedCompany(company)
    setSearchResults([])
    setSearchQuery(company.name)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    if (!selectedCompany) {
      setError('Vennligst søk opp og velg et foretak fra Brønnøysundregisteret')
      setLoading(false)
      return
    }

    try {
      const onboardingUserId = getOrCreateOnboardingUserId()

      await axios.post(
        `${API_BASE_URL}/api/farms`,
        {
          name: selectedCompany.name,
          org_number: selectedCompany.org_number,
          address: selectedCompany.address,
          municipality: selectedCompany.municipality,
        },
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
                Finn din gård
              </h1>
              <p className="text-stone-600 text-sm">
                Skriv inn firmanavn eller organisasjonsnummer for å hente opplysninger direkte fra Brønnøysundregisteret.
              </p>
            </div>

            {error && (
              <div className="bg-rose-50 border-l-4 border-rose-500 text-rose-800 p-4 text-sm rounded-r-lg mb-6">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="relative">
                <label htmlFor="searchQuery" className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-2">
                  Firmanavn eller organisasjonsnummer *
                </label>
                <div className="relative">
                  <input
                    type="text"
                    id="searchQuery"
                    name="searchQuery"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    required
                    className="w-full px-4 py-3 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-bonde-green text-sm bg-white"
                    placeholder="Eks. Grønn Gård eller 987654321"
                  />
                  {isSearching && (
                    <div className="absolute right-3 top-3.5 text-xs text-stone-400 animate-pulse">
                      Søker...
                    </div>
                  )}
                </div>

                {/* Dropdown with search results */}
                {searchResults.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-white border border-stone-200 rounded-lg shadow-lg max-h-60 overflow-y-auto divide-y divide-stone-100">
                    {searchResults.map((company) => (
                      <button
                        key={company.org_number}
                        type="button"
                        onClick={() => handleSelectCompany(company)}
                        className="w-full text-left p-3 hover:bg-bonde-oat/50 transition-colors flex flex-col"
                      >
                        <span className="font-semibold text-stone-900 text-sm">{company.name}</span>
                        <div className="flex items-center justify-between text-xs text-stone-500 mt-0.5">
                          <span>Org.nr: {company.org_number} • {company.organization_form || 'Foretak'}</span>
                          {company.city && <span>{company.city}</span>}
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {searchError && (
                  <p className="text-xs text-rose-600 mt-2">{searchError}</p>
                )}
              </div>

              {selectedCompany && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-sm text-emerald-900">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-emerald-950 text-base">{selectedCompany.name}</span>
                    <span className="text-xs bg-emerald-200/60 text-emerald-800 font-semibold px-2 py-0.5 rounded">
                      Verifisert i BRREG
                    </span>
                  </div>
                  <p className="text-emerald-800">
                    Org.nr: <strong>{selectedCompany.org_number}</strong> ({selectedCompany.organization_form || 'Foretak'})
                  </p>
                  {selectedCompany.address && (
                    <p className="text-emerald-700 text-xs mt-1">
                      Adresse: {selectedCompany.address}, {selectedCompany.postal_code} {selectedCompany.city}
                    </p>
                  )}
                  {selectedCompany.municipality && (
                    <p className="text-emerald-700 text-xs">Kommune: {selectedCompany.municipality}</p>
                  )}
                </div>
              )}

              <Button
                type="submit"
                disabled={loading || !selectedCompany}
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
