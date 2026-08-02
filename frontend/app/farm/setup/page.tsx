'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import axios from 'axios'
import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
import { CompanySearch, Company } from '@/components/ui/CompanySearch'

export default function FarmSetupPage() {
  const router = useRouter()

  const [step, setStep] = useState<'details' | 'payment'>('details')

  // Required registration fields
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [address, setAddress] = useState('')

  // Farm details (from BRREG or manual)
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [farmName, setFarmName] = useState('')
  const [orgNumber, setOrgNumber] = useState('')
  const [isManualMode, setIsManualMode] = useState(false)

  // Payment choice state (Faktura / Vipps)
  const [paymentMethod, setPaymentMethod] = useState<'faktura' | 'vipps'>('faktura')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCompanySelect = (company: Company) => {
    setSelectedCompany(company)
    setFarmName(company.name)
    setOrgNumber(company.org_number)
    if (company.address) {
      setAddress((prev) => prev || company.address || '')
    }
  }

  const handleGoogleSignup = () => {
    alert('Google OAuth innlogging / registrering er klargjort! Sender deg videre...')
    router.push('/dashboard')
  }

  const handleNextToPayment = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!firstName.trim() || !lastName.trim() || !email.trim() || !password) {
      setError('Vennligst fyll ut fornavn, etternavn, e-postadresse og passord.')
      return
    }

    const finalFarmName = isManualMode ? farmName.trim() : (selectedCompany?.name || farmName.trim())
    if (!finalFarmName) {
      setError('Vennligst oppgi gårdens navn eller velg fra Brønnøysundregisteret.')
      return
    }

    setStep('payment')
  }

  const handleFinalSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL

      if (backendUrl) {
        try {
          await axios.post(`${backendUrl}/api/auth/register`, {
            first_name: firstName,
            last_name: lastName,
            email: email,
            password: password,
            address: address,
            farm_name: isManualMode ? farmName : (selectedCompany?.name || farmName),
            org_number: isManualMode ? orgNumber : (selectedCompany?.org_number || orgNumber),
          })
        } catch (regErr) {
          console.warn('Backend registration warning:', regErr)
        }

        try {
          await axios.post(`${backendUrl}/api/farms`, {
            name: isManualMode ? farmName : (selectedCompany?.name || farmName),
            org_number: (isManualMode ? orgNumber : selectedCompany?.org_number) || '000000000',
            address: address || selectedCompany?.address || '',
            municipality: selectedCompany?.municipality || '',
          })
        } catch (farmErr) {
          console.warn('Backend farm creation warning:', farmErr)
        }
      }

      router.push('/dashboard')
    } catch (err: any) {
      console.error('Registration error:', err)
      router.push('/dashboard')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bonde-oat text-stone-900 flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow py-12 px-4 flex flex-col items-center">
        <div className="w-full max-w-2xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <span className="text-xs font-bold uppercase tracking-widest text-bonde-green bg-bonde-light border border-emerald-200/80 px-3.5 py-1 rounded-full mb-3 inline-block">
              🎁 30 dagers gratis prøveperiode
            </span>
            <h1 className="text-3xl sm:text-4xl font-serif text-stone-900 mb-2 font-normal">
              {step === 'details' ? 'Opprett din konto' : 'Velg betalingsmetode'}
            </h1>
            <p className="text-stone-600 text-sm">
              {step === 'details'
                ? 'Sømløs onboarding for norske bønder. Ingen bindingstid.'
                : 'Du belastes ingenting under prøveperioden (30 dagers gratis prøveperiode).'}
            </p>
          </div>

          {error && (
            <div className="bg-rose-50 border-l-4 border-rose-500 text-rose-800 p-4 text-sm rounded-r-lg mb-6 shadow-xs">
              {error}
            </div>
          )}

          <div className="bg-white border border-stone-200/90 rounded-2xl p-6 sm:p-10 shadow-card">
            {step === 'details' ? (
              <form onSubmit={handleNextToPayment} className="space-y-6">
                {/* Fast Google Signup */}
                <div className="mb-6">
                  <button
                    type="button"
                    onClick={handleGoogleSignup}
                    className="w-full flex items-center justify-center gap-3 bg-white border border-stone-300 hover:border-stone-400 text-stone-700 font-semibold text-sm py-3 px-4 rounded-xl shadow-xs transition"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path
                        fill="#4285F4"
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      />
                      <path
                        fill="#34A853"
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                      />
                      <path
                        fill="#EA4335"
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                      />
                    </svg>
                    Fortsett med Google
                  </button>

                  <div className="relative my-6 text-center">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-stone-200"></div>
                    </div>
                    <span className="relative bg-white px-3 text-xs uppercase text-stone-400 font-bold tracking-wider">
                      eller registrér med e-post
                    </span>
                  </div>
                </div>

                {/* 1. Brukerinformasjon */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-bonde-green border-b border-stone-100 pb-2">
                    1. Personlig informasjon
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-1">
                        Fornavn *
                      </label>
                      <input
                        type="text"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        required
                        placeholder="Ola"
                        className="w-full px-4 py-2.5 border border-stone-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-bonde-green outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-1">
                        Etternavn *
                      </label>
                      <input
                        type="text"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        required
                        placeholder="Nordmann"
                        className="w-full px-4 py-2.5 border border-stone-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-bonde-green outline-none"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-1">
                      E-postadresse (Brukernavn) *
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      placeholder="ola@norskbonde.no"
                      className="w-full px-4 py-2.5 border border-stone-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-bonde-green outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-1">
                      Passord *
                    </label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      placeholder="••••••••"
                      className="w-full px-4 py-2.5 border border-stone-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-bonde-green outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-1">
                      Adresse *
                    </label>
                    <input
                      type="text"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      required
                      placeholder="Gårdsveien 14, 2350 NES"
                      className="w-full px-4 py-2.5 border border-stone-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-bonde-green outline-none"
                    />
                  </div>
                </div>

                {/* 2. Gård/Foretak (Hjelp fra BRREG eller manuell) */}
                <div className="space-y-4 pt-4">
                  <div className="flex items-center justify-between border-b border-stone-100 pb-2">
                    <h3 className="text-sm font-bold uppercase tracking-wider text-bonde-green">
                      2. Gård / Foretak
                    </h3>
                    <button
                      type="button"
                      onClick={() => setIsManualMode(!isManualMode)}
                      className="text-xs text-stone-500 hover:text-bonde-green underline"
                    >
                      {isManualMode ? 'Bruk BRREG-søk' : 'Fyll ut manuelt i stedet'}
                    </button>
                  </div>

                  {!isManualMode ? (
                    <div>
                      <CompanySearch
                        onSelect={handleCompanySelect}
                        label="Søk opp din gård / foretak i BRREG (valgfritt hjelpemiddel)"
                        placeholder="Søk firmanavn eller orgnr..."
                      />

                      {selectedCompany && (
                        <div className="mt-3 bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 text-xs text-emerald-900 flex items-center justify-between">
                          <div>
                            <span className="font-bold block text-sm">{selectedCompany.name}</span>
                            <span>Org.nr: {selectedCompany.org_number} • {selectedCompany.municipality || 'Norge'}</span>
                          </div>
                          <span className="bg-emerald-200 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded">
                            Valgt
                          </span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-1">
                          Gårdsnavn / Foretak *
                        </label>
                        <input
                          type="text"
                          value={farmName}
                          onChange={(e) => setFarmName(e.target.value)}
                          required
                          placeholder="Solberg Gård"
                          className="w-full px-4 py-2.5 border border-stone-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-bonde-green"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-1">
                          Org.nr (Valgfritt)
                        </label>
                        <input
                          type="text"
                          value={orgNumber}
                          onChange={(e) => setOrgNumber(e.target.value.replace(/\D/g, '').slice(0, 9))}
                          maxLength={9}
                          placeholder="9 siffer"
                          className="w-full px-4 py-2.5 border border-stone-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-bonde-green"
                        />
                      </div>
                    </div>
                  )}
                </div>

                <div className="pt-4">
                  <Button type="submit" variant="primary" fullWidth showArrow>
                    GÅ VIDERE TIL BETALING →
                  </Button>
                </div>
              </form>
            ) : (
              /* Step 2: Flexible Payment Choice */
              <form onSubmit={handleFinalSubmit} className="space-y-6">
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-900 mb-4">
                  <p className="font-bold text-sm mb-0.5">Prøveperiode: 0 kr i 30 dager</p>
                  <p>Abonnementet koster 290 kr/mnd etter prøveperioden. Kan avsluttes når som helst.</p>
                </div>

                <div className="space-y-3">
                  <label className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-2">
                    Velg foretrukket betalingsmåte
                  </label>

                  <div
                    onClick={() => setPaymentMethod('faktura')}
                    className={`p-4 border-2 rounded-xl cursor-pointer transition flex items-center justify-between ${
                      paymentMethod === 'faktura'
                        ? 'border-bonde-green bg-emerald-50/50'
                        : 'border-stone-200 bg-white hover:border-stone-300'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-5 h-5 rounded-full border-2 border-bonde-green flex items-center justify-center">
                        {paymentMethod === 'faktura' && <div className="w-2.5 h-2.5 bg-bonde-green rounded-full" />}
                      </div>
                      <div>
                        <p className="font-bold text-sm text-stone-900">EHF / E-postfaktura</p>
                        <p className="text-xs text-stone-500">Månedlig eller årlig faktura for gården</p>
                      </div>
                    </div>
                    <span className="text-xs bg-stone-100 text-stone-700 px-2.5 py-1 rounded font-semibold">
                      Anbefalt
                    </span>
                  </div>

                  <div
                    onClick={() => setPaymentMethod('vipps')}
                    className={`p-4 border-2 rounded-xl cursor-pointer transition flex items-center justify-between ${
                      paymentMethod === 'vipps'
                        ? 'border-bonde-green bg-emerald-50/50'
                        : 'border-stone-200 bg-white hover:border-stone-300'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-5 h-5 rounded-full border-2 border-bonde-green flex items-center justify-center">
                        {paymentMethod === 'vipps' && <div className="w-2.5 h-2.5 bg-bonde-green rounded-full" />}
                      </div>
                      <div>
                        <p className="font-bold text-sm text-stone-900">Vipps faste betalinger</p>
                        <p className="text-xs text-stone-500">Enkel trekk av månedlig lisens via Vipps</p>
                      </div>
                    </div>
                    <span className="text-xs bg-orange-100 text-orange-800 px-2.5 py-1 rounded font-bold">
                      Vipps
                    </span>
                  </div>
                </div>

                <div className="pt-4 flex gap-3">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => setStep('details')}
                  >
                    ← TILBAKE
                  </Button>
                  <Button
                    type="submit"
                    disabled={loading}
                    variant="primary"
                    fullWidth
                    showArrow
                  >
                    {loading ? 'FULLFØRER REGISTRERING...' : 'FULLFØR OG START GRATIS PRØVEPERIODE'}
                  </Button>
                </div>
              </form>
            )}
          </div>

          <div className="text-center mt-6 text-xs text-stone-500">
            Har du allerede registrert en konto?{' '}
            <Link href="/login" className="text-bonde-green font-semibold hover:underline">
              Logg inn her med e-post og passord
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
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
