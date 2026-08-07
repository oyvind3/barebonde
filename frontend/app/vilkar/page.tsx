import Link from 'next/link'

export const metadata = {
  title: 'Vilkår – Barebonde',
  description: 'Brukervilkår for Barebonde pilot.',
}

export default function VilkarPage() {
  return (
    <div className="min-h-screen flex flex-col bg-bonde-oat font-sans text-stone-900">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between px-4">
          <Link href="/" className="rounded-md bg-bonde-green px-3 py-2 text-sm font-bold uppercase tracking-wider text-white">
            🌱 Barebonde
          </Link>
          <Link href="/" className="text-sm text-stone-600 hover:text-bonde-green">← Tilbake</Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-grow px-4 py-12">
        <h1 className="mb-8 text-3xl font-serif text-stone-900">Brukervilkår</h1>

        <div className="space-y-8 text-sm leading-relaxed text-stone-700">
          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">1. Pilotperiode</h2>
            <p>
              Barebonde er i en pilotfase og tilbys gratis til pilotbrukere. Tjenesten er under
              aktiv utvikling, og funksjonalitet kan endres, utvides eller fjernes mellom versjoner.
              Vi varsler før eventuell betalt lansering.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">2. Tjenestens omfang</h2>
            <p>
              Barebonde tilbyr bilagsregistrering med OCR-støtte og enkel økonomioversikt.
              Tjenesten er foreløpig ikke et komplett regnskapssystem og erstatter ikke
              lovpålagt regnskapsføring, MVA-innsending eller revisjon.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">3. Brukerens ansvar</h2>
            <p>
              Brukeren er ansvarlig for at registrerte opplysninger er korrekte, og for at
              bokførte bilag kontrolleres før de brukes som grunnlag for regnskapsrapportering.
              OCR-forslag er alltid forslag som skal bekreftes av brukeren.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">4. Tilgjengelighet</h2>
            <p>
              Vi arbeider for god tilgjengelighet, men gir ingen garanti for uavbrutt drift i
              pilotperioden. Planlagt vedlikehold varsles så langt det er praktisk mulig.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">5. Ansvarsbegrensning</h2>
            <p>
              Barebonde er ikke ansvarlig for indirekte tap, tapte inntekter eller krav fra
              tredjepart som følge av bruk av tjenesten, med mindre tapet skyldes forsett
              eller grov uaktsomhet fra vår side.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">6. Oppsigelse og sletting</h2>
            <p>
              Du kan når som helst slutte å bruke tjenesten. Sletting av gården i innstillingene
              fjerner tilknyttede data. Vi kan avslutte pilottilgang med rimelig varsel.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">7. Endringer</h2>
            <p>
              Vilkårene kan oppdateres i takt med tjenestens utvikling. Fortsatt bruk etter
              vesentlige endringer anses som aksept av de nye vilkårene.
            </p>
          </section>
        </div>
      </main>

      <footer className="border-t border-stone-200 bg-white py-6 text-center text-xs text-stone-500">
        © 2026 Barebonde · Pilot
      </footer>
    </div>
  )
}