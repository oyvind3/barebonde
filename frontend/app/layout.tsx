import type { Metadata } from 'next'
import './globals.css'
import { RootClientWrapper } from './root-wrapper'

export const metadata: Metadata = {
  title: 'Barebonde - Regnskapssystem for landbruksvirksomheter',
  description: 'Digital plattform for norske bønder og små landbruksforetak',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="no">
      <body>
        <RootClientWrapper>
          {children}
        </RootClientWrapper>
      </body>
    </html>
  )
}
