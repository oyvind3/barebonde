'use client'

import { Suspense } from 'react'
import AuthCallbackContent from './callback-content'

// This page is dynamic and should not be statically generated
export const dynamic = 'force-dynamic'

export default function AuthCallback() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <AuthCallbackContent />
    </Suspense>
  )
}

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-farm-green mb-4">Innlogger...</h1>
        <p className="text-gray-600">Vennligst vent mens vi oppretter kontoen din</p>
      </div>
    </div>
  )
}
