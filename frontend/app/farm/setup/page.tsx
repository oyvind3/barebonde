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
  address: string
  is_active?: boolean
  registered_mva?: string
  industry_code?: string
  registered_date?: string
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
    <div className="min-h-screen bg-[#0d0f12] text-stone-100 flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow py-12 px-4 flex flex-col items-center">
        <div className="w-full max-w-2xl mx-auto">
          {/* Header section matching orgn.no style */}
          <div className="text-center mb-8">
            <span className="text-xs font-bold uppercase tracking-widest text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-3.5 py-1 rounded-full mb-4 inline-block shadow-xs">
              🎁 Prøv gratis i 30 dager
            </span>
            <h1 className="text-3xl sm:text-5xl font-serif text-white mb-3 font-normal tracking-tight">
              Finn organisasjonsnummer — Bedriftsoppslag
            </h1>
            <p className="text-stone-400 text-sm sm:text-base font-sans">
              Søk raskt på norske virksomheter. Skriv inn firmanavn eller organisasjonsnummer.
            </p>
          </div>

          {error && (
            <div className="bg-rose-950/80 border-l-4 border-rose-500 text-rose-200 p-4 text-sm rounded-r-lg mb-6 shadow-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="relative">
              {/* Search input box with focus glow like orgn.no */}
              <div className="relative">
                <input
                  type="text"
                  id="searchQuery"
                  name="searchQuery"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  required
                  autoComplete="off"
                  className="w-full px-5 py-4 border-2 border-stone-700 focus:border-blue-500 rounded-xl outline-none text-base sm:text-lg bg-[#14181f] text-white placeholder-stone-500 shadow-xl transition-all"
                  placeholder="Søk orgnr (9 siffer) eller navn..."
                />
                {isSearching && (
                  <div className="absolute right-4 top-4 text-xs text-blue-400 animate-pulse font-medium">
                    Søker i BRREG...
                  </div>
                )}
              </div>

              {/* Instant Dropdown results styled after orgn.no */}
              {searchResults.length > 0 && (
                <div className="absolute z-20 w-full mt-2 bg-[#1b202a] border border-stone-700/80 rounded-xl shadow-2xl overflow-hidden divide-y divide-stone-800/80">
                  {searchResults.map((company) => (
                    <button
                      key={company.org_number}
                      type="button"
                      onClick={() => handleSelectCompany(company)}
                      className="w-full text-left p-4 hover:bg-stone-800/70 transition-colors flex items-center justify-between group"
                    >
                      <div className="flex flex-col">
                        <span className="font-bold text-white text-base group-hover:text-blue-400 transition-colors">
                          {company.name}
                        </span>
                        <span className="text-xs text-stone-400 mt-1 flex items-center gap-2">
                          <span className="font-mono text-stone-300">{company.org_number}</span>
                          <span>•</span>
                          <span>{company.municipality || company.city || 'Norge'}</span>
                          <span>•</span>
                          <span className="text-stone-400">{company.organization_form || 'Foretak'}</span>
                        </span>
                      </div>
                      <div className="text-stone-500 group-hover:text-stone-300 text-xs px-2 py-1 rounded bg-stone-800/50">
                        Velg ➔
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {searchError && (
                <p className="text-xs text-rose-400 mt-2">{searchError}</p>
              )}
            </div>

            {/* Selected Company Details Card matching 3rd screenshot */}
            {selectedCompany ? (
              <div className="bg-[#14181f] border border-stone-700/80 rounded-2xl p-6 sm:p-8 shadow-xl text-stone-200 animate-fadeIn">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-stone-800 pb-5 mb-6">
                  <div>
                    <h2 className="text-2xl sm:text-3xl font-bold font-serif text-white tracking-wide">
                      {selectedCompany.name}
                    </h2>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-stone-400 font-mono text-sm tracking-wider">
                        {selectedCompany.org_number.replace(/(\d{3})(\d{3})(\d{3})/, '$1 $2 $3')}
                      </span>
                      <span className="bg-emerald-500/20 text-emerald-400 text-xs font-semibold px-2.5 py-0.5 rounded-full border border-emerald-500/30">
                        Aktiv
                      </span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm">
                  <div>
                    <span className="text-xs text-stone-400 uppercase tracking-wider block mb-1">
                      Adresse
                    </span>
                    <p className="font-medium text-stone-200">
                      {selectedCompany.address ? `${selectedCompany.address}, ` : ''}
                      {selectedCompany.postal_code} {selectedCompany.city || ''}
                    </p>
                  </div>

                  <div>
                    <span className="text-xs text-stone-400 uppercase tracking-wider block mb-1">
                      Kommune
                    </span>
                    <p className="font-medium text-stone-200 uppercase">
                      {selectedCompany.municipality || 'Ikke oppgitt'}
                    </p>
                  </div>

                  <div>
                    <span className="text-xs text-stone-400 uppercase tracking-wider block mb-1">
                      Organisasjonsform
                    </span>
                    <p className="font-medium text-stone-200">
                      {selectedCompany.organization_form || 'Foretak'}
                    </p>
                  </div>

                  <div>
                    <span className="text-xs text-stone-400 uppercase tracking-wider block mb-1">
                      Registrert i BRREG
                    </span>
                    <p className="font-medium text-stone-200">
                      {selectedCompany.registered_date || 'Ja'}
                    </p>
                  </div>

                  <div>
                    <span className="text-xs text-stone-400 uppercase tracking-wider block mb-1">
                      Registrert i MVA-registeret
                    </span>
                    <p className="font-medium text-stone-200">
                      {selectedCompany.registered_mva || 'Nei'}
                    </p>
                  </div>

                  {selectedCompany.industry_code && (
                    <div className="sm:col-span-2">
                      <span className="text-xs text-stone-400 uppercase tracking-wider block mb-1">
                        Næringskode
                      </span>
                      <p className="font-medium text-stone-200">
                        {selectedCompany.industry_code}
                      </p>
                    </div>
                  )}
                </div>

                <div className="mt-8 pt-6 border-t border-stone-800/80 flex flex-col sm:flex-row items-center gap-4">
                  <Button
                    type="submit"
                    disabled={loading}
                    variant="primary"
                    fullWidth
                    showArrow
                  >
                    {loading ? 'OPPRETTER GÅRD...' : 'START 30 DAGERS GRATIS PRØVEPERIODE'}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="bg-[#14181f] border border-dashed border-stone-800 rounded-xl p-6 text-center text-stone-400 text-sm">
                Søk etter gård eller bedrift for å se detaljer og starte din 30 dagers gratis prøveperiode.
              </div>
            )}
          </form>

          <div className="mt-12 text-center text-xs text-stone-500">
            Har du allerede registrert gården din?{' '}
            <Link href="/login" className="text-blue-400 font-semibold hover:underline">
              Logg inn her med brukernavn/e-post
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
