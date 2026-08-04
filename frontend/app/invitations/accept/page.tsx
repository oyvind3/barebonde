'use client'

import Link from 'next/link'
import { useSearchParams, useRouter } from 'next/navigation'
import { useState } from 'react'
import { Navbar } from '@/components/navigation/Navbar'
import { apiFetch } from '@/lib/api'

export default function AcceptInvitationPage() {
  const intent = useSearchParams().get('intent') || ''
  const router = useRouter(); const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false)
  const complete = async (action: 'accept' | 'decline') => { setBusy(true); const response = await apiFetch(`/api/invitations/${action}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ intent }) }); if (!response.ok) setMessage(action === 'accept' ? 'Invitasjonen kunne ikke godtas. Kontroller at du er logget inn med riktig e-post.' : 'Invitasjonen kunne ikke avslås.'); else if (action === 'accept') router.replace('/dashboard'); else setMessage('Invitasjonen er avslått.'); setBusy(false) }
  return <div className="min-h-screen bg-bonde-oat"><Navbar/><main className="mx-auto max-w-lg p-6"><section className="rounded-xl bg-white p-6 shadow-sm"><h1 className="text-3xl font-serif">Gårdsinvitasjon</h1>{!intent?<><p className="mt-3">Invitasjonen er ikke lenger gyldig. Be gårdens eier sende en ny invitasjon.</p></>:<><p className="mt-3 text-stone-600">Logg inn med e-postadressen invitasjonen ble sendt til, og velg deretter hva du vil gjøre.</p>{message&&<p className="mt-4 text-sm text-bonde-green">{message}</p>}<div className="mt-6 flex gap-3"><button disabled={busy} onClick={()=>complete('accept')} className="rounded bg-bonde-green px-4 py-2 text-white">Godta invitasjon</button><button disabled={busy} onClick={()=>complete('decline')} className="rounded border px-4 py-2">Avslå</button></div><p className="mt-5 text-sm"><Link className="underline" href={`/login?returnTo=${encodeURIComponent(`/invitations/accept?intent=${intent}`)}`}>Logg inn eller opprett konto</Link></p></>}</section></main></div>
}
