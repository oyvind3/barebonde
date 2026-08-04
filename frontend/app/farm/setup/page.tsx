'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
import { Company, CompanySearch } from '@/components/ui/CompanySearch'
import { apiFetch, bootstrapIdentity } from '@/lib/api'

type SetupStep = 'business' | 'operations' | 'account' | 'verifyEmail' | 'payment' | 'confirmation'

const setupSteps: Array<{ id: Exclude<SetupStep, 'confirmation'>; label: string }> = [
  { id: 'business', label: 'Foretak' },
  { id: 'operations', label: 'Drift' },
  { id: 'account', label: 'Deg' },
  { id: 'payment', label: 'Betaling' },
]

const primaryFarmOptions = [
  { value: 'plante', label: 'Planteproduksjon', description: 'Korn, gras, frukt eller grønt' },
  { value: 'husdyr', label: 'Husdyr', description: 'Melk, kjøtt, egg eller andre dyr' },
  { value: 'skog', label: 'Skogbruk', description: 'Skog og utmark er hoveddriften' },
  { value: 'blandet', label: 'Blandet drift', description: 'Flere viktige driftsgrener' },
  { value: 'annet', label: 'Annet', description: 'En annen type landbruksvirksomhet' },
] as const

const productionOptions = [
  { value: 'korn', label: 'Korn' },
  { value: 'grovfor', label: 'Grovfôr' },
  { value: 'melk', label: 'Melk' },
  { value: 'storfe', label: 'Storfe' },
  { value: 'sau_geit', label: 'Sau og geit' },
  { value: 'svin', label: 'Svin' },
  { value: 'fjorkre_egg', label: 'Fjørfe og egg' },
  { value: 'frukt_baer', label: 'Frukt og bær' },
  { value: 'gronnsaker_potet', label: 'Grønnsaker og potet' },
  { value: 'skogbruk', label: 'Skogbruk' },
  { value: 'annen_produksjon', label: 'Annen produksjon' },
] as const

const goalOptions = [
  { value: 'regnskap', label: 'Regnskap' },
  { value: 'bilag', label: 'Bilag og OCR' },
  { value: 'dokumenter', label: 'Dokumenter og avtaler' },
  { value: 'frister', label: 'Frister' },
  { value: 'maskiner', label: 'Maskiner og ressurser' },
  { value: 'areal', label: 'Eiendom og areal' },
  { value: 'driftsplan', label: 'Drift og planlegging' },
  { value: 'integrasjoner', label: 'Integrasjoner' },
] as const

const inputClass = 'w-full rounded-xl border border-stone-300 bg-white px-4 py-3 text-sm text-stone-900 outline-none transition focus:border-bonde-green focus:ring-2 focus:ring-bonde-green/20'
const labelClass = 'mb-1.5 block text-xs font-bold uppercase tracking-wider text-stone-700'
const ONBOARDING_DRAFT_KEY = 'barebonde_onboarding_draft'

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]
}

