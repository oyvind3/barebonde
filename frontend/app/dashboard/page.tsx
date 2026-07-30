'use client'

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-farm-green mb-8">Dashboard</h1>
        
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

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-8">
          <p className="text-yellow-800">
            ℹ️ Velkomst! Denne er den første versjonen av Barebonde. 
            Mer funksjonalitet kommer snart.
          </p>
        </div>
      </div>
    </div>
  )
}
