'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import VoucherDetailClient from '@/components/bilag/VoucherDetailClient'

function VoucherDetailWrapper() {
  const searchParams = useSearchParams()
  const voucherId = searchParams.get('id') || ''

  if (!voucherId) {
    return (
      <div className="min-h-screen bg-bonde-oat flex flex-col font-sans items-center justify-center">
        <p className="text-sm text-stone-600">Mangler bilags-ID.</p>
      </div>
    )
  }

  return <VoucherDetailClient voucherId={voucherId} />
}

export default function VoucherDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-bonde-oat flex flex-col font-sans items-center justify-center">
          <p className="text-sm text-stone-600">Laster...</p>
        </div>
      }
    >
      <VoucherDetailWrapper />
    </Suspense>
  )
}