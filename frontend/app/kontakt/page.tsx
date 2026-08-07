import Link from 'next/link'

export const metadata = {
  title: 'Kontakt – Barebonde',
  description: 'Kontakt Barebonde-teamet.',
}

export default function KontaktPage() {
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

      <main className="mx-auto w-full max-w-2xl flex-grow px-4 py-12">
        <h1 className="mb-4 text-3xl font-serif text-stone-900">Kontakt oss</h1>
        <p className="mb-8 text-sm leading-relaxed text-stone-700">
          Barebonde er i pilotfase, og vi setter pris på tilbakemeldinger fra brukerne.
          Har du spørsmål, feilrapporter eller forslag til forbedringer, ta kontakt.
        </p>

        <div className="space-y-4">
          <div className="rounded-xl border border-stone-200 bg-white p-6">
            <h2 className="mb-2 text-lg font-serif text-stone-900">E-post</h2>
            <p className="text-sm text-stone-700">
              <a href="mailto:kontakt@barebonde.no" className="font-medium text-bonde-green hover:underline">
                kontakt@barebonde.no
              </a>
            </p>
            <p className="mt-1 text-xs text-stone-500">Vi svarer normalt innen 2 virkedager.</p>
          </div>

          <div className="rounded-xl border border-stone-200 bg-white p-6">
            <h2 className="mb-2 text-lg font-serif text-stone-900">Feil og sikkerhet</h2>
            <p className="text-sm text-stone-700">
              Oppdaget du en sikkerhetssårbarhet? Send en beskrivelse til e-postadressen over
              med «sikkerhet» i emnefeltet. Ikke del sensitiv data i første henvendelse.
            </p>
          </div>

          <div className="rounded-xl border border-stone-200 bg-white p-6">
            <h2 className="mb-2 text-lg font-serif text-stone-900">Pilotbrukere</h2>
            <p className="text-sm text-stone-700">
              Som pilotbruker kan du melde ønsker og feil direkte. Tilbakemeldinger brukes
              aktivt til å prioritere videre utvikling.
            </p>
          </div>
        </div>
      </main>

      <footer className="border-t border-stone-200 bg-white py-6 text-center text-xs text-stone-500">
        © 2026 Barebonde · Pilot
      </footer>
    </div>
  )
}