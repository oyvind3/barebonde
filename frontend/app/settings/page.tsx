'use client'

import { useEffect, useState } from 'react'
import { Navbar } from '@/components/navigation/Navbar'
import { apiErrorMessage, apiFetch } from '@/lib/api'
import Link from 'next/link'

type Session={session_id:string;created_at:string;expires_at:string;current:boolean}

export default function SettingsPage(){
  const[sessions,setSessions]=useState<Session[]>([])
  const[msg,setMsg]=useState('')
  
  const load=()=>
    apiFetch('/api/auth/sessions')
      .then(async r=>r.ok?setSessions(await r.json().then(x=>x.sessions)):setMsg(await apiErrorMessage(r,'Kunne ikke hente sesjoner.')))
  
  useEffect(()=>{load()},[])
  
  const revoke=async(id:string)=>{
    const r=await apiFetch(`/api/auth/sessions/${encodeURIComponent(id)}`,{method:'DELETE'})
    if(!r.ok)return setMsg(await apiErrorMessage(r,'Kunne ikke logge ut enheten.'))
    load()
  }

  return (
    <div className="min-h-screen bg-bonde-oat">
      <Navbar/>
      <main className="mx-auto max-w-4xl p-6">
        <h1 className="text-3xl font-serif">Innstillinger</h1>
        <p className="mt-2 text-sm text-stone-600">
          Administrer din personlige profil og virksomhetsinnstillinger her.
        </p>
        
        {msg && <p className="mt-4 text-sm">{msg}</p>}
        
        {/* Two-column layout for better organization */}
        <div className="mt-8 grid gap-6 md:grid-cols-2">
          {/* Min Profil section */}
          <section className="rounded-xl bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-bonde-light text-lg">👤</span>
              <div>
                <h2 className="text-lg font-semibold text-stone-900">Min profil</h2>
                <p className="text-xs text-stone-500">Personlige innstillinger</p>
              </div>
            </div>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/profile" className="flex items-center justify-between rounded-lg p-3 hover:bg-stone-50 transition-colors">
                  <span>Profilinformasjon</span>
                  <span className="text-stone-400">→</span>
                </Link>
              </li>
              <li>
                <Link href="/settings/security" className="flex items-center justify-between rounded-lg p-3 hover:bg-stone-50 transition-colors">
                  <span>Sikkerhet og pålogging</span>
                  <span className="text-stone-400">→</span>
                </Link>
              </li>
              <li>
                <Link href="/settings/notifications" className="flex items-center justify-between rounded-lg p-3 hover:bg-stone-50 transition-colors">
                  <span>Varslinger</span>
                  <span className="text-stone-400">→</span>
                </Link>
              </li>
            </ul>
          </section>

          {/* Gård / Bedrift section */}
          <section className="rounded-xl bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-bonde-light text-lg">🏡</span>
              <div>
                <h2 className="text-lg font-semibold text-stone-900">Gård / Bedrift</h2>
                <p className="text-xs text-stone-500">Virksomhetsinnstillinger</p>
              </div>
            </div>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/settings/farm" className="flex items-center justify-between rounded-lg p-3 hover:bg-stone-50 transition-colors">
                  <span>Gårdsinnstillinger</span>
                  <span className="text-stone-400">→</span>
                </Link>
              </li>
              <li>
                <Link href="/settings/members" className="flex items-center justify-between rounded-lg p-3 hover:bg-stone-50 transition-colors">
                  <span>Brukere og tilganger</span>
                  <span className="text-stone-400">→</span>
                </Link>
              </li>
              <li>
                <Link href="/settings/bank-accounts" className="flex items-center justify-between rounded-lg p-3 hover:bg-stone-50 transition-colors">
                  <span>Bankkontoer</span>
                  <span className="text-stone-400">→</span>
                </Link>
              </li>
            </ul>
          </section>
        </div>

        {/* Active sessions section - moved below */}
        <section className="mt-8 rounded-xl bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-stone-900">Aktive sesjoner</h2>
          {sessions.length === 0 ? (
            <p className="text-sm text-stone-500">Ingen aktive sesjoner funnet.</p>
          ) : (
            <div className="space-y-3">
              {sessions.map(s => (
                <div key={s.session_id} className="flex items-center justify-between border-b border-stone-100 pb-3 last:border-0">
                  <div className="text-sm">
                    <p className="font-medium text-stone-900">
                      {s.current ? '✓ Denne enheten' : 'Annen enhet'}
                    </p>
                    <p className="text-xs text-stone-500">
                      Utløper {new Date(s.expires_at).toLocaleDateString('nb-NO')}
                    </p>
                  </div>
                  {!s.current && (
                    <button 
                      onClick={() => revoke(s.session_id)}
                      className="rounded px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 transition-colors"
                    >
                      Logg ut
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
