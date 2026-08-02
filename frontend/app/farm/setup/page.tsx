'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import axios from 'axios'
import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://data.brreg.no/enhetsregisteret/api/enheter'

export default function FarmSetupPage() {
  const router = useRouter()

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCompany, setSelectedCompany] = useState<BrregCompany | null>(null)
  const [searchResults, setSearchResults] = useState<BrregCompany[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  // Manual fallback state
  const [isManualMode, setIsManualMode] = useState(false)
  const [manualForm, setManualForm] = useState({
    name: '',
    org_number: '',
    address: '',
    municipality: '',
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Debounce search query to BRREG API or backend
  useEffect(() => {
    const trimmed = searchQuery.trim()
    if (!trimmed || trimmed.length < 2) {
      setSearchResults([])
      setIsSearching(false)
      return
    }

    if (selectedCompany && trimmed !== selectedCompany.name && trimmed !== selectedCompany.org_number) {
      setSelectedCompany(null)
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      setSearchError(null)

      try {
        let results: BrregCompany[] = []
        // First try backend API, or fallback to BRREG open API directly
        const backendUrl = process.env.NEXT_PUBLIC_API_URL
        if (backendUrl) {
          try {
            const response = await axios.get<BrregCompany[]>(`${backendUrl}/api/farms/search`, {
              params: { q: trimmed },
              timeout: 3000,
            })
            results = response.data
          } catch (backendErr) {
            console.warn('Backend search unavailable, falling back to direct BRREG API call', backendErr)
          }
        }

        // Direct BRREG API fallback
        if (!results.length) {
          const digitsOnly = trimmed.replace(/\s/g, '')
          if (/^\d{9}$/.test(digitsOnly)) {
            const directRes = await axios.get(`https://data.brreg.no/enhetsregisteret/api/enheter/${digitsOnly}`)
            if (directRes.data) {
              const item = directRes.data
              const addressObj = item.forretningsadresse || item.postadresse || {}
              results = [{
                org_number: item.organisasjonsnummer || digitsOnly,
                name: item.navn || '',
                organization_form: item.organisasjonsform?.beskrivelse || '',
                postal_code: addressObj.postnummer || '',
                city: addressObj.poststed || '',
                municipality: addressObj.kommune || '',
                address: (addressObj.adresse || []).join(', '),
                registered_mva: item.registrertIMvaregisteret ? 'Ja' : 'Nei',
                industry_code: item.naeringskode1?.beskrivelse || '',
                registered_date: item.registreringsdatoEnhetsregisteret || '',
              }]
            }
          } else {
            const searchRes = await axios.get('https://data.brreg.no/enhetsregisteret/api/enheter', {
              params: {
                navn: trimmed,
                navnMetodeForSoek: 'FORTLOEPENDE',
                size: 10,
              }
            })
            const rawItems = searchRes.data?._embedded?.enheter || []
            results = rawItems.map((item: any) => {
              const addressObj = item.forretningsadresse || item.postadresse || {}
              return {
                org_number: item.organisasjonsnummer || '',
                name: item.navn || '',
                organization_form: item.organisasjonsform?.beskrivelse || '',
                postal_code: addressObj.postnummer || '',
                city: addressObj.poststed || '',
                municipality: addressObj.kommune || '',
                address: (addressObj.adresse || []).join(', '),
                registered_mva: item.registrertIMvaregisteret ? 'Ja' : 'Nei',
                industry_code: item.naeringskode1?.beskrivelse || '',
                registered_date: item.registreringsdatoEnhetsregisteret || '',
              }
            })
          }
        }

        setSearchResults(results)

        if (/^\d{9}$/.test(trimmed.replace(/\s/g, '')) && results.length === 1) {
          setSelectedCompany(results[0])
        }
      } catch (err: unknown) {
        console.error('Brreg search error:', err)
        setSearchError('Klarte ikke hente fra Brønnøysund akkurat nå.')
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

    const farmName = isManualMode ? manualForm.name.trim() : selectedCompany?.name
    const farmOrgNr = isManualMode ? manualForm.org_number.trim() : selectedCompany?.org_number
    const farmAddr = isManualMode ? manualForm.address.trim() : selectedCompany?.address
    const farmMuni = isManualMode ? manualForm.municipality.trim() : selectedCompany?.municipality

    if (!farmName) {
      setError('Vennligst oppgi gårdsnavn/virksomhetsnavn.')
      setLoading(false)
      return
    }

    try {
      const onboardingUserId = getOrCreateOnboardingUserId()

      const backendUrl = process.env.NEXT_PUBLIC_API_URL
      if (backendUrl) {
        await axios.post(
          `${backendUrl}/api/farms`,
          {
            name: farmName,
            org_number: farmOrgNr || '000000000',
            address: farmAddr || '',
            municipality: farmMuni || '',
          },
          {
            headers: {
              'x-onboarding-user-id': onboardingUserId,
            },
          }
        )
      }

      router.push('/dashboard')
    } catch (err: any) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setError('Denne gården er allerede registrert i systemet')
      } else if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        // Even if backend fails in static demo, proceed to dashboard
        router.push('/dashboard')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bonde-oat text-stone-900 flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow py-12 px-4 flex flex-col items-center">
        <div className="w-full max-w-xl mx-auto">
          {/* Header section matching Barebonde styling */}
          <div className="text-center mb-8">
            <span className="text-xs font-bold uppercase tracking-widest text-bonde-green bg-bonde-light border border-emerald-200/80 px-3.5 py-1 rounded-full mb-3 inline-block">
              🎁 Prøv gratis i 30 dager
            </span>
            <h1 className="text-3xl sm:text-4xl font-serif text-stone-900 mb-2 font-normal">
              Finn organisasjonsnummer — Bedriftsoppslag
            </h1>
            <p className="text-stone-600 text-sm">
              Søk raskt på norske virksomheter. Skriv inn firmanavn eller organisasjonsnummer for å hente opplysninger direkte fra Brønnøysund.
            </p>
          </div>

          {error && (
            <div className="bg-rose-50 border-l-4 border-rose-500 text-rose-800 p-4 text-sm rounded-r-lg mb-6 shadow-xs">
              {error}
            </div>
          )}

          <div className="bg-white border border-stone-200/90 rounded-2xl p-6 sm:p-8 shadow-card mb-6">
            {!isManualMode ? (
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="relative">
                  <label htmlFor="searchQuery" className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-2">
                    Søk orgnr (9 siffer) eller navn *
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      id="searchQuery"
                      name="searchQuery"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      required={!selectedCompany}
                      autoComplete="off"
                      className="w-full px-4 py-3.5 border-2 border-stone-300 focus:border-bonde-green rounded-xl outline-none text-base bg-white text-stone-900 placeholder-stone-400 shadow-xs transition-all"
                      placeholder="Eks. Grønn Gård eller 987654321"
                    />
                    {isSearching && (
                      <div className="absolute right-4 top-4 text-xs text-bonde-green animate-pulse font-medium">
                        Søker...
                      </div>
                    )}
                  </div>

                  {/* Dropdown search results */}
                  {searchResults.length > 0 && (
                    <div className="absolute z-20 w-full mt-2 bg-white border border-stone-200 rounded-xl shadow-xl overflow-hidden divide-y divide-stone-100">
                      {searchResults.map((company) => (
                        <button
                          key={company.org_number}
                          type="button"
                          onClick={() => handleSelectCompany(company)}
                          className="w-full text-left p-3.5 hover:bg-bonde-oat/60 transition-colors flex items-center justify-between group"
                        >
                          <div className="flex flex-col">
                            <span className="font-semibold text-stone-900 text-sm group-hover:text-bonde-green transition-colors">
                              {company.name}
                            </span>
                            <span className="text-xs text-stone-500 mt-0.5 flex items-center gap-2">
                              <span className="font-mono text-stone-600">{company.org_number}</span>
                              <span>•</span>
                              <span>{company.municipality || company.city || 'Norge'}</span>
                              <span>•</span>
                              <span>{company.organization_form || 'Foretak'}</span>
                            </span>
                          </div>
                          <div className="text-stone-400 group-hover:text-bonde-green text-xs px-2 py-1 rounded bg-stone-100">
                            Velg ➔
                          </div>
                        </button>
                      ))}
                    </div>
                  )}

                  {searchError && (
                    <p className="text-xs text-amber-700 mt-2">{searchError}</p>
                  )}
                </div>

                {/* Selected company details */}
                {selectedCompany ? (
                  <div className="bg-emerald-50/70 border border-emerald-200/80 rounded-xl p-5 text-stone-800 text-sm animate-fadeIn">
                    <div className="flex items-center justify-between border-b border-emerald-200/60 pb-3 mb-4">
                      <div>
                        <h2 className="text-xl font-bold font-serif text-stone-900">
                          {selectedCompany.name}
                        </h2>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-stone-600 font-mono text-xs">
                            Org.nr: {selectedCompany.org_number.replace(/(\d{3})(\d{3})(\d{3})/, '$1 $2 $3')}
                          </span>
                          <span className="bg-emerald-200/60 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded-full">
                            Verifisert i BRREG
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                      <div>
                        <span className="text-stone-500 uppercase tracking-wider block font-bold mb-0.5">
                          Adresse
                        </span>
                        <p className="text-stone-800">
                          {selectedCompany.address ? `${selectedCompany.address}, ` : ''}
                          {selectedCompany.postal_code} {selectedCompany.city || ''}
                        </p>
                      </div>

                      <div>
                        <span className="text-stone-500 uppercase tracking-wider block font-bold mb-0.5">
                          Kommune
                        </span>
                        <p className="text-stone-800 uppercase">
                          {selectedCompany.municipality || 'Ikke oppgitt'}
                        </p>
                      </div>

                      <div>
                        <span className="text-stone-500 uppercase tracking-wider block font-bold mb-0.5">
                          Organisasjonsform
                        </span>
                        <p className="text-stone-800">
                          {selectedCompany.organization_form || 'Foretak'}
                        </p>
                      </div>

                      <div>
                        <span className="text-stone-500 uppercase tracking-wider block font-bold mb-0.5">
                          MVA-registrert
                        </span>
                        <p className="text-stone-800">
                          {selectedCompany.registered_mva || 'Nei'}
                        </p>
                      </div>
                    </div>

                    <div className="mt-6 pt-4 border-t border-emerald-200/60">
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
                  <div className="bg-stone-50 border border-dashed border-stone-200 rounded-xl p-5 text-center text-stone-500 text-xs">
                    Søk etter din gård eller bedrift ovenfor for å hente opplysninger automatisk.
                  </div>
                )}
              </form>
            ) : (
              /* Manual Fill Form Option */
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-stone-200 mb-2">
                  <h2 className="text-lg font-bold font-serif text-stone-900">Fyll ut gårdsopplysninger manuelt</h2>
                  <button
                    type="button"
                    onClick={() => setIsManualMode(false)}
                    className="text-xs text-bonde-green hover:underline font-semibold"
                  >
                    ← Tilbake til BRREG-søk
                  </button>
                </div>

                <div>
                  <label htmlFor="manualName" className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-1">
                    Gårdsnavn / Foretaksnavn *
                  </label>
                  <input
                    type="text"
                    id="manualName"
                    value={manualForm.name}
                    onChange={(e) => setManualForm({ ...manualForm, name: e.target.value })}
                    required
                    placeholder="Eks. Solberg Gård"
                    className="w-full px-4 py-2.5 border border-stone-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-bonde-green"
                  />
                </div>

                <div>
                  <label htmlFor="manualOrg" className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-1">
                    Organisasjonsnummer (valgfritt)
                  </label>
                  <input
                    type="text"
                    id="manualOrg"
                    value={manualForm.org_number}
                    onChange={(e) => setManualForm({ ...manualForm, org_number: e.target.value.replace(/\D/g, '').slice(0, 9) })}
                    maxLength={9}
                    placeholder="9 siffer"
                    className="w-full px-4 py-2.5 border border-stone-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-bonde-green"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="manualAddress" className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-1">
                      Adresse (valgfritt)
                    </label>
                    <input
                      type="text"
                      id="manualAddress"
                      value={manualForm.address}
                      onChange={(e) => setManualForm({ ...manualForm, address: e.target.value })}
                      placeholder="Gårdsveien 12"
                      className="w-full px-4 py-2.5 border border-stone-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-bonde-green"
                    />
                  </div>

                  <div>
                    <label htmlFor="manualMunicipality" className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-1">
                      Kommune (valgfritt)
                    </label>
                    <input
                      type="text"
                      id="manualMunicipality"
                      value={manualForm.municipality}
                      onChange={(e) => setManualForm({ ...manualForm, municipality: e.target.value })}
                      placeholder="Ringsaker"
                      className="w-full px-4 py-2.5 border border-stone-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-bonde-green"
                    />
                  </div>
                </div>

                <div className="pt-4">
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
              </form>
            )}

            {/* Toggle manual mode button */}
            {!isManualMode && (
              <div className="mt-6 pt-4 border-t border-stone-100 text-center">
                <button
                  type="button"
                  onClick={() => setIsManualMode(true)}
                  className="text-xs text-stone-600 hover:text-bonde-green font-medium underline transition"
                >
                  Finner du ikke gården i Brønnøysund? Klikk her for å fylle ut manuelt ✍️
                </button>
              </div>
            )}
          </div>

          <div className="text-center text-xs text-stone-500">
            Har du allerede registrert gården din?{' '}
            <Link href="/login" className="text-bonde-green font-semibold hover:underline">
              Logg inn her med brukernavn/e-post
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
