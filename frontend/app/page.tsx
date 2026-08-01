'use client'

import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { StatsBar } from '@/components/ui/StatsBar'

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-[#f3f2fb] via-[#f8f7fd] to-white font-sans text-gray-900">
      {/* Top Navigation */}
      <Navbar />

      {/* Main Content */}
      <main className="flex-grow">
        {/* Hero Section */}
        <section className="pt-20 pb-16 md:pt-28 md:pb-24 px-4 text-center max-w-5xl mx-auto">
          <h1 className="text-4xl sm:text-6xl md:text-7xl font-serif text-gray-900 font-normal tracking-tight leading-tight mb-8">
            Se gårdens regnskap og verditall
          </h1>

          <p className="text-lg sm:text-xl md:text-2xl text-gray-700 max-w-3xl mx-auto font-sans font-normal leading-relaxed mb-10">
            Ikke gå inn i gårdsoppgjøret i blinde. Se hva regnskapet, avtalene og fristene krever før du beslutter.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 max-w-md mx-auto mb-16">
            <Button href="/farm/setup" variant="primary" showArrow fullWidth>
              PRØV GRATIS
            </Button>
            <Button href="/dashboard" variant="secondary" showArrow fullWidth>
              SE VIDEO
            </Button>
          </div>
        </section>

        {/* Social Proof Stats Bar */}
        <StatsBar />

        {/* Feature Overview Section */}
        <section className="py-20 px-4 max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <span className="text-xs font-bold uppercase tracking-widest text-[#43468b] bg-[#e8e7f8] px-3 py-1 mb-4 inline-block">
              Full kontroll på gården
            </span>
            <h2 className="text-3xl sm:text-5xl font-serif text-gray-900 mt-2">
              Alt du trenger på én plattform
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <Card>
              <div className="text-3xl mb-4">💰</div>
              <h3 className="text-xl font-bold font-serif mb-3 text-gray-900">Regnskap & Bilag</h3>
              <p className="text-gray-600 text-sm leading-relaxed mb-6">
                Automatisk håndtering av landbruksspesifikke MVA-satser, bilagsføring og oversikt over inntekter og utgifter.
              </p>
              <Button href="/farm/setup" variant="outline" showArrow>
                LES MER
              </Button>
            </Card>

            <Card>
              <div className="text-3xl mb-4">📄</div>
              <h3 className="text-xl font-bold font-serif mb-3 text-gray-900">Avtaler & Signering</h3>
              <p className="text-gray-600 text-sm leading-relaxed mb-6">
                Digitaliser forpaktningsavtaler, maskinleie og leverandørkontrakter med trygg digital eSignering.
              </p>
              <Button href="/farm/setup" variant="outline" showArrow>
                LES MER
              </Button>
            </Card>

            <Card>
              <div className="text-3xl mb-4">⏰</div>
              <h3 className="text-xl font-bold font-serif mb-3 text-gray-900">Offentlige Frister</h3>
              <p className="text-gray-600 text-sm leading-relaxed mb-6">
                Automatisk varsling for produksjonstilskudd, mva-meldinger og skattefrister rett til din kalender.
              </p>
              <Button href="/farm/setup" variant="outline" showArrow>
                LES MER
              </Button>
            </Card>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12 border-t border-gray-800 text-sm">
        <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center space-x-3">
            <span className="bg-white text-black font-bold px-3 py-1 text-xs uppercase">Barebonde</span>
            <span className="text-gray-400">© 2026 Barebonde AS. Norsk landbruksplattform.</span>
          </div>
          <div className="flex space-x-6 text-gray-400">
            <a href="#" className="hover:text-white transition">Vilkår</a>
            <a href="#" className="hover:text-white transition">Personvern</a>
            <a href="#" className="hover:text-white transition">Kontakt oss</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
