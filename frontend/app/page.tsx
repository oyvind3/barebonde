'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    // Check if user is logged in
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token')
      if (token) {
        // User is logged in - redirect to dashboard
        router.push('/dashboard')
      }
      setIsLoading(false)
    }

    checkAuth()
  }, [router])

  const handleLogin = async () => {
    try {
      const response = await fetch('/api/auth/login')
      const data = await response.json()
      // Redirect to ID-porten
      if (data.login_url) {
        window.location.href = data.login_url
      }
    } catch (error) {
      console.error('Login error:', error)
    }
  }

  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen">Laster...</div>
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-farm-light to-white">
      <div className="max-w-4xl mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-farm-green mb-4">Barebonde</h1>
          <p className="text-xl text-gray-600 mb-2">Regnskapssystem for norske bønder</p>
          <p className="text-gray-500">Enkel administrasjon av økonomi, avtaler og frister</p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 mb-12">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-farm-green mb-2">💰 Regnskap</h3>
            <p className="text-gray-600">Oversikt over inntekter og utgifter</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-farm-green mb-2">📄 Avtaler</h3>
            <p className="text-gray-600">Digitalisering av kontrakter og signering</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-farm-green mb-2">⏰ Frister</h3>
            <p className="text-gray-600">Aldri miste viktige skatte- og tilskuddsfrister</p>
          </div>
        </div>

        <div className="text-center">
          <button
            onClick={handleLogin}
            className="bg-farm-green text-white px-8 py-3 rounded-lg text-lg font-semibold hover:bg-opacity-90 transition"
          >
            Logg inn med ID-porten
          </button>
        </div>
      </div>
    </main>
  )
}
