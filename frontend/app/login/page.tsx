'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { apiFetch, rememberCsrfToken } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('token')
    if (!token) return

    const completeMagicLinkLogin = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await apiFetch('/api/auth/magic-link/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        })
        const data = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(data.detail || 'Innloggingslenken kunne ikke brukes.')
        rememberCsrfToken(data.csrf_token)
        router.replace('/dashboard')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Innloggingslenken kunne ikke brukes.')
      } finally {
        setLoading(false)
      }
    }

    completeMagicLinkLogin()
  }, [router])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    if (!email) {
      setError('Vennligst oppgi e-postadressen din.')
      setLoading(false)
      return
    }
    try {
      const response = await apiFetch('/api/auth/magic-link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.detail || 'Kunne ikke sende innloggingslenken.')
      setMessage(data.message || 'Innloggingslenke sendt på e-post.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kunne ikke sende innloggingslenken.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow py-16 px-4 flex items-center justify-center">
        <div className="w-full max-w-md">
          <Card hoverEffect={false} className="p-8 sm:p-10 border border-stone-200/80 rounded-2xl shadow-card bg-white">
            <div className="text-center mb-8">
              <span className="text-xs font-bold uppercase tracking-widest text-bonde-green bg-bonde-light px-3 py-1 rounded-full mb-3 inline-block">
                Logg inn
              </span>
              <h1 className="text-3xl font-serif text-stone-900 mb-2">
                Velkommen tilbake
              </h1>
              <p className="text-stone-600 text-sm">
                Få en sikker engangslenke på e-post.
              </p>
            </div>

            {error && (
              <div className="bg-rose-50 border-l-4 border-rose-500 text-rose-800 p-4 text-sm rounded-r-lg mb-6">
                {error}
              </div>
            )}
            {message && (
              <div className="bg-emerald-50 border-l-4 border-emerald-500 text-emerald-800 p-4 text-sm rounded-r-lg mb-6">
                {message}
              </div>
            )}

            {/* E-mail one-time-link form */}
            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label htmlFor="email" className="block text-xs font-bold uppercase tracking-wider text-stone-700 mb-2">
                  E-postadresse *
                </label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="ola@norskbonde.no"
                  className="w-full px-4 py-3 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-bonde-green text-sm bg-white"
                />
              </div>

              <Button
                type="submit"
                disabled={loading}
                variant="primary"
                fullWidth
                showArrow
              >
                {loading ? 'SENDER...' : 'SEND INNLOGGINGSLENKE'}
              </Button>
            </form>

            <div className="mt-8 pt-6 border-t border-stone-100 text-center">
              <p className="text-xs text-stone-600">
                Har du ikke en konto ennå?{' '}
                <Link href="/farm/setup" className="font-bold text-bonde-green hover:underline">
                  Prøv gratis i 30 dager
                </Link>
              </p>
            </div>
          </Card>
        </div>
      </main>
    </div>
  )
}
