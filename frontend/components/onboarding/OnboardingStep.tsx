'use client'

import { useState } from 'react'

interface OnboardingStepProps {
  stepNumber: number
  title: string
  description: string
  isCompleted: boolean
  href?: string
  linkText?: string
  children?: React.ReactNode
}

export function OnboardingStep({ 
  stepNumber, 
  title, 
  description, 
  isCompleted, 
  href, 
  linkText,
  children 
}: OnboardingStepProps) {
  return (
    <section className="border-b border-gray-100 pb-4 last:border-0">
      <div className="flex items-start gap-3">
        {/* Step indicator */}
        <div 
          className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${
            isCompleted 
              ? 'bg-bonde-green text-white' 
              : 'bg-gray-200 text-gray-600'
          }`}
          aria-label={`Steg ${stepNumber}: ${isCompleted ? 'fullført' : 'gjenstår'}`}
        >
          {isCompleted ? (
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            stepNumber
          )}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <h2 className="font-semibold text-gray-900">
            {title}
            {isCompleted && (
              <span className="ml-2 text-xs font-normal text-bonde-green">✓ Fullført</span>
            )}
          </h2>
          <p className="text-sm text-gray-600 mt-1">{description}</p>
          
          {href && linkText && (
            <a 
              href={href}
              className="inline-block mt-2 text-sm text-bonde-green hover:text-bonde-green/80 underline transition-colors focus:outline-none focus:ring-2 focus:ring-bonde-green focus:ring-offset-2 rounded"
            >
              {linkText}
            </a>
          )}
          
          {children}
        </div>
      </div>
    </section>
  )
}
