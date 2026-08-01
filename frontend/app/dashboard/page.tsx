'use client'

import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#f3f2fb] via-[#f8f7fd] to-white flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full">
        {/* Dashboard Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 pb-6 border-b border-gray-200">
          <div>
            <span className="text-xs font-bold uppercase tracking-widest text-[#43468b] bg-[#e8e7f8] px-3 py-1 mb-2 inline-block">
              Gårdsoversikt
            </span>
            <h1 className="text-3xl sm:text-4xl font-serif text-gray-900">
              Dashboard (Prøveversjon)
            </h1>
            <p className="text-gray-600 text-sm mt-1">
              Velkommen til Barebonde sin digitale plattform for gårdsdrift.
            </p>
          </div>

          <div className="mt-4 md:mt-0 flex gap-3">
            <Button href="/farm/setup" variant="outline" showArrow>
              ENDRE GÅRD
            </Button>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          <Card hoverEffect={false} className="p-6 border-l-4 border-l-[#43468b]">
            <p className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Totale utgifter (12 mnd)</p>
            <p className="text-3xl font-serif text-gray-900 font-bold">kr 0</p>
          </Card>

          <Card hoverEffect={false} className="p-6 border-l-4 border-l-[#43468b]">
            <p className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Kommende frister</p>
            <p className="text-3xl font-serif text-gray-900 font-bold">0</p>
          </Card>

          <Card hoverEffect={false} className="p-6 border-l-4 border-l-[#43468b]">
            <p className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Aktive avtaler</p>
            <p className="text-3xl font-serif text-gray-900 font-bold">0</p>
          </Card>

          <Card hoverEffect={false} className="p-6 border-l-4 border-l-[#43468b]">
            <p className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Registrerte brukere</p>
            <p className="text-3xl font-serif text-gray-900 font-bold">1</p>
          </Card>
        </div>

        {/* Demo info banner */}
        <Card hoverEffect={false} className="p-8 border border-blue-200 bg-blue-50/50 mb-10">
          <div className="flex items-start space-x-4">
            <span className="text-2xl">ℹ️</span>
            <div>
              <h3 className="text-base font-bold text-blue-900 uppercase tracking-wide mb-1">
                Åpen prøveversjon er aktiv
              </h3>
              <p className="text-sm text-blue-800 leading-relaxed">
                Full automatisk e-ID innlogging (ID-porten) og direkte synkronisering mot landbruksdirektoratet, Peppol/EHF og BRREG er under utvikling.
              </p>
            </div>
          </div>
        </Card>
      </main>
    </div>
  )
}
