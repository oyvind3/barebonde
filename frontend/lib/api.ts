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

export async function bootstrapIdentity(): Promise<IdentityBootstrap | null> {
  const response = await apiFetch('/api/me')
  if (response.status === 401) return null
  if (!response.ok) throw new Error('Kunne ikke hente innlogget bruker.')
  const identity = await response.json() as IdentityBootstrap
  rememberCsrfToken(identity.csrf_token)
  return identity
}
