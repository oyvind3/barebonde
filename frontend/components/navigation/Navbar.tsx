'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useIdentity } from '@/lib/identity'

const APP_LINKS = [
  { href: '/dashboard', label: 'Oversikt' },
  { href: '/bilag', label: 'Bilag' },
  { href: '/faktura', label: 'Faktura' },
  { href: '/reports', label: 'Rapporter' },
  { href: '/settings', label: 'Innstillinger' },
]

function roleLabel(role?: string): string {
  if (role === 'owner') return 'Eier'
  if (role === 'manager') return 'Drift'
  if (role === 'staff') return 'Medarbeider'
  return role || 'Medlem'
}

export function Navbar() {
  const { status, identity, activeFarm, logout } = useIdentity()
  const [mobileOpen, setMobileOpen] = useState(false)
  const pathname = usePathname()
  const router = useRouter()

  const membership = identity?.memberships.find((item) => item.farm.id === activeFarm?.id)
  const isAuthenticated = status === 'authenticated' && identity
  const isLoading = status === 'loading'
  const logoHref = isAuthenticated ? '/dashboard' : '/'

  const handleLogout = async () => {
    setMobileOpen(false)
    await logout()
    router.push('/login')
  }

  const closeMobile = () => setMobileOpen(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b border-stone-200 bg-white/95 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Link
            href={logoHref}
            onClick={closeMobile}
            className="rounded-md bg-bonde-green px-3 py-2 text-sm font-bold uppercase tracking-wider text-white"
          >
            🌱 Barebonde
          </Link>

          {isLoading ? (
            <div className="hidden gap-6 lg:flex" aria-hidden="true">
              <span className="h-4 w-16 animate-pulse rounded bg-stone-200" />
              <span className="h-4 w-12 animate-pulse rounded bg-stone-200" />
              <span className="h-4 w-20 animate-pulse rounded bg-stone-200" />
            </div>
          ) : isAuthenticated ? (
            <nav className="hidden gap-6 text-sm font-medium text-stone-700 lg:flex" aria-label="Hovednavigasjon">
              {APP_LINKS.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={pathname === link.href || pathname.startsWith(`${link.href}/`)
                    ? 'font-semibold text-bonde-green'
                    : 'hover:text-bonde-green'}
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          ) : (
            <nav className="hidden gap-6 text-sm font-medium text-stone-700 lg:flex" aria-label="Hovednavigasjon">
              <a href="/#funksjoner" className="hover:text-bonde-green">Funksjoner</a>
              <Link href="/personvern" className="hover:text-bonde-green">Personvern</Link>
              <Link href="/vilkar" className="hover:text-bonde-green">Vilkår</Link>
            </nav>
          )}
        </div>

        <div className="flex items-center gap-3">
          {isLoading ? (
            <div className="flex items-center gap-3" aria-hidden="true">
              <span className="hidden h-4 w-24 animate-pulse rounded bg-stone-200 md:block" />
              <span className="h-9 w-28 animate-pulse rounded-lg bg-stone-200" />
            </div>
          ) : isAuthenticated && identity ? (
            <>
              <div className="hidden text-right text-xs text-stone-600 md:block">
                <p className="font-semibold text-stone-900">{activeFarm?.name || 'Ingen aktiv gård'}</p>
                <p>{roleLabel(membership?.farm_role)} · {identity.subscription?.display_name || 'Ingen plan'}</p>
              </div>
              <details className="relative hidden lg:block">
                <summary className="cursor-pointer list-none rounded-lg border border-stone-200 px-3 py-2 text-sm font-semibold">
                  {identity.user.display_name || identity.user.first_name || identity.user.email} ▾
                </summary>
                <div className="absolute right-0 mt-2 w-52 rounded-lg border border-stone-200 bg-white p-2 shadow-lg">
                  <Link href="/profile" className="block rounded px-3 py-2 hover:bg-stone-50">Min profil</Link>
                  <Link href="/settings" className="block rounded px-3 py-2 hover:bg-stone-50">Kontoinnstillinger</Link>
                  {membership?.farm_role !== 'staff' && (
                    <Link href="/settings/farm" className="block rounded px-3 py-2 hover:bg-stone-50">Gårdsinnstillinger</Link>
                  )}
                  <button onClick={handleLogout} className="w-full rounded px-3 py-2 text-left text-red-700 hover:bg-red-50">
                    Logg ut
                  </button>
                </div>
              </details>
              {/* Mobile menu button */}
              <button
                onClick={() => setMobileOpen(!mobileOpen)}
                aria-label={mobileOpen ? 'Lukk meny' : 'Åpne meny'}
                aria-expanded={mobileOpen}
                className="flex h-11 w-11 items-center justify-center rounded-lg border border-stone-200 text-xl lg:hidden"
              >
                {mobileOpen ? '✕' : '☰'}
              </button>
            </>
          ) : (
            <div className="flex gap-3 text-xs font-bold uppercase">
              <Link href="/login" className="rounded-lg px-4 py-2 hover:bg-stone-100">Logg inn</Link>
              <Link href="/farm/setup" className="rounded-lg bg-bonde-green px-4 py-2 text-white">Kom i gang</Link>
            </div>
          )}
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && isAuthenticated && identity && (
        <nav className="border-t border-stone-200 bg-white px-4 py-3 lg:hidden" aria-label="Mobilmeny">
          <div className="mb-3 border-b border-stone-100 pb-3 text-sm">
            <p className="font-semibold text-stone-900">{activeFarm?.name || 'Ingen aktiv gård'}</p>
            <p className="text-xs text-stone-600">
              {identity.user.display_name || identity.user.first_name || identity.user.email} · {roleLabel(membership?.farm_role)}
            </p>
          </div>
          <ul className="space-y-1">
            {APP_LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  onClick={closeMobile}
                  className={`block rounded-lg px-3 py-3 text-base font-medium ${
                    pathname === link.href || pathname.startsWith(`${link.href}/`)
                      ? 'bg-bonde-light text-bonde-green'
                      : 'text-stone-700 hover:bg-stone-50'
                  }`}
                >
                  {link.label}
                </Link>
              </li>
            ))}
            <li>
              <Link href="/profile" onClick={closeMobile} className="block rounded-lg px-3 py-3 text-base font-medium text-stone-700 hover:bg-stone-50">
                Min profil
              </Link>
            </li>
            {membership?.farm_role !== 'staff' && (
              <li>
                <Link href="/settings/farm" onClick={closeMobile} className="block rounded-lg px-3 py-3 text-base font-medium text-stone-700 hover:bg-stone-50">
                  Gårdsinnstillinger
                </Link>
              </li>
            )}
            <li>
              <button
                onClick={handleLogout}
                className="w-full rounded-lg px-3 py-3 text-left text-base font-medium text-red-700 hover:bg-red-50"
              >
                Logg ut
              </button>
            </li>
          </ul>
        </nav>
      )}
    </header>
  )
}