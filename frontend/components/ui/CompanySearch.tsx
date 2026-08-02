'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

export interface Company {
  org_number: string
  name: string
  organization_form?: string
  postal_code?: string
  city?: string
  municipality?: string
  address?: string
  registered_mva?: string
  industry_code?: string
}

interface CompanySearchProps {
  onSelect: (company: Company) => void
  placeholder?: string
  label?: string
}

export function CompanySearch({
  onSelect,
  placeholder = 'Søk orgnr (9 siffer) eller bedriftsnavn...',
  label = 'Søk i Brønnøysundregisteret',
}: CompanySearchProps) {
  const [query, setQuery] = useState('')
  const [results, setSearchResults] = useState<Company[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [hasSelected, setHasSelected] = useState(false)

  useEffect(() => {
    const trimmed = query.trim()

    // Don't search if user just selected a company and hasn't edited text
    if (hasSelected || !trimmed || trimmed.length < 2) {
      setSearchResults([])
      setIsSearching(false)
      return
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      setSearchError(null)

      try {
        let companies: Company[] = []

        // Try backend first if available
        const backendUrl = process.env.NEXT_PUBLIC_API_URL
        if (backendUrl) {
          try {
            const res = await axios.get<Company[]>(`${backendUrl}/api/farms/search`, {
              params: { q: trimmed },
              timeout: 2500,
            })
            companies = res.data
          } catch {
            // ignore and fallback to BRREG directly
          }
        }

        // Direct BRREG API fallback
        if (!companies.length) {
          const digitsOnly = trimmed.replace(/\s/g, '')
          if (/^\d{9}$/.test(digitsOnly)) {
            const res = await axios.get(`https://data.brreg.no/enhetsregisteret/api/enheter/${digitsOnly}`)
            if (res.data) {
              const item = res.data
              const addressObj = item.forretningsadresse || item.postadresse || {}
              companies = [{
                org_number: item.organisasjonsnummer || digitsOnly,
                name: item.navn || '',
                organization_form: item.organisasjonsform?.beskrivelse || '',
                postal_code: addressObj.postnummer || '',
                city: addressObj.poststed || '',
                municipality: addressObj.kommune || '',
                address: (addressObj.adresse || []).join(', '),
                registered_mva: item.registrertIMvaregisteret ? 'Ja' : 'Nei',
                industry_code: item.naeringskode1?.beskrivelse || '',
              }]
            }
          } else {
            const res = await axios.get('https://data.brreg.no/enhetsregisteret/api/enheter', {
              params: {
                navn: trimmed,
                navnMetodeForSoek: 'FORTLOEPENDE',
                size: 10,
              }
            })
            const rawItems = res.data?._embedded?.enheter || []
            companies = rawItems.map((item: any) => {
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
              }
            })
          }
        }

        setSearchResults(companies)
      } catch {
        setSearchError('Klarte ikke hente fra Brønnøysund akkurat nå.')
      } finally {
        setIsSearching(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [query, hasSelected])

  const handleSelect = (company: Company) => {
    setHasSelected(true)
    setQuery(company.name)
    setSearchResults([])
    onSelect(company)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
    setHasSelected(false)
  }

  return (
    <div className="relative w-full">
      {label && (
        <label className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-2">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={handleInputChange}
          className="w-full px-4 py-3 border-2 border-stone-300 focus:border-bonde-green rounded-xl outline-none text-sm bg-white text-stone-900 placeholder-stone-400 shadow-xs transition-all"
          placeholder={placeholder}
          autoComplete="off"
        />
        {isSearching && (
          <div className="absolute right-3.5 top-3.5 text-xs text-bonde-green animate-pulse font-medium">
            Søker...
          </div>
        )}
      </div>

      {results.length > 0 && !hasSelected && (
        <div className="absolute z-30 w-full mt-1.5 bg-white border border-stone-200 rounded-xl shadow-xl overflow-hidden divide-y divide-stone-100 max-h-60 overflow-y-auto">
          {results.map((company) => (
            <button
              key={company.org_number}
              type="button"
              onClick={() => handleSelect(company)}
              className="w-full text-left p-3 hover:bg-bonde-oat/70 transition-colors flex items-center justify-between group"
            >
              <div className="flex flex-col">
                <span className="font-semibold text-stone-900 text-sm group-hover:text-bonde-green">
                  {company.name}
                </span>
                <span className="text-xs text-stone-500 mt-0.5 flex items-center gap-2">
                  <span className="font-mono text-stone-600">{company.org_number}</span>
                  <span>•</span>
                  <span>{company.municipality || company.city || 'Norge'}</span>
                  {company.organization_form && (
                    <>
                      <span>•</span>
                      <span>{company.organization_form}</span>
                    </>
                  )}
                </span>
              </div>
              <span className="text-xs text-stone-400 group-hover:text-bonde-green font-medium">
                Velg ➔
              </span>
            </button>
          ))}
        </div>
      )}

      {searchError && <p className="text-xs text-amber-700 mt-1.5">{searchError}</p>}
    </div>
  )
}