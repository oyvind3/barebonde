'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Navbar } from '@/components/navigation/Navbar'
import { apiErrorMessage, apiFetch, bootstrapIdentity, IdentityBootstrap } from '@/lib/api'
import { ProgressTracker, OnboardingStep, InterestsSelector, Summary } from '@/components/onboarding'

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

  return (
    <div className="min-h-screen bg-bonde-oat">
      <Navbar />
      <main className="mx-auto max-w-3xl p-4 sm:p-6">
        {/* Header - mobile responsive */}
        <header className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-serif text-gray-900">
            Kom i gang med Barebonde
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Følg stegene under for å sette opp kontoen din
          </p>
        </header>

        {/* Progress tracker */}
        <ProgressTracker
          completedSteps={state.completed_steps}
          totalSteps={7}
          completionPercent={state.completion_percent}
        />

        {/* Main content card */}
        <div className="rounded-xl bg-white p-4 sm:p-6 shadow-sm">
          {/* Step 1: Profile */}
          <OnboardingStep
            stepNumber={1}
            title="Personlig profil"
            description="Fullfør navn, telefon og aksepter vilkår/personvern."
            isCompleted={state.completed_steps.includes('profile')}
            href="/profile"
            linkText="Åpne profil"
          >
            <button
              onClick={() => save({ accept_terms: true, accept_privacy: true, current_step: 'profile' })}
              className="mt-2 text-sm text-bonde-green hover:text-bonde-green/80 underline transition-colors focus:outline-none focus:ring-2 focus:ring-bonde-green focus:ring-offset-2 rounded"
              aria-label="Aksepter vilkår og personvern"
            >
              Aksepter vilkår og personvern
            </button>
          </OnboardingStep>

          {/* Step 2: Farm/Virksomhet */}
          <OnboardingStep
            stepNumber={2}
            title="Virksomhet"
            description="Registrer eller velg gården din"
            isCompleted={state.completed_steps.includes('farm')}
            href="/farm/setup"
            linkText="Opprett eller velg gård"
          />

          {/* Step 3: Farm settings */}
          <OnboardingStep
            stepNumber={3}
            title="Gårdsinnstillinger"
            description="Tilpass hvordan du vil drive gården"
            isCompleted={state.completed_steps.includes('farm_settings')}
            href="/settings/farm"
            linkText="Åpne gårdsinnstillinger"
          />

          {/* Step 4: Bank account (optional) */}
          <OnboardingStep
            stepNumber={4}
            title="Bankkonto"
            description="Legg til bankkonto for enklere betalinger (valgfritt)"
            isCompleted={state.completed_steps.includes('bank_account')}
            href="/settings/bank-accounts"
            linkText="Legg til bankkonto"
          />

          {/* Step 5: Interests */}
          <section className="border-b border-gray-100 pb-4 last:border-0">
            <div className="flex items-start gap-3">
              <div 
                className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${
                  state.completed_steps.includes('interests')
                    ? 'bg-bonde-green text-white'
                    : 'bg-gray-200 text-gray-600'
                }`}
              >
                5
              </div>
              <div className="flex-1">
                <h2 className="font-semibold text-gray-900">
                  Hva vil du bruke Barebonde til?
                </h2>
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
          <div className="mt-6">
            <button
              onClick={complete}
              disabled={isCompleting || !state.completed_steps.includes('profile') || !state.completed_steps.includes('farm')}
              className="w-full sm:w-auto rounded-lg bg-bonde-green px-6 py-3 text-white font-medium hover:bg-bonde-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-bonde-green focus:ring-offset-2"
            >
              {isCompleting ? 'Fullfører...' : 'Fullfør onboarding'}
            </button>
          </div>

          {/* Messages */}
          {message && (
            <div 
              className={`mt-4 p-3 rounded-lg text-sm ${
                message.includes('✓') || message.includes('🎉')
                  ? 'bg-green-50 text-green-700'
                  : 'bg-red-50 text-red-700'
              }`}
              role={message.includes('Feil') || message.includes('Kunne ikke') ? 'alert' : 'status'}
            >
              {message}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
