import type { Metadata } from 'next'
import './globals.css'
import { IdentityProvider } from '@/lib/identity'
import { API_BASE_URL } from '@/lib/api'

export const metadata: Metadata = {
  title: 'Barebonde - Bilagsregistrering og økonomioversikt for landbruk',
  description: 'Bilagsregistrering og enkel økonomioversikt for norsk landbruk. Under utvikling med pilotbrukere.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const apiOrigin = typeof API_BASE_URL === 'string' ? API_BASE_URL : ''
  return (
    <html lang="no">
      <head>
        {apiOrigin && apiOrigin.startsWith('http') && (
          <>
            <link rel="preconnect" href={apiOrigin} crossOrigin="anonymous" />
            <link rel="dns-prefetch" href={apiOrigin} />
          </>
        )}
      </head>
      <body>
        <IdentityProvider>{children}</IdentityProvider>
      </body>
    </html>
  )
}