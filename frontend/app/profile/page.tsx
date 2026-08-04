'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Navbar } from '@/components/navigation/Navbar'
import { apiErrorMessage, apiFetch } from '@/lib/api'

type Profile = { email: string; email_verified: boolean; first_name: string; last_name: string; display_name: string; phone_number?: string; preferred_language: string; timezone: string; profile_completed: boolean; terms_accepted_at?: string; privacy_accepted_at?: string }

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null); const [message, setMessage] = useState('')
  useEffect(() => { apiFetch('/api/profile').then(async r => r.ok ? setProfile(await r.json()) : setMessage(await apiErrorMessage(r, 'Kunne ikke hente profilen.'))).catch(() => setMessage('Kunne ikke hente profilen.')) }, [])
  const save = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); const response = await apiFetch('/api/profile', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); if (!response.ok) return setMessage(await apiErrorMessage(response, 'Kunne ikke lagre profilen.')); setProfile(await response.json()); setMessage('Profilen er lagret.') }
  return <div className="min-h-screen bg-bonde-oat"><Navbar /><main className="mx-auto max-w-2xl p-6"><h1 className="text-3xl font-serif">Min profil</h1>{message && <p className="mt-4 text-sm text-stone-700">{message}</p>}{profile && <form onSubmit={save} className="mt-6 space-y-4 rounded-xl bg-white p-6 shadow-sm"><label className="block text-sm">E-post (kan ikke endres)<input disabled value={profile.email} className="mt-1 w-full rounded border p-2 text-stone-500" /></label><label className="block text-sm">Fornavn<input name="first_name" defaultValue={profile.first_name} className="mt-1 w-full rounded border p-2" /></label><label className="block text-sm">Etternavn<input name="last_name" defaultValue={profile.last_name} className="mt-1 w-full rounded border p-2" /></label><label className="block text-sm">Visningsnavn<input name="display_name" defaultValue={profile.display_name} className="mt-1 w-full rounded border p-2" /></label><label className="block text-sm">Telefon<input name="phone_number" defaultValue={profile.phone_number || ''} className="mt-1 w-full rounded border p-2" /></label><label className="block text-sm">Språk<select name="preferred_language" defaultValue={profile.preferred_language} className="mt-1 w-full rounded border p-2"><option value="nb">Norsk</option><option value="en">English</option></select></label><button className="rounded bg-bonde-green px-4 py-2 font-semibold text-white">Lagre profil</button></form>}</main></div>
}
