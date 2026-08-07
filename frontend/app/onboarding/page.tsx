'use client'

import { useEffect, useState } from 'react'
import { Navbar } from '@/components/navigation/Navbar'
import { apiErrorMessage, apiFetch, bootstrapIdentity, IdentityBootstrap } from '@/lib/api'
import { OnboardingStep, InterestsSelector, Summary } from '@/components/onboarding'
import Link from 'next/link'

interface State {
  completed: boolean
  current_step: string
  completed_steps: string[]
  completion_percent: number
  interests: string[]
}

export default function OnboardingPage() {
  const [state, setState] = useState<State | null>(null)
  const [identity, setIdentity] = useState<IdentityBootstrap | null>(null)
  const [message, setMessage] = useState('')
  const [isCompleting, setIsCompleting] = useState(false)

  const load = async () => {
    try {
      const [identityResult, response] = await Promise.all([
        bootstrapIdentity(),
        apiFetch('/api/onboarding'),
      ])
      setIdentity(identityResult)
      
      if (!response.ok) {
        return setMessage(await apiErrorMessage(response, 'Kunne ikke hente onboarding.'))
      }
      
      setState(await response.json())
    } catch {
      setMessage('Du må logge inn.')
    }
  }

  useEffect(() => {
    load().catch(() => setMessage('Du må logge inn.'))
  }, [])

  const save = async (body: unknown) => {
    const response = await apiFetch('/api/onboarding', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    
    if (!response.ok) {
      return setMessage(await apiErrorMessage(response, 'Kunne ikke lagre.'))
    }
    
    setState(await response.json())
    setMessage('Lagret ✓')
    
    // Clear success message after 3 seconds
    setTimeout(() => setMessage(''), 3000)
  }

  const complete = async () => {
    if (!state) return
    
    setIsCompleting(true)
    setMessage('')
    
    try {
      const response = await apiFetch('/api/onboarding/complete', { method: 'POST' })
      
      if (!response.ok) {
        const error = await apiErrorMessage(response, 'Fullfør obligatoriske steg først.')
        return setMessage(error)
      }
      
      setState(await response.json())
      setMessage('🎉 Onboarding er fullført! Velkommen til Barebonde.')
    } catch {
      setMessage('Noe gikk galt. Prøv igjen.')
    } finally {
      setIsCompleting(false)
    }
  }

  if (!state) {
    return (
      <div className="min-h-screen bg-bonde-oat flex items-center justify-center">
        <div className="animate-pulse text-gray-600">Laster inn...</div>
      </div>
    )
  }

  // Calculate next recommended action
  const getNextAction = () => {
    const requiredSteps = ['profile', 'farm']
    const missingRequired = requiredSteps.filter(step => !state.completed_steps.includes(step))
    
    if (missingRequired.length > 0) {
      if (missingRequired.includes('profile')) {
        return { title: 'Fullfør profilen din', href: '/profile', priority: 'high' }
      }
      if (missingRequired.includes('farm')) {
        return { title: 'Registrer eller velg gård', href: '/farm/setup', priority: 'high' }
      }
    }
    
    const optionalSteps = ['farm_settings', 'bank_account', 'interests']
    const missingOptional = optionalSteps.filter(step => !state.completed_steps.includes(step))
    
    if (missingOptional.length > 0) {
      const stepMap: Record<string, { title: string; href: string }> = {
        farm_settings: { title: 'Tilpass gårdsinnstillinger', href: '/settings/farm' },
        bank_account: { title: 'Legg til bankkonto', href: '/settings/bank-accounts' },
        interests: { title: 'Velg hva du vil bruke Barebonde til', href: '#interests' },
      }
      const next = missingOptional[0]
      return { title: stepMap[next]?.title || 'Neste steg', href: stepMap[next]?.href || '#', priority: 'normal' }
    }
    
    return { title: 'Fullfør onboarding', href: '#', priority: 'complete' }
  }

  const nextAction = getNextAction()

  return (
    <div className="min-h-screen bg-gradient-to-b from-bonde-oat to-white">
      <Navbar />
      <main className="mx-auto max-w-4xl p-4 sm:p-6">
        {/* Welcome Header */}
        <header className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-bonde-light px-4 py-1.5 text-sm font-medium text-bonde-green">
            🌱 Velkommen til Barebonde
          </div>
          <h1 className="mt-4 text-3xl sm:text-4xl font-serif text-gray-900">
            Kom i gang på 5 minutter
          </h1>
          <p className="mt-3 text-base text-gray-600 max-w-2xl mx-auto">
            Følg stegene under for å sette opp kontoen din. Du kan når som helst lagre og komme tilbake senere.
          </p>
        </header>

        {/* Progress Card */}
        <div className="mb-8 rounded-2xl bg-white p-6 shadow-lg border border-stone-100">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <div className={`flex h-12 w-12 items-center justify-center rounded-full text-xl font-bold ${
                  state.completion_percent === 100 
                    ? 'bg-bonde-green text-white' 
                    : 'bg-bonde-light text-bonde-green'
                }`}>
                  {state.completion_percent === 100 ? '✓' : `${state.completion_percent}%`}
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    {state.completion_percent === 100 ? 'Gratulerer!' : 'Din fremdrift'}
                  </h2>
                  <p className="text-sm text-gray-600">
                    {state.completed_steps.length} av 7 steg fullført
                    {state.completion_percent === 100 ? ' - alt er klart!' : ''}
                  </p>
                </div>
              </div>
            </div>
            
            {state.completion_percent < 100 && (
              <Link 
                href={nextAction.href}
                className={`inline-flex items-center justify-center rounded-lg px-6 py-3 font-medium transition-all ${
                  nextAction.priority === 'high'
                    ? 'bg-bonde-green text-white hover:bg-bonde-green/90 shadow-md'
                    : 'bg-stone-100 text-stone-700 hover:bg-stone-200'
                }`}
              >
                {nextAction.title} →
              </Link>
            )}
          </div>
          
          {/* Mini progress bar */}
          <div className="mt-6">
            <div className="flex justify-between text-xs text-gray-500 mb-2">
              <span>Obligatoriske steg</span>
              <span>{state.completed_steps.includes('profile') && state.completed_steps.includes('farm') ? 'Fullført' : 'Pågår'}</span>
            </div>
            <div className="h-2 w-full rounded-full bg-stone-100 overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-bonde-green to-emerald-500 transition-all duration-500"
                style={{ width: `${((state.completed_steps.filter(s => ['profile', 'farm'].includes(s)).length) / 2) * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Main content card */}
        <div className="rounded-2xl bg-white p-6 shadow-lg border border-stone-100">
          {/* Step 1: Account / e-post */}
          <OnboardingStep
            stepNumber={1}
            title="Konto"
            description="E-postadressen din er bekreftet når kontoen er aktiv."
            isCompleted={state.completed_steps.includes('identity')}
            href="/profile"
            linkText={state.completed_steps.includes('identity') ? 'Kontoen er aktiv' : 'Bekreft e-post'}
          />

          {/* Step 2: Profile */}
          <OnboardingStep
            stepNumber={2}
            title="Personlig profil"
            description="Fullfør navn, telefon og aksepter vilkår/personvern."
            isCompleted={state.completed_steps.includes('profile')}
            href="/profile"
            linkText={state.completed_steps.includes('profile') ? 'Se profil' : 'Fullfør profil'}
          >
            {!state.completed_steps.includes('profile') && (
              <button
                onClick={() => save({ accept_terms: true, accept_privacy: true, current_step: 'profile' })}
                className="mt-2 text-sm text-bonde-green hover:text-bonde-green/80 underline transition-colors focus:outline-none focus:ring-2 focus:ring-bonde-green focus:ring-offset-2 rounded"
                aria-label="Aksepter vilkår og personvern"
              >
                Aksepter vilkår og personvern
              </button>
            )}
          </OnboardingStep>

          {/* Step 3: Farm/Virksomhet */}
          <OnboardingStep
            stepNumber={3}
            title="Virksomhet"
            description="Registrer eller velg gården din"
            isCompleted={state.completed_steps.includes('farm')}
            href="/farm/setup"
            linkText={state.completed_steps.includes('farm') ? 'Se gård' : 'Opprett eller velg gård'}
          />

          {/* Step 4: Farm settings */}
          <OnboardingStep
            stepNumber={4}
            title="Gårdsinnstillinger"
            description="Tilpass hvordan du vil drive gården"
            isCompleted={state.completed_steps.includes('farm_settings')}
            href="/settings/farm"
            linkText="Åpne gårdsinnstillinger"
          />

          {/* Step 5: Bank account (optional) */}
          <OnboardingStep
            stepNumber={5}
            title="Bankkonto"
            description="Legg til bankkonto for enklere betalinger (valgfritt)"
            isCompleted={state.completed_steps.includes('bank_account')}
            href="/settings/bank-accounts"
            linkText="Legg til bankkonto"
            optional
          />

          {/* Step 6: Interests */}
          <section id="interests" className="border-b border-gray-100 pb-6 last:border-0">
            <div className="flex items-start gap-4">
              <div 
                className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                  state.completed_steps.includes('interests')
                    ? 'bg-bonde-green text-white'
                    : 'bg-gray-200 text-gray-600'
                }`}
              >
                {state.completed_steps.includes('interests') ? '✓' : '6'}
              </div>
              <div className="flex-1">
                <h2 className="font-semibold text-gray-900">
                  Hva vil du bruke Barebonde til?
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Hjelp oss å tilpasse opplevelsen til dine behov
                </p>
                <InterestsSelector
                  interests={state.interests}
                  onSave={(newInterests) => save({ interests: newInterests, current_step: 'interests' })}
                />
              </div>
            </div>
          </section>

          {/* Summary */}
          <Summary
            displayName={identity?.user.display_name}
            email={identity?.user.email}
            farmName={identity?.active_farm?.name}
            subscriptionName={identity?.subscription?.display_name}
            completedSteps={state.completed_steps}
          />

          {/* Complete button */}
          <div className="mt-8">
            <button
              onClick={complete}
              disabled={isCompleting || !state.completed_steps.includes('profile') || !state.completed_steps.includes('farm')}
              className="w-full sm:w-auto rounded-xl bg-bonde-green px-8 py-4 text-white font-semibold hover:bg-bonde-green/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-bonde-green focus:ring-offset-2 shadow-md"
            >
              {isCompleting ? 'Fullfører...' : state.completion_percent === 100 ? '✅ Fullført!' : 'Fullfør onboarding'}
            </button>
          </div>

          {/* Messages */}
          {message && (
            <div 
              className={`mt-6 p-4 rounded-xl text-sm ${
                message.includes('✓') || message.includes('🎉')
                  ? 'bg-green-50 text-green-700 border border-green-200'
                  : 'bg-red-50 text-red-700 border border-red-200'
              }`}
              role={message.includes('Feil') || message.includes('Kunne ikke') ? 'alert' : 'status'}
            >
              {message}
            </div>
          )}
        </div>

        {/* Help section */}
        <div className="mt-8 text-center">
          <p className="text-sm text-gray-600">
            Trenger du hjelp?{' '}
            <a href="mailto:post@barebonde.no" className="text-bonde-green hover:underline font-medium">
              Kontakt oss
            </a>
          </p>
        </div>
      </main>
    </div>
  )
}
