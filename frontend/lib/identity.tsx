'use client'

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch, bootstrapIdentity, IdentityBootstrap, rememberCsrfToken } from '@/lib/api'

export type IdentityStatus = 'loading' | 'authenticated' | 'anonymous' | 'error'

interface IdentityContextValue {
  status: IdentityStatus
  identity: IdentityBootstrap | null
  activeFarm: IdentityBootstrap['active_farm']
  refreshIdentity: (preferredFarmId?: string) => Promise<IdentityBootstrap | null>
  setActiveFarm: (farmId: string) => Promise<void>
  logout: () => Promise<void>
}

const IdentityContext = createContext<IdentityContextValue | null>(null)

// Module-level single-flight state shared across all consumers
let inflightPromise: Promise<IdentityBootstrap | null> | null = null
let cachedIdentity: IdentityBootstrap | null = null
let cacheTimestamp = 0
const CACHE_TTL_MS = 30_000 // 30 second memory cache

const FARM_ID_KEY = 'barebonde_active_farm_id'

function getStoredFarmId(): string {
  if (typeof window === 'undefined') return ''
  return window.localStorage.getItem(FARM_ID_KEY) || ''
}

function setStoredFarmId(farmId: string): void {
  if (typeof window === 'undefined') return
  if (farmId) window.localStorage.setItem(FARM_ID_KEY, farmId)
  else window.localStorage.removeItem(FARM_ID_KEY)
}

async function fetchIdentity(preferredFarmId?: string): Promise<IdentityBootstrap | null> {
  const farmId = preferredFarmId || getStoredFarmId()
  const identity = await bootstrapIdentity(farmId || undefined)
  if (identity) {
    cachedIdentity = identity
    cacheTimestamp = Date.now()
    // Sync stored farm id with server-confirmed active farm
    const activeFarmId = identity.active_farm?.id || ''
    setStoredFarmId(activeFarmId)
  }
  return identity
}

function invalidateCache(): void {
  cachedIdentity = null
  cacheTimestamp = 0
  inflightPromise = null
}

export function IdentityProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<IdentityStatus>('loading')
  const [identity, setIdentity] = useState<IdentityBootstrap | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const refreshIdentity = useCallback(async (preferredFarmId?: string): Promise<IdentityBootstrap | null> => {
    // Invalidate cache on explicit refresh
    invalidateCache()

    if (inflightPromise) {
      return inflightPromise
    }

    inflightPromise = fetchIdentity(preferredFarmId)
      .then((result) => {
        inflightPromise = null
        return result
      })
      .catch((error) => {
        inflightPromise = null
        throw error
      })

    return inflightPromise
  }, [])

  // Initial bootstrap on mount
  useEffect(() => {
    let cancelled = false

    const bootstrap = async () => {
      // Check memory cache first
      if (cachedIdentity && Date.now() - cacheTimestamp < CACHE_TTL_MS) {
        if (!cancelled && mountedRef.current) {
          setIdentity(cachedIdentity)
          setStatus('authenticated')
        }
        return
      }

      try {
        const result = await refreshIdentity()
        if (!cancelled && mountedRef.current) {
          setIdentity(result)
          setStatus(result ? 'authenticated' : 'anonymous')
        }
      } catch {
        if (!cancelled && mountedRef.current) {
          // On error, keep any cached identity rather than flashing anonymous
          if (cachedIdentity) {
            setIdentity(cachedIdentity)
            setStatus('authenticated')
          } else {
            setStatus('error')
          }
        }
      }
    }

    bootstrap()
    return () => {
      cancelled = true
    }
  }, [refreshIdentity])

  const setActiveFarm = useCallback(async (farmId: string) => {
    const isMember = identity?.memberships.some((m) => m.farm.id === farmId)
    if (!isMember) return

    setStoredFarmId(farmId)
    invalidateCache()

    try {
      const result = await fetchIdentity(farmId)
      if (mountedRef.current) {
        setIdentity(result)
        setStatus(result ? 'authenticated' : 'anonymous')
      }
    } catch {
      // Keep existing identity on error
    }
  }, [identity])

  const logout = useCallback(async () => {
    try {
      await apiFetch('/api/auth/logout', { method: 'POST' })
    } catch {
      // Ignore logout errors
    }
    rememberCsrfToken('')
    invalidateCache()
    if (mountedRef.current) {
      setIdentity(null)
      setStatus('anonymous')
    }
  }, [])

  const activeFarm = identity?.active_farm || null

  const value = useMemo<IdentityContextValue>(() => ({
    status,
    identity,
    activeFarm,
    refreshIdentity,
    setActiveFarm,
    logout,
  }), [status, identity, activeFarm, refreshIdentity, setActiveFarm, logout])

  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>
}

export function useIdentity(): IdentityContextValue {
  const context = useContext(IdentityContext)
  if (!context) {
    throw new Error('useIdentity must be used within an IdentityProvider')
  }
  return context
}