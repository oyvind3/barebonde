'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { apiFetch, bootstrapIdentity, IdentityBootstrap, rememberCsrfToken } from '@/lib/api'

export function Navbar() {
  const [identity, setIdentity] = useState<IdentityBootstrap | null>(null)

  useEffect(() => { bootstrapIdentity().then(setIdentity).catch(() => setIdentity(null)) }, [])
  const membership = identity?.memberships.find((item) => item.farm.id === identity.active_farm?.id)
  const logout = async () => {
    await apiFetch('/api/auth/logout', { method: 'POST' }).catch(() => undefined)
    rememberCsrfToken('')
    window.location.assign('/login')
  }

  return <header className="sticky top-0 z-50 w-full border-b border-stone-200 bg-white/95 backdrop-blur-md">
    <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6">
      <div className="flex items-center gap-7">
        <Link href="/" className="rounded-md bg-bonde-green px-3 py-2 text-sm font-bold uppercase tracking-wider text-white">🌱 Barebonde</Link>
        <nav className="hidden gap-6 text-sm font-medium text-stone-700 lg:flex"><Link href="/dashboard">Dashboard</Link><Link href="/bilag">Bilag</Link><Link href="/reports">Rapporter</Link></nav>
      </div>
      {identity ? <div className="flex items-center gap-3">
        <div className="hidden text-right text-xs text-stone-600 md:block"><p className="font-semibold text-stone-900">{identity.active_farm?.name || 'Ingen aktiv gård'}</p><p>{membership?.farm_role === 'owner' ? 'Eier' : membership?.farm_role || 'Medlem'} · {identity.subscription?.display_name || 'Ingen plan'}</p></div>
        <details className="relative"><summary className="cursor-pointer rounded-lg border border-stone-200 px-3 py-2 text-sm font-semibold">{identity.user.display_name || identity.user.first_name || identity.user.email} ▾</summary><div className="absolute right-0 mt-2 w-52 rounded-lg border border-stone-200 bg-white p-2 shadow-lg"><Link href="/profile" className="block rounded px-3 py-2 hover:bg-stone-50">Min profil</Link><Link href="/settings" className="block rounded px-3 py-2 hover:bg-stone-50">Kontoinnstillinger</Link>{membership?.farm_role !== 'staff' && <Link href="/settings/farm" className="block rounded px-3 py-2 hover:bg-stone-50">Gårdsinnstillinger</Link>}<button onClick={logout} className="w-full rounded px-3 py-2 text-left text-red-700 hover:bg-red-50">Logg ut</button></div></details>
      </div> : <div className="flex gap-4 text-xs font-bold uppercase"><Link href="/login">Logg inn</Link><Link href="/farm/setup" className="rounded-lg bg-bonde-green px-4 py-2 text-white">Prøv gratis</Link></div>}
    </div>
  </header>
}
