import Link from 'next/link'

export const metadata = {
  title: 'Personvern – Barebonde',
  description: 'Hvordan Barebonde behandler personopplysninger og regnskapsdata.',
}

export default function PersonvernPage() {
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
        <h1 className="mb-8 text-3xl font-serif text-stone-900">Personvernerklæring</h1>

        <div className="space-y-8 text-sm leading-relaxed text-stone-700">
          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">1. Behandlingsansvarlig</h2>
            <p>
              Barebonde er behandlingsansvarlig for personopplysninger som behandles i tjenesten.
              Spørsmål om personvern kan rettes til kontaktsiden.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">2. Hvilke opplysninger vi behandler</h2>
            <ul className="list-disc space-y-2 pl-5">
              <li>Kontodata: navn, e-postadresse og passordhash eller innloggingsmetode.</li>
              <li>Gårds- og medlemskapsdata: gårdsnavn, organisasjonsnummer og roller.</li>
              <li>Bilagsdata: opplastede dokumenter (PDF/bilde) og registrerte bilagsfelter.</li>
              <li>Tekniske data: sesjonsinformasjon og grunnleggende bruksmønster for drift og sikkerhet.</li>
            </ul>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">3. Formål</h2>
            <p>
              Opplysningene brukes til å levere tjenesten: autentisering, bilagsregistrering,
              OCR-behandling og økonomioversikt for gården. Vi behandler ikke data for
              markedsføringsformål og selger ikke data til tredjeparter.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">4. Lagring og sikkerhet</h2>
            <p>
              Data lagres i Azure (Cosmos DB og Blob Storage) innenfor EØS-området.
              Tilgang krever gyldig sesjon, og følsomme operasjoner er beskyttet med CSRF-token.
              Passord lagres kun som hash. Opplastede bilag lagres kryptert i Blob Storage.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">5. Dine rettigheter</h2>
            <p>
              Du har rett til innsyn, retting og sletting av egne opplysninger i henhold til
              personvernforordningen (GDPR). Sletting av en gård sletter tilknyttede bilag og
              medlemskap. Kontakt oss via kontaktsiden for forespørsler.
            </p>
          </section>

          <section>
            <h2 className="mb-3 text-xl font-serif text-stone-900">6. Endringer</h2>
            <p>
              Denne erklæringen kan bli oppdatert. Vesentlige endringer varsles i tjenesten
              før de trer i kraft.
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