'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

interface FarmFormData {
  name: string
  org_number: string
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function FarmSetupPage() {
  const router = useRouter()
  const [formData, setFormData] = useState<FarmFormData>({
    name: '',
    org_number: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      if (!/^\d{9}$/.test(formData.org_number)) {
        setError('Organisasjonsnummeret må være 9 sifre')
        setLoading(false)
        return
      }

      await axios.post(
        `${API_BASE_URL}/api/farms`,
        {
          name: formData.name,
          org_number: formData.org_number,
        }
      )

      router.push('/dashboard')
    } catch (err: any) {
      if (err.response?.status === 409) {
        setError('Denne gården er allerede registrert i systemet')
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Feil ved opprettelse av gård. Prøv igjen.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#f3f2fb] via-[#f8f7fd] to-white flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow py-16 px-4">
        <div className="max-w-xl mx-auto">
          <Card hoverEffect={false} className="p-8 sm:p-12 border border-gray-200">
            <div className="text-center mb-8">
              <span className="text-xs font-bold uppercase tracking-widest text-[#43468b] bg-[#e8e7f8] px-3 py-1 mb-3 inline-block">
                Prøveversjon
              </span>
              <h1 className="text-3xl sm:text-4xl font-serif text-gray-900 mb-2">
                Registrer din gård
              </h1>
              <p className="text-gray-600 text-sm">
                Fyll inn gårdsnavn og organisasjonsnummer for å komme i gang.
              </p>
            </div>

            {error && (
              <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 text-sm mb-6">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="name" className="block text-xs font-bold uppercase tracking-wider text-gray-700 mb-2">
                  Gårdsnavn *
                </label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-none focus:outline-none focus:ring-2 focus:ring-[#43468b] text-sm"
                  placeholder="f.eks. Solbakken Gård"
                />
              </div>

              <div>
                <label htmlFor="org_number" className="block text-xs font-bold uppercase tracking-wider text-gray-700 mb-2">
                  Organisasjonsnummer *
                </label>
                <input
                  type="text"
                  id="org_number"
                  name="org_number"
                  value={formData.org_number}
                  onChange={handleInputChange}
                  required
                  maxLength={9}
                  className="w-full px-4 py-3 border border-gray-300 rounded-none focus:outline-none focus:ring-2 focus:ring-[#43468b] text-sm"
                  placeholder="9 siffer (f.eks. 123456789)"
                />
              </div>

              <Button
                type="submit"
                disabled={loading}
                variant="primary"
                fullWidth
                showArrow
              >
                {loading ? 'OPPRETTER GÅRD...' : 'FORTSETT TIL DASHBOARD'}
              </Button>
            </form>
          </Card>
        </div>
      </main>
    </div>
  )
}
            </label>
            <input
              type="text"
              id="org_number"
              name="org_number"
              value={formData.org_number}
              onChange={handleInputChange}
              required
              placeholder="9 sifre (f.eks. 123456789)"
              maxLength={9}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-farm-green focus:border-transparent font-mono"
            />
            <p className="text-sm text-gray-500 mt-1">
              Du finner dette på Brønnøysundregistrene eller skattemelding
            </p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-farm-green text-white py-3 rounded-lg font-semibold hover:bg-opacity-90 transition disabled:opacity-50"
          >
            {loading ? 'Oppretter gård...' : 'Opprett gård'}
          </button>
        </form>

        <p className="text-sm text-gray-500 text-center mt-8">
          Du kan legge til flere gårder og invitere teammedlemmer senere
        </p>
      </div>
    </div>
  )
}
