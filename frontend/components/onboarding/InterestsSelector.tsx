'use client'

import { useState } from 'react'

interface InterestsSelectorProps {
  interests: string[]
  onSave: (newInterests: string[]) => Promise<void>
}

const INTERESTS = [
  { id: 'bilag', label: 'Bilag', description: 'Registrer og behold oversikt over bilag' },
  { id: 'bokforing', label: 'Bokføring', description: 'Full regnskapsføring' },
  { id: 'rapporter', label: 'Rapporter', description: 'Økonomiske rapporter og oversikter' },
  { id: 'fakturering', label: 'Fakturering', description: 'Send og motta fakturaer' },
  { id: 'ehf', label: 'EHF', description: 'Elektronisk handelsformat' },
  { id: 'maskiner', label: 'Maskiner', description: 'Oversikt over maskiner og utstyr' },
  { id: 'vedlikehold', label: 'Vedlikehold', description: 'Service og vedlikeholdsplaner' },
  { id: 'oppgaver', label: 'Oppgaver', description: 'Daglige oppgaver og påminnelser' },
  { id: 'avtaler_frister', label: 'Avtaler & frister', description: 'Kontrakter og viktige datoer' },
]

export function InterestsSelector({ interests, onSave }: InterestsSelectorProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState('')

  const toggleInterest = async (interestId: string) => {
    if (isSaving) return
    
    setIsSaving(true)
    setMessage('')
    
    try {
      const newInterests = interests.includes(interestId)
        ? interests.filter(i => i !== interestId)
        : [...interests, interestId]
      
      await onSave(newInterests)
    } catch (error) {
      setMessage('Kunne ikke lagre endringen. Prøv igjen.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="mt-3">
      <p className="text-sm text-gray-600 mb-3">
        Velg det du er interessert i å bruke. Du kan alltid endre senere.
      </p>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {INTERESTS.map(({ id, label, description }) => {
          const isSelected = interests.includes(id)
          
          return (
            <label 
              key={id}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                isSelected 
                  ? 'border-bonde-green bg-bonde-green/5' 
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => toggleInterest(id)}
                disabled={isSaving}
                className="mt-1 w-4 h-4 text-bonde-green border-gray-300 rounded focus:ring-bonde-green"
                aria-describedby={`${id}-description`}
              />
              <div>
                <span className="text-sm font-medium text-gray-900">{label}</span>
                <p id={`${id}-description`} className="text-xs text-gray-500 mt-0.5">
                  {description}
                </p>
              </div>
            </label>
          )
        })}
      </div>
      
      {message && (
        <p className="mt-2 text-sm text-red-600" role="alert">
          {message}
        </p>
      )}
    </div>
  )
}
