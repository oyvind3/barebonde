'use client'

interface SummaryProps {
  displayName?: string
  email?: string
  farmName?: string
  subscriptionName?: string
  completedSteps: string[]
}

export function Summary({ 
  displayName, 
  email, 
  farmName, 
  subscriptionName,
  completedSteps 
}: SummaryProps) {
  const requiredSteps = ['identity', 'profile', 'farm']
  const allRequiredCompleted = requiredSteps.every(step => completedSteps.includes(step))

  return (
    <div className="mt-6 p-4 bg-gray-50 rounded-lg">
      <h3 className="font-semibold text-gray-900 mb-3">Oppsummering</h3>
      
      <dl className="space-y-2 text-sm">
        <div>
          <dt className="text-gray-600">Bruker</dt>
          <dd className="font-medium text-gray-900">
            {displayName || email || 'Ikke oppgitt'}
          </dd>
        </div>
        
        <div>
          <dt className="text-gray-600">Gård</dt>
          <dd className="font-medium text-gray-900">
            {farmName || 'Ingen gård registrert'}
          </dd>
        </div>
        
        <div>
          <dt className="text-gray-600">Abonnement</dt>
          <dd className="font-medium text-gray-900">
            {subscriptionName || 'Ingen plan valgt'}
          </dd>
        </div>
      </dl>
      
      {allRequiredCompleted ? (
        <p className="mt-3 text-sm text-bonde-green font-medium">
          ✓ Klar til å fullføre onboarding
        </p>
      ) : (
        <p className="mt-3 text-sm text-orange-600">
          Fullfør profil og gårdregistrering for å avslutte
        </p>
      )}
    </div>
  )
}
