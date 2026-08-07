'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { InteractivePreview } from '@/components/ui/InteractivePreview'
import { useIdentity } from '@/lib/identity'

export default function Home() {
  const { status, activeFarm } = useIdentity()
  const router = useRouter()

  // Authenticated users go straight to the app, never via the marketing page
  useEffect(() => {
    if (status === 'authenticated') {
      router.replace(activeFarm ? '/dashboard' : '/farm/setup')
    }
  }, [status, activeFarm, router])

  // While session status is unknown: calm branded loading state, no public UI
  if (status === 'loading' || status === 'authenticated') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-bonde-oat px-4">
        <span className="mb-4 rounded-md bg-bonde-green px-4 py-2 text-lg font-bold uppercase tracking-wider text-white">
          🌱 Barebonde
        </span>
        <p className="text-stone-600" role="status">Henter gården din …</p>
        {status === 'authenticated' && (
          <p className="mt-2 text-sm text-stone-500">Videresender …</p>
        )}
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-bonde-oat font-sans text-stone-900">
      <Navbar />

      <main className="flex-grow">
        {/* Hero */}
        <section className="pt-20 pb-16 md:pt-28 md:pb-24 px-4 text-center max-w-5xl mx-auto">
          <p className="mx-auto mb-6 inline-block rounded-full border border-bonde-green/30 bg-bonde-light px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-bonde-green">
            Pilot · Gratis i pilotperioden
          </p>
          <h1 className="text-4xl sm:text-6xl md:text-7xl font-serif text-stone-900 font-normal tracking-tight leading-tight mb-8">
            Mindre papirarbeid. <br className="hidden sm:inline" />
            <span className="text-bonde-green italic">Mer tid til gården.</span>
          </h1>

          <p className="text-lg sm:text-xl md:text-2xl text-stone-700 max-w-3xl mx-auto font-sans font-normal leading-relaxed mb-6">
            Bilagsregistrering og enkel økonomioversikt for norsk landbruk. Last opp fakturaer,
            kontroller OCR-forslag og bokfør — alt tilpasset norsk landbruk.
          </p>
          <p className="text-sm text-stone-600 max-w-2xl mx-auto mb-10">
            Du blir ikke belastet i pilotperioden. Vi varsler før eventuell betalt lansering.
            Løsningen er under utvikling og erstatter foreløpig ikke et ordinært regnskapssystem.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 max-w-md mx-auto mb-16">
            <Button href="/farm/setup" variant="primary" showArrow fullWidth>
              KOM I GANG GRATIS
            </Button>
            <Button href="/login" variant="secondary" showArrow fullWidth>
              LOGG INN
            </Button>
          </div>
        </section>

        {/* Honest value bar */}
        <section className="w-full border-y border-stone-200/60 bg-bonde-oat/50 py-12">
          <div className="mx-auto grid max-w-6xl grid-cols-2 gap-8 px-4 text-center md:grid-cols-4">
            <div className="flex flex-col items-center">
              <span className="text-2xl font-bold font-sans text-bonde-green tracking-tight md:text-3xl">🇳🇴 Norsk landbruk</span>
              <span className="mt-2 text-xs font-semibold uppercase tracking-wider text-stone-600">Utviklet for</span>
            </div>
            <div className="flex flex-col items-center">
              <span className="text-2xl font-bold font-sans text-bonde-green tracking-tight md:text-3xl">OCR-forslag</span>
              <span className="mt-2 text-xs font-semibold uppercase tracking-wider text-stone-600">Leser norske fakturaer</span>
            </div>
            <div className="flex flex-col items-center">
              <span className="text-2xl font-bold font-sans text-bonde-green tracking-tight md:text-3xl">Brønnøysund</span>
              <span className="mt-2 text-xs font-semibold uppercase tracking-wider text-stone-600">Henter foretaksdata</span>
            </div>
            <div className="flex flex-col items-center">
              <span className="text-2xl font-bold font-sans text-bonde-green tracking-tight md:text-3xl">Pilot</span>
              <span className="mt-2 text-xs font-semibold uppercase tracking-wider text-stone-600">Gratis med pilotbrukere</span>
            </div>
          </div>
        </section>

        {/* Preview */}
        <section className="py-16 px-4 max-w-6xl mx-auto">
          <div className="text-center mb-4">
            <h2 className="text-3xl sm:text-4xl font-serif text-stone-900">
              Slik ser det ut på gården
            </h2>
          </div>
          <p className="mb-8 text-center text-sm text-stone-600">
            Konseptvisning – enkelte funksjoner er under utvikling.
          </p>
          <InteractivePreview />
        </section>

        {/* Features */}
        <section id="funksjoner" className="py-20 px-4 max-w-7xl mx-auto border-t border-stone-200/60">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-5xl font-serif text-stone-900">
              Bilag og økonomioversikt
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <Card>
              <div className="w-12 h-12 rounded-xl bg-bonde-light flex items-center justify-center text-2xl mb-5 text-bonde-green">🌱</div>
              <h3 className="text-xl font-bold font-serif mb-3 text-stone-900">Bilag & OCR</h3>
              <p className="text-stone-600 text-sm leading-relaxed mb-6">
                Last opp PDF eller bilde av fakturaen. OCR leser leverandør, beløp og dato som forslag —
                du kontrollerer og bokfører.
              </p>
              <Button href="/farm/setup" variant="outline" showArrow>
                KOM I GANG
              </Button>
            </Card>

            <Card>
              <div className="w-12 h-12 rounded-xl bg-amber-100/80 flex items-center justify-center text-2xl mb-5 text-bonde-earth">📊</div>
              <h3 className="text-xl font-bold font-serif mb-3 text-stone-900">Økonomioversikt</h3>
              <p className="text-stone-600 text-sm leading-relaxed mb-6">
                Enkel oversikt over inntekter, kostnader og estimert MVA basert på registrerte bilag.
                Foreløpig oversikt — erstatter ikke ordinær regnskapsføring.
              </p>
              <Button href="/farm/setup" variant="outline" showArrow>
                KOM I GANG
              </Button>
            </Card>

            <Card>
              <div className="w-12 h-12 rounded-xl bg-emerald-100/80 flex items-center justify-center text-2xl mb-5 text-emerald-800">🚜</div>
              <h3 className="text-xl font-bold font-serif mb-3 text-stone-900">Mer fremover</h3>
              <p className="text-stone-600 text-sm leading-relaxed mb-6">
                Frister, avtaler og flere integrasjoner er under utvikling. Pilotbrukere får tilgang
                etter hvert som funksjonene blir klare.
              </p>
              <span className="inline-block rounded-lg border border-stone-200 px-4 py-2 text-xs font-bold uppercase text-stone-400">
                Kommer senere
              </span>
            </Card>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-bonde-dark text-stone-300 py-10 border-t border-stone-800 text-sm">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center space-x-3">
            <span className="bg-bonde-green text-white font-bold px-3 py-1 text-xs uppercase rounded">🌱 Barebonde</span>
            <span className="text-stone-400 text-xs">© 2026 Barebonde · Pilot</span>
          </div>
          <div className="flex space-x-6 text-xs text-stone-400">
            <Link href="/vilkar" className="hover:text-white transition">Vilkår</Link>
            <Link href="/personvern" className="hover:text-white transition">Personvern</Link>
            <Link href="/kontakt" className="hover:text-white transition">Kontakt</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}