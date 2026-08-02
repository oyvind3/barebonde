'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    if (!email || !password) {
      setError('Vennligst oppgi e-postadresse og passord.')
      setLoading(false)
      return
    }

    // Simulate login / authenticate demo user
    setTimeout(() => {
      setLoading(false)
      router.push('/dashboard')
    }, 600)
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
                Logg inn med din e-postadresse og passord for å få tilgang til gården din.
              </p>
            </div>

            {error && (
              <div className="bg-rose-50 border-l-4 border-rose-500 text-rose-800 p-4 text-sm rounded-r-lg mb-6">
                {error}
              </div>
            )}

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

              <div>
                <div className="flex justify-between items-center mb-2">
                  <label htmlFor="password" className="block text-xs font-bold uppercase tracking-wider text-stone-700">
                    Passord *
                  </label>
                  <a href="#" className="text-xs text-bonde-green hover:underline">Glemt passord?</a>
                </div>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
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
                {loading ? 'LOGGER INN...' : 'LOGG INN'}
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