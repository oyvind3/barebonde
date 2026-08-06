'use client'
import { FormEvent, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Navbar } from '@/components/navigation/Navbar'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { apiFetch, rememberCsrfToken } from '@/lib/api'

const safeReturnTo=(value:string|null)=>value?.startsWith('/invitations/accept?intent=')||value==='/dashboard'||value==='/onboarding'?value:'/onboarding'

export default function LoginPage(){
  const router=useRouter()
  const [email,setEmail]=useState('')
  const [password,setPassword]=useState('')
  const [mode,setMode]=useState<'login'|'register'>('login')
  const [message,setMessage]=useState('')
  const [error,setError]=useState('')
  const [loading,setLoading]=useState(false)
  
  const search=typeof window==='undefined'?'':window.location.search
  const returnTo=safeReturnTo(new URLSearchParams(search).get('returnTo'))
  
  // Handle magic link token from URL
  useEffect(()=>{
    const token=new URLSearchParams(search).get('token')
    if(!token)return
    
    apiFetch('/api/auth/magic-link/verify',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({token})
    }).then(async response=>{
      const data=await response.json()
      if(!response.ok) throw new Error(data.detail||'Lenken kunne ikke brukes.')
      rememberCsrfToken(data.csrf_token)
      router.replace(returnTo)
    }).catch(reason=>setError(reason instanceof Error?reason.message:'Lenken kunne ikke brukes.'))
  },[router,returnTo,search])
  
  const submit=async(event:FormEvent)=>{
    event.preventDefault()
    setLoading(true)
    setError('')
    
    try{
      let endpoint,body
      if(mode==='login'){
        // Try password login first
        endpoint='/api/auth/login/password'
        body={email,password}
      }else{
        // Registration with optional password
        endpoint='/api/auth/register'
        body={
          email,
          password: password || undefined,
          first_name: 'Bonde',
          last_name: '',
          phone_number: ''
        }
      }
      
      const response=await apiFetch(endpoint,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(body)
      })
      
      const data=await response.json().catch(()=>({}))
      
      if(!response.ok){
        // If password login fails and user doesn't have password, suggest magic link
        if(mode==='login' && response.status===401 && data.detail?.includes('ikke satt et passord')){
          setMessage('Du har ikke satt passord ennå. Vi sender en innloggingslenke på e-post.')
          // Automatically send magic link
          await apiFetch('/api/auth/email/request',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({email,return_to:returnTo})
          })
          return
        }
        throw new Error(data.detail||'Kunne ikke fullføre forespørselen.')
      }
      
      // For registration, show success message
      if(mode==='register'){
        setMessage(data.message||'Registrering fullført! Sjekk e-posten din for bekreftelse.')
      } else {
        // For login, redirect on success
        if(data.csrf_token){
          rememberCsrfToken(data.csrf_token)
          router.replace(returnTo)
        }
      }
    }catch(reason){
      setError(reason instanceof Error?reason.message:'Noe gikk galt. Prøv igjen.')
    }finally{
      setLoading(false)
    }
  }
  
  return (
    <div className="min-h-screen bg-bonde-oat">
      <Navbar/>
      <main className="flex justify-center p-6 py-16">
        <Card hoverEffect={false} className="w-full max-w-md bg-white p-8">
          <h1 className="text-3xl font-serif">
            {mode==='login'?'Logg inn':'Opprett konto'}
          </h1>
          
          <div className="mt-4 flex gap-3 border-b pb-4">
            <button 
              onClick={()=>{setMode('login');setError('');setMessage('')}}
              className={`pb-2 ${mode==='login'?'border-b-2 border-bonde-green text-bonde-green':''}`}
            >
              Logg inn
            </button>
            <button 
              onClick={()=>{setMode('register');setError('');setMessage('')}}
              className={`pb-2 ${mode==='register'?'border-b-2 border-bonde-green text-bonde-green':''}`}
            >
              Opprett konto
            </button>
          </div>
          
          {error&&<p className="mt-4 text-red-700 text-sm">{error}</p>}
          {message&&<p className="mt-4 text-bonde-green text-sm">{message}</p>}
          
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                E-post
              </label>
              <input 
                id="email"
                className="w-full rounded border p-3 focus:ring-2 focus:ring-bonde-green focus:border-transparent" 
                required 
                type="email" 
                value={email} 
                onChange={event=>setEmail(event.target.value)}
                autoComplete="email"
              />
            </div>
            
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Passord {mode==='login'&&'(valgfritt hvis du ikke har satt ett)'}
              </label>
              <input 
                id="password"
                className="w-full rounded border p-3 focus:ring-2 focus:ring-bonde-green focus:border-transparent" 
                type="password" 
                value={password} 
                onChange={event=>setPassword(event.target.value)}
                minLength={mode==='register'?8:undefined}
                placeholder={mode==='register'?'Minst 8 tegn':''}
                autoComplete={mode==='login'?'current-password':'new-password'}
              />
              {mode==='register' && (password || '').length < 8 && (password || '').length > 0 &&(
                <p className="mt-1 text-xs text-gray-500">Passordet må være minst 8 tegn</p>
              )}
            </div>
            
            {mode==='login' && (
              <p className="text-xs text-gray-500">
                Har du ikke passord?{" "}
                <button 
                  type="button"
                  onClick={async()=>{
                    if(!email){
                      setError('Skriv inn e-postadressen din først')
                      return
                    }
                    try{
                      await apiFetch('/api/auth/email/request',{
                        method:'POST',
                        headers:{'Content-Type':'application/json'},
                        body:JSON.stringify({email,return_to:returnTo})
                      })
                      setMessage('Innloggingslenke sendt på e-post!')
                    }catch(e){
                      setError('Kunne ikke sende lenke. Prøv igjen.')
                    }
                  }}
                  className="text-bonde-green underline hover:text-bonde-green/80"
                >
                  Få tilsendt innloggingslenke
                </button>
              </p>
            )}
            
            <Button 
              type="submit" 
              disabled={loading||(mode==='register' && (password || '').length < 8)} 
              variant="primary" 
              fullWidth
            >
              {loading?'Vent...':(mode==='login'?'Logg inn':'Opprett konto')}
            </Button>
          </form>
          
          {mode==='login'&&(
            <p className="mt-6 text-center text-sm text-gray-600">
              Ny bruker?{" "}
              <button 
                onClick={()=>{setMode('register');setError('');setMessage('')}}
                className="text-bonde-green font-medium hover:text-bonde-green/80"
              >
                Opprett konto
              </button>
            </p>
          )}
          {mode==='register'&&(
            <p className="mt-6 text-center text-sm text-gray-600">
              Allerede bruker?{" "}
              <button 
                onClick={()=>{setMode('login');setError('');setMessage('')}}
                className="text-bonde-green font-medium hover:text-bonde-green/80"
              >
                Logg inn
              </button>
            </p>
          )}
        </Card>
      </main>
    </div>
  )
}
