'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { API_BASE_URL } from '@/lib/api'

export type GoogleUser = {
  user_id?: string
  google_id?: string
  email: string
  first_name: string
  last_name: string
  picture?: string | null
  message: string
  credential?: string
}

interface GoogleCredentialResponse {
  credential: string
}

interface GoogleLoginButtonProps {
  onSuccess?: (user: GoogleUser) => void
  onError?: (error: string) => void
  disabled?: boolean
  className?: string
  redirectTo?: string | null
  deferPersistence?: boolean
}

declare global {
  interface Window {
    google?: any
  }
}

export function GoogleLoginButton({
  onSuccess,
  onError,
  disabled = false,
  className = '',
  redirectTo = '/dashboard',
  deferPersistence = false,
}: GoogleLoginButtonProps) {
  const router = useRouter()
  const googleButtonRef = useRef<HTMLDivElement>(null)
  const onSuccessRef = useRef(onSuccess)
  const onErrorRef = useRef(onError)
  const [clientId, setClientId] = useState(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [buttonWidth, setButtonWidth] = useState(320)

  useEffect(() => {
    onSuccessRef.current = onSuccess
    onErrorRef.current = onError
  }, [onError, onSuccess])

  useEffect(() => {
    if (clientId) return

    const controller = new AbortController()
    const loadGoogleConfig = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/google/config`, { signal: controller.signal })
        const data = await response.json().catch(() => ({}))
        if (!response.ok || !data.client_id) {
          throw new Error(data.detail || 'Google innlogging er ikke konfigurert på serveren.')
        }
        setClientId(data.client_id)
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return
        const message = err instanceof Error ? err.message : 'Klarte ikke hente Google-konfigurasjon.'
        setError(message)
        onErrorRef.current?.(message)
      }
    }

    loadGoogleConfig()
    return () => controller.abort()
  }, [clientId])

  const handleCredentialResponse = useCallback(async (response: GoogleCredentialResponse) => {
    setLoading(true)
    setError(null)

    try {
      if (!response.credential) {
        throw new Error('Ingen token mottatt fra Google.')
      }

      const backendResponse = await fetch(
        `${API_BASE_URL}/api/auth/${deferPersistence ? 'google/verify' : 'google'}`,
        {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: response.credential }),
        },
      )
      const userData = await backendResponse.json().catch(() => ({}))
      if (!backendResponse.ok) {
        throw new Error(userData.detail || 'Google-autentisering feilet på serveren.')
      }

      const user: GoogleUser = deferPersistence
        ? { ...userData, credential: response.credential, message: 'Google-identiteten er verifisert.' }
        : userData as GoogleUser
      if (!deferPersistence) {
        window.localStorage.setItem('user', JSON.stringify(user))
      }
      onSuccessRef.current?.(user)
      if (!deferPersistence && redirectTo) router.push(redirectTo)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Google-autentisering feilet.'
      setError(message)
      onErrorRef.current?.(message)
    } finally {
      setLoading(false)
    }
  }, [deferPersistence, redirectTo, router])

  const initializeGoogleButton = useCallback(() => {
    if (!window.google || !googleButtonRef.current || !clientId) return

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: handleCredentialResponse,
      auto_select: false,
    })
    googleButtonRef.current.replaceChildren()
    window.google.accounts.id.renderButton(googleButtonRef.current, {
      type: 'standard',
      shape: 'rectangular',
      theme: 'outline',
      text: 'signin_with',
      size: 'large',
      logo_alignment: 'left',
      width: buttonWidth,
    })
  }, [buttonWidth, clientId, handleCredentialResponse])

  useEffect(() => {
    const element = googleButtonRef.current
    if (!element) return

    const updateWidth = () => {
      const nextWidth = Math.max(200, Math.min(400, Math.floor(element.clientWidth || 320)))
      setButtonWidth((currentWidth) => currentWidth === nextWidth ? currentWidth : nextWidth)
    }

    updateWidth()
    const observer = new ResizeObserver(updateWidth)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!clientId) return

    if (window.google) {
      initializeGoogleButton()
      return
    }

    const existingScript = document.querySelector<HTMLScriptElement>('script[data-google-identity-services]')
    const script = existingScript || document.createElement('script')
    const onLoad = () => initializeGoogleButton()
    const handleScriptError = () => {
      const message = 'Klarte ikke laste Google Sign-In.'
      setError(message)
      onErrorRef.current?.(message)
    }

    script.addEventListener('load', onLoad)
    script.addEventListener('error', handleScriptError)
    if (!existingScript) {
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.defer = true
      script.dataset.googleIdentityServices = 'true'
      document.body.appendChild(script)
    }

    return () => {
      script.removeEventListener('load', onLoad)
      script.removeEventListener('error', handleScriptError)
    }
  }, [clientId, initializeGoogleButton])

  return (
    <div className={className}>
      <div className={disabled ? 'pointer-events-none opacity-50' : ''}>
        <div
          ref={googleButtonRef}
          className="flex w-full justify-center"
          style={{ minHeight: '40px', display: 'flex', alignItems: 'center' }}
        />
      </div>

      {error && (
        <div className="mt-3 bg-rose-50 border-l-4 border-rose-500 text-rose-800 p-3 text-sm rounded-r-lg">
          <p className="font-semibold">Google-innlogging feilet</p>
          <p>{error}</p>
        </div>
      )}

      {loading && <div className="mt-3 text-center text-sm text-stone-600">Verifiserer med Google...</div>}
    </div>
  )
}
