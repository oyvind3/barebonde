'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { authClient } from '@/lib/auth-client'

export default function AuthCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get session token from URL params (set by better-auth.com)
        const sessionToken = searchParams.get('session_token')
        
        if (!sessionToken) {
          setError('Ingen gyldig sesjonstoken. Prøv igjen.')
          setLoading(false)
          return
        }

        // Send callback to backend
        await authClient.handleCallback(sessionToken)
        
        // Redirect to farm setup if first login, otherwise dashboard
        router.push('/farm/setup')
      } catch (err: any) {
        setError(err.message || 'Innlogging feilet. Prøv igjen.')
        setLoading(false)
      }
    }

    handleCallback()
  }, [router, searchParams])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-farm-green mb-4">Innlogger...</h1>
          <p className="text-gray-600">Vennligst vent mens vi oppretter kontoen din</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Feil</h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <a href="/" className="text-farm-green hover:underline">
            Tilbake til forsiden
          </a>
        </div>
      </div>
    )
  }

  return null
}
