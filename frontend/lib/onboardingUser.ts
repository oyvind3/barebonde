const ONBOARDING_USER_KEY = 'barebonde_onboarding_user_id'

function createLocalUserId(): string {
  return `onb-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function getOrCreateOnboardingUserId(): string {
  if (typeof window === 'undefined') {
    return 'demo-user'
  }

  const existing = window.localStorage.getItem(ONBOARDING_USER_KEY)
  if (existing) {
    return existing
  }

  const nextId = createLocalUserId()
  window.localStorage.setItem(ONBOARDING_USER_KEY, nextId)
  return nextId
}
