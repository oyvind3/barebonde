'use client'

import { AuthProvider } from '@/hooks/useAuth'

export function RootClientWrapper({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  )
}
