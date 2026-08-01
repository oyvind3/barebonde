'use client'

import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatsBar } from '@/components/ui/StatsBar'
import { Badge } from '@/components/ui/Badge'
import { InteractivePreview } from '@/components/ui/InteractivePreview'

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col bg-bonde-oat font-sans text-stone-900">
      {/* Top Navigation */}
      <Navbar />

      {/* Main Content */}
      <main className="flex-grow">
        {/* Hero Section */}
        <section className="pt-20 pb-16 md:pt-28 md:pb-24 px-4 text-center max-w-5xl mx-auto">
          <Badge variant="purple" className="mb-6">
            Norsk Landbruksplattform
          </Badge>

          <h1 className="text-4xl sm:text-6xl md:text-7xl font-serif text-stone-900 font-normal tracking-tight leading-tight mb-8">
            Mindre papirarbeid. <br className="hidden sm:inline" />
            <span className="text-bonde-green italic">Mer tid til gården.</span>
          </h1>

          <p className="text-lg sm:text-xl md:text-2xl text-stone-700 max-w-3xl mx-auto font-sans font-normal leading-relaxed mb-10">
            Enkel regnskapsføring, automatiske offentlige frister og eSignering av forpaktningsavtaler — alt skreddersydd for norske gardsbruk.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 max-w-md mx-auto mb-16">
            <Button href="/farm/setup" variant="primary" showArrow fullWidth>
              PRØV GRATIS
            </Button>
            <Button href="/dashboard" variant="secondary" showArrow fullWidth>
              SE DEMO
            </Button>
          </div>
        </section>

        {/* Social Proof Stats Bar */}
        <StatsBar />

        {/* Interactive Platform Preview Showcase */}
        <section className="py-16 px-4 max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <Badge variant="purple" className="mb-3">
              Interaktiv Forhåndsvisning
            </Badge>
            <h2 className="text-3xl sm:text-4xl font-serif text-stone-900">
              Innsikt og kontroll på sekunder
            </h2>
          </div>

          <InteractivePreview />
        </section>

        {/* Feature Overview Section */}
        <section className="py-20 px-4 max-w-7xl mx-auto border-t border-stone-200/60">
          <div className="text-center mb-16">
            <Badge variant="purple" className="mb-3">
              Full oversikt på gården
            </Badge>
            <h2 className="text-3xl sm:text-5xl font-serif text-stone-900 mt-2">
              Alt du trenger på én plattform
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <Card>
              <div className="w-12 h-12 rounded-xl bg-bonde-light flex items-center justify-center text-2xl mb-5 text-bonde-green">🌱</div>
              <h3 className="text-xl font-bold font-serif mb-3 text-stone-900">Regnskap & Landbruks-MVA</h3>
              <p className="text-stone-600 text-sm leading-relaxed mb-6">
                Automatisk tolking av bilag fra Felleskjøpet og Tine. Direkte MVA-rapportering skreddersydd for primærnæring.
              </p>
              <Button href="/farm/setup" variant="outline" showArrow>
                LES MER
              </Button>
            </Card>

            <Card>
              <div className="w-12 h-12 rounded-xl bg-amber-100/80 flex items-center justify-center text-2xl mb-5 text-bonde-earth">📜</div>
              <h3 className="text-xl font-bold font-serif mb-3 text-stone-900">Avtaler & BankID Signering</h3>
              <p className="text-stone-600 text-sm leading-relaxed mb-6">
                Enkelt oppsett og eSignering av forpaktningsavtaler, maskinleie og leiekjøring direkte på mobilen.
              </p>
              <Button href="/farm/setup" variant="outline" showArrow>
                LES MER
              </Button>
            </Card>

            <Card>
              <div className="w-12 h-12 rounded-xl bg-emerald-100/80 flex items-center justify-center text-2xl mb-5 text-emerald-800">🚜</div>
              <h3 className="text-xl font-bold font-serif mb-3 text-stone-900">Offentlige Søknader & Frister</h3>
              <p className="text-stone-600 text-sm leading-relaxed mb-6">
                Full kalendersynk for produksjonstilskudd, avløsertilskudd og kommunale jordlovssøknader.
              </p>
              <Button href="/farm/setup" variant="outline" showArrow>
                LES MER
              </Button>
            </Card>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-bonde-dark text-stone-200 py-12 border-t border-stone-800 text-sm">
        <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center space-x-3">
            <span className="bg-bonde-green text-white font-bold px-3 py-1 text-xs uppercase rounded">🌱 Barebonde</span>
            <span className="text-stone-400">© 2026 Barebonde AS. Enkel og varm landbruksplattform.</span>
          </div>
          <div className="flex space-x-6 text-stone-400">
            <a href="#" className="hover:text-white transition">Vilkår</a>
            <a href="#" className="hover:text-white transition">Personvern</a>
            <a href="#" className="hover:text-white transition">Kontakt oss</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
    </div>
  )
}
