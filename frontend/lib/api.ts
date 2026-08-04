const productionApiUrl = 'https://barebonde-ebf2byfnesgzaqgn.norwayeast-01.azurewebsites.net'

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || (
  process.env.NODE_ENV === 'production' ? productionApiUrl : 'http://localhost:8000'
)

export type IdentityBootstrap = {
  user: {
    user_id: string
    email: string
    first_name: string
    last_name: string
    picture?: string | null
    phone_number?: string | null
    status: string
  }
  session: {
    session_id: string
    created_at: string
    last_seen_at?: string | null
    expires_at: string
    current: boolean
  }
  csrf_token: string
  csrf: {
    token: string
    expires_at: string
  }
  memberships: Array<{
    farm: {
      id: string
      name: string
      org_number: string
      farm_status: string
    }
    farm_role: string
    membership_status: string
  }>
  active_farm: {
    id: string
    name: string
    org_number: string
    farm_status: string
  } | null
  subscription: {
    plan_code: string
    plan_version: string
    display_name: string
    subscription_status: string
    started_at?: string | null
    current_period_start?: string | null
    current_period_end?: string | null
    trial_ends_at?: string | null
    grace_period_ends_at?: string | null
    cancel_at_period_end: boolean
    canceled_at?: string | null
  } | null
  entitlements: Record<string, boolean>
}

let csrfToken = ''

export function rememberCsrfToken(value: string | undefined): void {
  csrfToken = value || ''
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  const method = (init.method || 'GET').toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && csrfToken) {
    headers.set('X-CSRF-Token', csrfToken)
  }
  return fetch(`${API_BASE_URL}${path}`, { ...init, headers, credentials: 'include' })
}

export async function apiErrorMessage(response: Response, fallback: string): Promise<string> {
  const payload = await response.json().catch(() => ({})) as { detail?: unknown }
  if (typeof payload.detail === 'string' && payload.detail) return payload.detail
  if (response.status === 401) return 'Logg inn for å fortsette.'
  if (response.status === 403) return 'Du har ikke rollen som kreves for denne handlingen.'
  if (response.status === 404) return 'Ressursen ble ikke funnet.'
  if (response.status === 409) return 'Handlingen er allerede utført eller er i konflikt med gjeldende status.'
  return fallback
}

export async function bootstrapIdentity(preferredFarmId?: string): Promise<IdentityBootstrap | null> {
  const selectedFarmId = preferredFarmId || (
    typeof window !== 'undefined' ? window.localStorage.getItem('barebonde_active_farm_id') || '' : ''
  )
  const query = selectedFarmId ? `?active_farm_id=${encodeURIComponent(selectedFarmId)}` : ''
  const response = await apiFetch(`/api/me${query}`)
  if (response.status === 401) return null
  if (!response.ok) throw new Error('Kunne ikke hente innlogget bruker.')
  const identity = await response.json() as IdentityBootstrap
  rememberCsrfToken(identity.csrf_token)
  return identity
}
