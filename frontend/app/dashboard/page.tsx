'use client'

import Link from 'next/link'

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-6xl mx-auto px-4 py-6 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-farm-green">Dashboard</h1>
            <p className="text-gray-600">Velkommen til Barebonde (Prøveversjon)</p>
          </div>
          <Link
            href="/"
            className="bg-gray-200 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-300 transition"
          >
            Hjem
          </Link>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-sm text-gray-500">Totale utgifter (12 mnd)</p>
            <p className="text-2xl font-bold text-farm-green">kr 0</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-sm text-gray-500">Kommende frister</p>
            <p className="text-2xl font-bold text-farm-green">0</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-sm text-gray-500">Avtaler</p>
            <p className="text-2xl font-bold text-farm-green">0</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <p className="text-sm text-gray-500">Brukere</p>
            <p className="text-2xl font-bold text-farm-green">1</p>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-8">
          <p className="text-blue-800">
            ℹ️ Åpen prøveversjon active. Full e-ID innlogging og automatisk regnskap videreutvikles.
          </p>
        </div>
      </div>
    </div>
  )
}
