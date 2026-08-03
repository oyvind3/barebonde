'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'

interface GoogleCredentialResponse {
  clientId: string
  credential: string
  select_by: string
}

interface GoogleLoginButtonProps {
  onSuccess?: (response: any) => void
  onError?: (error: string) => void
  disabled?: boolean
  className?: string
}

declare global {
  interface Window {
    google: any
  }
}

/**
 * Google Login Button Component
 * 
 * Uses Google Identity Services to safely handle OAuth 2.0 authentication.
 * Token is verified on the backend before the user is authenticated.
 * 
 * Security:
 * - GOOGLE_CLIENT_ID is safe to expose (it's public)
 * - JWT token is sent to backend for verification
 * - GOOGLE_CLIENT_SECRET stays on backend only
 * - Token is verified server-side with google-auth library
 */
export function GoogleLoginButton({
  onSuccess,
  onError,
  disabled = false,
  className = '',
}: GoogleLoginButtonProps) {
  const router = useRouter()
  const googleButtonRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Load Google Identity Services script
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true

    script.onload = () => {
      if (window.google) {
        initializeGoogleButton()
      }
    }

    script.onerror = () => {
      const errorMsg = 'Klarte ikke laste Google Sign-In'
      setError(errorMsg)
      onError?.(errorMsg)
    }

    document.body.appendChild(script)

    return () => {
      document.body.removeChild(script)
    }
  }, [onError])

  const initializeGoogleButton = () => {
    if (!window.google || !googleButtonRef.current) return

    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
    if (!clientId) {
      const errorMsg = 'Google Client ID not configured'
      console.error(errorMsg)
      setError(errorMsg)
      onError?.(errorMsg)
      return
    }

    // Initialize Google Sign-In button
    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: handleCredentialResponse,
      auto_select: false,
    })

    // Render the button into the container
    window.google.accounts.id.renderButton(googleButtonRef.current, {
      type: 'standard',
      shape: 'rectangular',
      theme: 'outline',
      text: 'signin_with',
      size: 'large',
      logo_alignment: 'left',
      width: '100%',
    })
  }

  /**
   * Handle credential response from Google
   * Sends JWT token to backend for verification
   */
  const handleCredentialResponse = async (
    response: GoogleCredentialResponse
  ) => {
    setLoading(true)
    setError(null)

    try {
      if (!response.credential) {
        throw new Error('Ingen token mottatt fra Google')
      }

      // Send JWT token to backend for verification
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${apiUrl}/api/auth/google`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: response.credential,
        }),
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(
          errorData.detail || 'Google autentisering feilet på serveren'
        )
      }

      const userData = await res.json()
      console.log('Google auth successful:', userData)

      // Call success callback if provided
      if (onSuccess) {
        onSuccess(userData)
      }

      // Store auth info and redirect to dashboard
      if (typeof window !== 'undefined') {
        // Store user info in localStorage (or use a proper auth state manager)
        localStorage.setItem('user', JSON.stringify(userData))
      }

      // Redirect to dashboard
      router.push('/dashboard')
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : 'Google autentisering feilet'
      console.error('Google auth error:', errorMsg)
      setError(errorMsg)
      onError?.(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={className}>
      {/* Google Button Container */}
      <div
        ref={googleButtonRef}
        className="flex justify-center"
        style={{
          minHeight: '40px',
          display: 'flex',
          alignItems: 'center',
        }}
      />

      {/* Error Message */}
      {error && (
        <div className="mt-3 bg-rose-50 border-l-4 border-rose-500 text-rose-800 p-3 text-sm rounded-r-lg">
          <p className="font-semibold">Google innlogging feilet</p>
          <p>{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="mt-3 text-center text-sm text-stone-600">
          Verifiserer med Google...
        </div>
      )}
    </div>
  )
}