export default function FarmSetupPage() {
  const router = useRouter()
  const [step, setStep] = useState<SetupStep>('business')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [resendLoading, setResendLoading] = useState(false)
  const [resendMessage, setResendMessage] = useState<string | null>(null)
  const [emailStatus, setEmailStatus] = useState<{ sent: boolean; message: string } | null>(null)
  const [emailVerified, setEmailVerified] = useState(false)

  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [isManualMode, setIsManualMode] = useState(false)
  const [farmName, setFarmName] = useState('')
  const [orgNumber, setOrgNumber] = useState('')
  const [farmAddress, setFarmAddress] = useState('')
  const [farmPostalCode, setFarmPostalCode] = useState('')
  const [farmCity, setFarmCity] = useState('')
  const [farmMunicipality, setFarmMunicipality] = useState('')
  const [farmIndustryCode, setFarmIndustryCode] = useState('')
  const [organizationForm, setOrganizationForm] = useState('')

  const [primaryFarmType, setPrimaryFarmType] = useState('')
  const [productionTypes, setProductionTypes] = useState<string[]>([])
  const [farmSizeRange, setFarmSizeRange] = useState('vet_ikke')
  const [teamSize, setTeamSize] = useState('1')
  const [onboardingGoals, setOnboardingGoals] = useState<string[]>([])

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [personalAddress, setPersonalAddress] = useState('')
  const [onboardingRole, setOnboardingRole] = useState('owner')

  const [paymentMethod, setPaymentMethod] = useState<'faktura' | 'vipps'>('faktura')
  const [billingEmail, setBillingEmail] = useState('')

  const activeStepIndex = step === 'verifyEmail' ? 2 : setupSteps.findIndex((item) => item.id === step)
  const isSetupStep = step !== 'confirmation'

  useEffect(() => {
    const restoreDraft = () => {
      const savedDraft = window.localStorage.getItem(ONBOARDING_DRAFT_KEY)
      if (!savedDraft) return
      try {
        const draft = JSON.parse(savedDraft)
        setFarmName(draft.farmName || '')
        setOrgNumber(draft.orgNumber || '')
        setFarmAddress(draft.farmAddress || '')
        setFarmPostalCode(draft.farmPostalCode || '')
        setFarmCity(draft.farmCity || '')
        setFarmMunicipality(draft.farmMunicipality || '')
        setFarmIndustryCode(draft.farmIndustryCode || '')
        setOrganizationForm(draft.organizationForm || '')
        setIsManualMode(Boolean(draft.isManualMode))
        setPrimaryFarmType(draft.primaryFarmType || '')
        setProductionTypes(Array.isArray(draft.productionTypes) ? draft.productionTypes : [])
        setFarmSizeRange(draft.farmSizeRange || 'vet_ikke')
        setTeamSize(draft.teamSize || '1')
        setOnboardingGoals(Array.isArray(draft.onboardingGoals) ? draft.onboardingGoals : [])
        setFirstName(draft.firstName || '')
        setLastName(draft.lastName || '')
        setEmail(draft.email || '')
        setPhoneNumber(draft.phoneNumber || '')
        setPersonalAddress(draft.personalAddress || '')
        setOnboardingRole(draft.onboardingRole || 'owner')
        setPaymentMethod(draft.paymentMethod || 'faktura')
        setBillingEmail(draft.billingEmail || '')
      } catch {
        window.localStorage.removeItem(ONBOARDING_DRAFT_KEY)
      }
    }

    const bootstrapOnboarding = async () => {
      restoreDraft()
      const token = new URLSearchParams(window.location.search).get('token')
      if (token) {
        try {
          const response = await apiFetch('/api/auth/magic-link/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token }),
          })
          const data = await response.json().catch(() => ({}))
          if (!response.ok) throw new Error(data.detail || 'Bekreftelseslenken kunne ikke brukes.')
          window.history.replaceState({}, '', '/farm/setup')
          setEmailVerified(true)
          setEmailStatus({ sent: true, message: 'E-postadressen er bekreftet.' })
          setStep('payment')
        } catch (verificationError) {
          setError(verificationError instanceof Error ? verificationError.message : 'Bekreftelseslenken kunne ikke brukes.')
          setStep('verifyEmail')
        }
      }

      try {
        const identity = await bootstrapIdentity()
        if (identity) {
          setFirstName((current) => current || identity.user.first_name)
          setLastName((current) => current || identity.user.last_name)
          setEmail((current) => current || identity.user.email)
        }
      } catch {
        // A visitor has no session until the e-mail link has been used.
      }
    }

    bootstrapOnboarding()
  }, [])

  const handleCompanySelect = (company: Company) => {
    setSelectedCompany(company)
    setFarmName(company.name)
    setOrgNumber(company.org_number)
    setOrganizationForm(company.organization_form || '')
    setFarmAddress(company.address || '')
    setFarmPostalCode(company.postal_code || '')
    setFarmCity(company.city || '')
    setFarmMunicipality(company.municipality || '')
    setFarmIndustryCode(company.industry_code || '')
    setError(null)
  }

  const goToOperations = () => {
    const hasCompany = Boolean(selectedCompany && !isManualMode)
    if (!hasCompany && !farmName.trim()) {
      setError('Velg foretak i Brønnøysundregistrene eller skriv inn gårdsnavnet.')
      return
    }
    setError(null)
    setStep('operations')
  }

  const goToAccount = () => {
    if (!primaryFarmType) {
      setError('Velg den viktigste driftsretningen, så kan vi tilpasse oppstarten.')
      return
    }
    if (!onboardingGoals.length) {
      setError('Velg minst ett område du vil ha hjelp med først.')
      return
    }
    setError(null)
    setStep('account')
  }

  const saveOnboardingDraft = () => {
    window.localStorage.setItem(ONBOARDING_DRAFT_KEY, JSON.stringify({
      farmName,
      orgNumber,
      farmAddress,
      farmPostalCode,
      farmCity,
      farmMunicipality,
      farmIndustryCode,
      organizationForm,
      isManualMode,
      primaryFarmType,
      productionTypes,
      farmSizeRange,
      teamSize,
      onboardingGoals,
      firstName,
      lastName,
      email,
      phoneNumber,
      personalAddress,
      onboardingRole,
      paymentMethod,
      billingEmail,
    }))
  }

  const requestEmailVerification = async () => {
    if (!firstName.trim() || !lastName.trim() || !email.trim() || !phoneNumber.trim()) {
      setError('Fyll ut navn, e-postadresse og telefonnummer før du går videre.')
      return
    }
    setLoading(true)
    setError(null)
    saveOnboardingDraft()
    try {
      const response = await apiFetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          email: email.trim(),
          phone_number: phoneNumber.trim(),
          address: personalAddress.trim() || undefined,
          onboarding_role: onboardingRole,
        }),
      })
      const registration = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(registration.detail || 'Kunne ikke lagre profilen.')
      if (!registration.email_sent) throw new Error(registration.email_message || 'Kunne ikke sende bekreftelses-e-post.')
      setEmailStatus({ sent: true, message: registration.email_message || 'Bekreftelses-e-post er sendt.' })
      setStep('verifyEmail')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Kunne ikke starte e-postbekreftelsen. Prøv igjen.')
    } finally {
      setLoading(false)
    }
  }

  const handleResendEmail = async () => {
    setResendLoading(true)
    setResendMessage(null)
    try {
      // Re-submit the pending registration rather than issuing a bare resend,
      // so a replacement one-time link retains the profile until verification.
      const response = await apiFetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          email: email.trim(),
          phone_number: phoneNumber.trim(),
          address: personalAddress.trim() || undefined,
          onboarding_role: onboardingRole,
        }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.email_sent) throw new Error(data.detail || data.email_message || 'Kunne ikke sende e-post på nytt. Prøv igjen senere.')
      setResendMessage(data.message || `Ny bekreftelseslenke er sendt til ${email}.`)
    } catch (requestError) {
      setResendMessage(requestError instanceof Error ? requestError.message : 'Kunne ikke sende bekreftelseslenken på nytt. Prøv igjen senere.')
    } finally {
      setResendLoading(false)
    }
  }

  const handleFinalSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError(null)

    const finalFarmName = selectedCompany?.name || farmName.trim()
    const finalOrgNumber = selectedCompany?.org_number || orgNumber.trim()

    try {
      if (!emailVerified) {
        throw new Error('Bekreft e-postadressen før du oppretter gården.')
      }
      const identity = await bootstrapIdentity()
      if (!identity) {
        throw new Error('Bekreft e-postadressen fra lenken før du oppretter gården.')
      }
      const farmResponse = await apiFetch('/api/farms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: finalFarmName,
          org_number: finalOrgNumber,
          address: farmAddress.trim(),
          postal_code: farmPostalCode.trim(),
          city: farmCity.trim(),
          municipality: farmMunicipality.trim(),
          manual_entry: isManualMode,
          organization_form: organizationForm,
          industry_code: farmIndustryCode,
          primary_farm_type: primaryFarmType,
          production_types: productionTypes,
          farm_size_range: farmSizeRange,
          team_size: teamSize,
          onboarding_goals: onboardingGoals,
          billing_method: paymentMethod,
          billing_email: billingEmail.trim() || undefined,
        }),
      })
      const farm = await farmResponse.json().catch(() => ({}))
      if (!farmResponse.ok) throw new Error(farm.detail || 'Kunne ikke opprette gården.')
      const updatedIdentity = await bootstrapIdentity(farm.id)
      if (updatedIdentity?.active_farm?.id) window.localStorage.setItem('barebonde_active_farm_id', updatedIdentity.active_farm.id)
      window.localStorage.removeItem(ONBOARDING_DRAFT_KEY)
      setStep('confirmation')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Kunne ikke fullføre registreringen. Prøv igjen.')
    } finally {
      setLoading(false)
    }
  }

  const selectedFarmOption = primaryFarmOptions.find((option) => option.value === primaryFarmType)

  return (
    <div className="flex min-h-screen flex-col bg-bonde-oat font-sans text-stone-900">
      <Navbar />

      <main className="flex flex-1 justify-center px-4 py-10 sm:py-14">
        <div className="w-full max-w-2xl">
          <div className="mb-7 text-center">
            <span className="mb-3 inline-block rounded-full border border-emerald-200/80 bg-bonde-light px-3.5 py-1 text-xs font-bold uppercase tracking-widest text-bonde-green">
              30 dagers gratis prøveperiode
            </span>
            <h1 className="mb-2 font-serif text-3xl font-normal text-stone-900 sm:text-4xl">
              {step === 'confirmation' ? 'Velkommen til Barebonde' : 'La oss gjøre Barebonde relevant fra start'}
            </h1>
            <p className="text-sm text-stone-600">
              {step === 'confirmation'
                ? 'Kontoen og gårdsprofilen din er opprettet.'
                : 'Svar på litt om gården din. Du kan alltid endre dette senere.'}
            </p>
          </div>

          {isSetupStep && (
            <ol className="mb-7 grid grid-cols-4 gap-2" aria-label="Fremdrift i oppsettet">
              {setupSteps.map((item, index) => {
                const isActive = item.id === step || (step === 'verifyEmail' && item.id === 'account')
                const isComplete = index < activeStepIndex
                return (
                  <li key={item.id} className="min-w-0 text-center">
                    <div className={`mb-1 h-1 rounded-full ${isComplete || isActive ? 'bg-bonde-green' : 'bg-stone-200'}`} />
                    <span className={`text-[11px] font-semibold ${isActive ? 'text-bonde-green' : 'text-stone-500'}`}>
                      {item.label}
                    </span>
                  </li>
                )
              })}
            </ol>
          )}

          {error && (
            <div className="mb-5 rounded-r-lg border-l-4 border-rose-500 bg-rose-50 p-4 text-sm text-rose-800" role="alert">
              {error}
            </div>
          )}

          <section className="rounded-2xl border border-stone-200/90 bg-white p-6 shadow-card sm:p-9">
            {step === 'business' && (
              <div className="space-y-7">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-bonde-green">Steg 1 av 4</p>
                  <h2 className="mt-1 text-xl font-semibold">Hvilket foretak gjelder det?</h2>
                  <p className="mt-1 text-sm text-stone-600">Søk i Brønnøysundregistrene, så fyller vi ut selskapsform og bransje der det finnes.</p>
                </div>

                {!isManualMode ? (
                  <div className="space-y-4">
                    <CompanySearch
                      onSelect={handleCompanySelect}
                      label="Søk etter gård eller foretak"
                      placeholder="Søk på navn eller organisasjonsnummer"
                    />
                    {selectedCompany && (
                      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <p className="font-semibold">{selectedCompany.name}</p>
                            <p className="mt-1 text-xs">Org.nr. {selectedCompany.org_number}{selectedCompany.municipality ? ` · ${selectedCompany.municipality}` : ''}</p>
                            {(farmAddress || farmPostalCode || farmCity) && <p className="mt-1 text-xs">{farmAddress}{farmPostalCode || farmCity ? ` · ${farmPostalCode} ${farmCity}`.trim() : ''}</p>}
                          </div>
                          <span className="rounded-full bg-emerald-200 px-2.5 py-1 text-[11px] font-bold text-emerald-800">Hentet fra Brønnøysundregistrene</span>
                        </div>
                        {(selectedCompany.organization_form || selectedCompany.industry_code) && (
                          <dl className="mt-3 grid gap-2 border-t border-emerald-200 pt-3 text-xs sm:grid-cols-2">
                            <div><dt className="font-semibold">Selskapsform</dt><dd>{selectedCompany.organization_form || 'Ikke oppgitt'}</dd></div>
                            <div><dt className="font-semibold">Bransje</dt><dd>{selectedCompany.industry_code || 'Ikke oppgitt'}</dd></div>
                          </dl>
                        )}
                        <div className="mt-4 grid gap-3 border-t border-emerald-200 pt-4 sm:grid-cols-2">
                          <div className="sm:col-span-2"><label className={labelClass} htmlFor="farm-address">Gårdens adresse</label><input id="farm-address" value={farmAddress} onChange={(event) => setFarmAddress(event.target.value)} className={inputClass} autoComplete="organization street-address" /></div>
                          <div><label className={labelClass} htmlFor="farm-postal-code">Postnummer</label><input id="farm-postal-code" value={farmPostalCode} onChange={(event) => setFarmPostalCode(event.target.value.replace(/\D/g, '').slice(0, 4))} className={inputClass} inputMode="numeric" autoComplete="postal-code" /></div>
                          <div><label className={labelClass} htmlFor="farm-city">Poststed</label><input id="farm-city" value={farmCity} onChange={(event) => setFarmCity(event.target.value)} className={inputClass} autoComplete="address-level2" /></div>
                        </div>
                      </div>
                    )}
                    <button type="button" onClick={() => { setIsManualMode(true); setSelectedCompany(null); setError(null) }} className="text-sm font-medium text-bonde-green underline underline-offset-2">
                      Finner du ikke foretaket? Fyll ut manuelt
                    </button>
                  </div>
                ) : (
                  <div className="space-y-5">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="sm:col-span-2">
                        <label className={labelClass} htmlFor="farm-name">Gårdsnavn eller foretaksnavn *</label>
                        <input id="farm-name" value={farmName} onChange={(event) => setFarmName(event.target.value)} className={inputClass} placeholder="Solberg gård" autoComplete="organization" />
                      </div>
                      <div>
                        <label className={labelClass} htmlFor="org-number">Organisasjonsnummer</label>
                        <input id="org-number" value={orgNumber} onChange={(event) => setOrgNumber(event.target.value.replace(/\D/g, '').slice(0, 9))} className={inputClass} inputMode="numeric" placeholder="Valgfritt, 9 siffer" />
                      </div>
                      <div>
                        <label className={labelClass} htmlFor="organization-form">Selskapsform</label>
                        <select id="organization-form" value={organizationForm} onChange={(event) => setOrganizationForm(event.target.value)} className={inputClass}>
                          <option value="">Velg hvis du vet</option>
                          <option value="ENK">Enkeltpersonforetak</option>
                          <option value="AS">Aksjeselskap</option>
                          <option value="SA">Samvirkeforetak</option>
                          <option value="annet">Annet</option>
                        </select>
                      </div>
                      <div className="sm:col-span-2">
                        <label className={labelClass} htmlFor="farm-address">Gårdens adresse</label>
                        <input id="farm-address" value={farmAddress} onChange={(event) => setFarmAddress(event.target.value)} className={inputClass} autoComplete="organization street-address" placeholder="Gårdsveien 14" />
                      </div>
                      <div>
                        <label className={labelClass} htmlFor="farm-postal-code">Postnummer</label>
                        <input id="farm-postal-code" value={farmPostalCode} onChange={(event) => setFarmPostalCode(event.target.value.replace(/\D/g, '').slice(0, 4))} className={inputClass} inputMode="numeric" autoComplete="postal-code" placeholder="2350" />
                      </div>
                      <div>
                        <label className={labelClass} htmlFor="farm-city">Poststed</label>
                        <input id="farm-city" value={farmCity} onChange={(event) => setFarmCity(event.target.value)} className={inputClass} autoComplete="address-level2" placeholder="Nes på Hedmarken" />
                      </div>
                    </div>
                    <button type="button" onClick={() => { setIsManualMode(false); setError(null) }} className="text-sm font-medium text-bonde-green underline underline-offset-2">
                      Tilbake til søk i Brønnøysundregistrene
                    </button>
                  </div>
                )}

                <Button type="button" onClick={goToOperations} fullWidth showArrow>
                  Fortsett
                </Button>
              </div>
            )}

            {step === 'operations' && (
              <div className="space-y-7">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-bonde-green">Steg 2 av 4</p>
                  <h2 className="mt-1 text-xl font-semibold">Fortell litt om driften</h2>
                  <p className="mt-1 text-sm text-stone-600">Dette velger startsiden, snarveier og forslag som passer gården din.</p>
                </div>

                <fieldset>
                  <legend className={labelClass}>Hva er den viktigste driftsretningen? *</legend>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {primaryFarmOptions.map((option) => (
                      <button key={option.value} type="button" onClick={() => setPrimaryFarmType(option.value)} className={`rounded-xl border-2 p-4 text-left transition ${primaryFarmType === option.value ? 'border-bonde-green bg-emerald-50/70' : 'border-stone-200 hover:border-stone-300'}`}>
                        <span className="block text-sm font-semibold">{option.label}</span>
                        <span className="mt-1 block text-xs text-stone-600">{option.description}</span>
                      </button>
                    ))}
                  </div>
                </fieldset>

                <fieldset>
                  <legend className={labelClass}>Hva produserer dere? <span className="normal-case font-normal text-stone-500">Velg gjerne flere.</span></legend>
                  <div className="flex flex-wrap gap-2">
                    {productionOptions.map((option) => {
                      const selected = productionTypes.includes(option.value)
                      return <button key={option.value} type="button" onClick={() => setProductionTypes((current) => toggleValue(current, option.value))} className={`rounded-full border px-3 py-2 text-sm transition ${selected ? 'border-bonde-green bg-bonde-green text-white' : 'border-stone-300 text-stone-700 hover:border-bonde-green'}`}>{option.label}</button>
                    })}
                  </div>
                </fieldset>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className={labelClass} htmlFor="farm-size">Omtrent hvor stort er gården?</label>
                    <select id="farm-size" value={farmSizeRange} onChange={(event) => setFarmSizeRange(event.target.value)} className={inputClass}>
                      <option value="vet_ikke">Vet ikke ennå</option>
                      <option value="under_50">Under 50 dekar</option>
                      <option value="50_199">50–199 dekar</option>
                      <option value="200_499">200–499 dekar</option>
                      <option value="500_plus">500 dekar eller mer</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelClass} htmlFor="team-size">Hvor mange bruker Barebonde?</label>
                    <select id="team-size" value={teamSize} onChange={(event) => setTeamSize(event.target.value)} className={inputClass}>
                      <option value="1">Bare meg</option>
                      <option value="2_5">2–5 personer</option>
                      <option value="6_10">6–10 personer</option>
                      <option value="11_plus">11 eller flere</option>
                    </select>
                  </div>
                </div>

                <fieldset>
                  <legend className={labelClass}>Hva vil du helst ha hjelp med først? *</legend>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {goalOptions.map((option) => {
                      const selected = onboardingGoals.includes(option.value)
                      return <button key={option.value} type="button" onClick={() => setOnboardingGoals((current) => toggleValue(current, option.value))} className={`rounded-xl border px-3 py-3 text-left text-sm transition ${selected ? 'border-bonde-green bg-emerald-50 text-bonde-green' : 'border-stone-200 text-stone-700 hover:border-stone-300'}`}>{selected ? '✓ ' : ''}{option.label}</button>
                    })}
                  </div>
                </fieldset>

                <div className="flex gap-3">
                  <Button type="button" variant="secondary" onClick={() => { setError(null); setStep('business') }}>Tilbake</Button>
                  <Button type="button" onClick={goToAccount} fullWidth showArrow>Fortsett</Button>
                </div>
              </div>
            )}

            {step === 'account' && (
              <div className="space-y-7">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-bonde-green">Steg 3 av 4</p>
                  <h2 className="mt-1 text-xl font-semibold">Hvem skal bruke Barebonde?</h2>
                  <p className="mt-1 text-sm text-stone-600">Vi bruker opplysningene til å sette opp kontoen og tilpasse opplevelsen. E-postadressen bekreftes før dere velger betaling.</p>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div><label className={labelClass} htmlFor="first-name">Fornavn *</label><input id="first-name" value={firstName} onChange={(event) => setFirstName(event.target.value)} className={inputClass} autoComplete="given-name" placeholder="Ola" /></div>
                  <div><label className={labelClass} htmlFor="last-name">Etternavn *</label><input id="last-name" value={lastName} onChange={(event) => setLastName(event.target.value)} className={inputClass} autoComplete="family-name" placeholder="Nordmann" /></div>
                </div>
                <div><label className={labelClass} htmlFor="email">E-postadresse *</label><input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} className={inputClass} autoComplete="email" placeholder="ola@eksempel.no" /></div>
                <div><label className={labelClass} htmlFor="phone">Telefonnummer *</label><input id="phone" type="tel" value={phoneNumber} onChange={(event) => setPhoneNumber(event.target.value)} className={inputClass} autoComplete="tel" inputMode="tel" placeholder="+47 912 34 567" /><p className="mt-1.5 text-xs text-stone-500">Norske åttesifrede numre lagres som +47. Andre nummer må ha landskode.</p></div>
                <div><label className={labelClass} htmlFor="personal-address">Din adresse <span className="normal-case font-normal text-stone-500">(valgfritt)</span></label><input id="personal-address" value={personalAddress} onChange={(event) => setPersonalAddress(event.target.value)} className={inputClass} autoComplete="street-address" placeholder="Svennerudvegen 221" /></div>

                <fieldset>
                  <legend className={labelClass}>Hva er rollen din på gården?</legend>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {[['owner', 'Eier eller driver'], ['manager', 'Driftsleder'], ['employee', 'Ansatt'], ['advisor', 'Regnskapsfører eller rådgiver']].map(([value, label]) => (
                      <button key={value} type="button" onClick={() => setOnboardingRole(value)} className={`rounded-xl border px-3 py-3 text-left text-sm transition ${onboardingRole === value ? 'border-bonde-green bg-emerald-50 text-bonde-green' : 'border-stone-200 text-stone-700 hover:border-stone-300'}`}>{onboardingRole === value ? '✓ ' : ''}{label}</button>
                    ))}
                  </div>
                </fieldset>

                <p className="rounded-xl border border-stone-200 bg-stone-50 p-4 text-sm text-stone-700">Du trenger ikke passord. Vi sender en sikker engangslenke som bekrefter e-postadressen før dere går videre til betaling.</p>

                <div className="flex gap-3">
                  <Button type="button" variant="secondary" onClick={() => { setError(null); setStep('operations') }}>Tilbake</Button>
                  <Button type="button" onClick={requestEmailVerification} disabled={loading} fullWidth showArrow>{loading ? 'Sender lenke...' : 'Bekreft e-post'}</Button>
                </div>
              </div>
            )}

            {step === 'verifyEmail' && (
              <div className="space-y-7">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-bonde-green">Steg 3 av 4</p>
                  <h2 className="mt-1 text-xl font-semibold">Bekreft e-postadressen din</h2>
                  <p className="mt-1 text-sm text-stone-600">Vi har sendt en engangslenke til <strong>{email}</strong>. Åpne lenken for å bekrefte e-postadressen og fortsette til betaling.</p>
                </div>

                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
                  <p className="font-semibold">Sjekk innboksen din</p>
                  <p className="mt-1 text-xs">Lenken kan brukes én gang og utløper etter kort tid. Du kommer tilbake hit automatisk når e-postadressen er bekreftet.</p>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button type="button" variant="secondary" onClick={() => { setError(null); setStep('account') }}>Endre opplysninger</Button>
                  <Button type="button" onClick={handleResendEmail} disabled={resendLoading} fullWidth>{resendLoading ? 'Sender...' : 'Send lenken på nytt'}</Button>
                </div>
                {resendMessage && <p className="text-sm text-stone-600">{resendMessage}</p>}
              </div>
            )}

            {step === 'payment' && (
              <form onSubmit={handleFinalSubmit} className="space-y-7">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-bonde-green">Steg 4 av 4</p>
                  <h2 className="mt-1 text-xl font-semibold">Velg hvordan dere vil betale</h2>
                  <p className="mt-1 text-sm text-stone-600">Prøveperioden er gratis i 30 dager. Betalingsvalg kan endres senere.</p>
                </div>
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"><strong>0 kr de første 30 dagene.</strong><br /><span className="text-xs">Abonnementet er 290 kr/mnd etter prøveperioden og kan avsluttes når som helst.</span></div>

                <fieldset className="space-y-3">
                  <legend className={labelClass}>Betalingsmetode</legend>
                  {[
                    ['faktura', 'EHF eller e-postfaktura', 'Passer når foretaket skal motta faktura.'],
                    ['vipps', 'Vipps faste betalinger', 'Automatisk månedlig trekk via Vipps-appen.'],
                  ].map(([value, label, description]) => (
                    <button key={value} type="button" onClick={() => setPaymentMethod(value as 'faktura' | 'vipps')} className={`flex w-full items-center justify-between gap-4 rounded-xl border-2 p-4 text-left transition ${paymentMethod === value ? 'border-bonde-green bg-emerald-50/70' : 'border-stone-200 hover:border-stone-300'}`}>
                      <span><span className="block text-sm font-semibold">{label}</span><span className="mt-1 block text-xs text-stone-600">{description}</span></span>
                      <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${paymentMethod === value ? 'border-bonde-green' : 'border-stone-300'}`}>{paymentMethod === value && <span className="h-2.5 w-2.5 rounded-full bg-bonde-green" />}</span>
                    </button>
                  ))}
                </fieldset>

                {paymentMethod === 'faktura' && <div><label className={labelClass} htmlFor="billing-email">E-post for faktura <span className="normal-case font-normal text-stone-500">(valgfritt)</span></label><input id="billing-email" type="email" value={billingEmail} onChange={(event) => setBillingEmail(event.target.value)} className={inputClass} placeholder={email || 'faktura@solberggard.no'} /></div>}

                <div className="rounded-xl bg-stone-50 p-4 text-xs text-stone-600"><p className="font-semibold text-stone-800">Oppsummering</p><p className="mt-1">{finalFarmNameForSummary(selectedCompany, farmName)} · {selectedFarmOption?.label || 'Drift ikke valgt'} · {onboardingGoals.length} valgte område{onboardingGoals.length === 1 ? '' : 'r'}</p></div>

                <div className="flex gap-3">
                  <Button type="button" variant="secondary" onClick={() => { setError(null); setStep('account') }}>Tilbake</Button>
                  <Button type="submit" disabled={loading} fullWidth showArrow>{loading ? 'Oppretter konto...' : 'Opprett konto'}</Button>
                </div>
              </form>
            )}

            {step === 'confirmation' && (
              <div className="space-y-6 text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-2xl text-bonde-green">✓</div>
                <div><h2 className="text-2xl font-semibold">Gårdsprofilen er klar</h2><p className="mt-2 text-sm text-stone-600">{emailStatus?.message || 'Du er klar til å ta i bruk Barebonde.'}</p></div>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button type="button" fullWidth onClick={() => router.push('/dashboard')}>Gå til oversikten</Button>
                  <Link href="/" className="inline-flex items-center justify-center rounded-lg border border-stone-200 px-6 py-3 text-xs font-medium uppercase tracking-wide text-stone-700 transition hover:bg-bonde-light sm:text-sm">Til forsiden</Link>
                </div>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}

function finalFarmNameForSummary(selectedCompany: Company | null, farmName: string): string {
  return selectedCompany?.name || farmName || 'Gården din'
}
