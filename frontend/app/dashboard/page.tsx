'use client'

import { Navbar } from '@/components/navigation/Navbar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-bonde-oat flex flex-col font-sans">
      <Navbar />

      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 py-10 w-full">
        {/* Dashboard Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 pb-6 border-b border-stone-200/80">
          <div>
            <span className="text-xs font-bold uppercase tracking-widest text-bonde-green bg-bonde-light px-3 py-1 rounded-full mb-2 inline-block">
              Gårdsoversikt
            </span>
            <h1 className="text-3xl sm:text-4xl font-serif text-stone-900">
              Gårdens kontrollpanel
            </h1>
            <p className="text-stone-600 text-sm mt-1">
              Velkommen til Barebonde — enkel og oversiktlig administrasjon av gårdsdriften.
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
          <Card hoverEffect={false} className="p-6 border-l-4 border-l-bonde-green bg-white">
            <p className="text-xs font-bold uppercase tracking-wider text-stone-600 mb-1">Driftsinntekter MHI</p>
            <p className="text-3xl font-serif text-stone-900 font-bold">kr 842 500</p>
            <p className="text-xs text-emerald-700 mt-1 font-medium">↑ Synkronisert med Tine/FK</p>
          </Card>

          <Card hoverEffect={false} className="p-6 border-l-4 border-l-bonde-green bg-white">
            <p className="text-xs font-bold uppercase tracking-wider text-stone-600 mb-1">MVA-Melding Frist</p>
            <p className="text-3xl font-serif text-bonde-green font-bold">10. Aug</p>
            <p className="text-xs text-stone-600 mt-1">Klargjort for Altinn</p>
          </Card>

          <Card hoverEffect={false} className="p-6 border-l-4 border-l-bonde-green bg-white">
            <p className="text-xs font-bold uppercase tracking-wider text-stone-600 mb-1">Forpaktningsavtaler</p>
            <p className="text-3xl font-serif text-stone-900 font-bold">3</p>
            <p className="text-xs text-emerald-700 mt-1 font-medium">✓ eSignert med BankID</p>
          </Card>

          <Card hoverEffect={false} className="p-6 border-l-4 border-l-bonde-green bg-white">
            <p className="text-xs font-bold uppercase tracking-wider text-stone-600 mb-1">Aktive brukere</p>
            <p className="text-3xl font-serif text-stone-900 font-bold">2</p>
            <p className="text-xs text-stone-600 mt-1">Gårdbruker & Regnskapsfører</p>
          </Card>
        </div>

        {/* Demo info banner */}
        <Card hoverEffect={false} className="p-8 border border-amber-200/80 bg-amber-50/60 rounded-2xl mb-10">
          <div className="flex items-start space-x-4">
            <span className="text-2xl">🌱</span>
            <div>
              <h3 className="text-base font-bold text-stone-900 uppercase tracking-wide mb-1">
                Demonavigasjon er aktiv
              </h3>
              <p className="text-sm text-stone-700 leading-relaxed">
                ID-porten innlogging og direktekobling mot Landbruksdirektoratet, Peppol/EHF, ELMA og Altinn er under klargjøring for produksjon.
              </p>
            </div>
          </div>
        </Card>
      </main>
    </div>
  )
}
