'use client'

interface ProgressTrackerProps {
  completedSteps: string[]
  totalSteps: number
  completionPercent: number
}

export function ProgressTracker({ completedSteps, totalSteps, completionPercent }: ProgressTrackerProps) {
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-gray-700">
          Fremdrift
        </p>
        <p className="text-sm text-gray-600">
          {completedSteps.length} av {totalSteps} steg · {completionPercent}%
        </p>
      </div>
      
      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div 
          className="bg-bonde-green h-3 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${completionPercent}%` }}
          role="progressbar"
          aria-valuenow={completionPercent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Onboarding fremdrift"
        />
      </div>
      
      {/* Step indicators */}
      <div className="mt-4 flex items-center justify-between">
        {['identity', 'profile', 'farm', 'farm_settings', 'bank_account', 'interests', 'summary'].map((step, index) => {
          const isCompleted = completedSteps.includes(step)
          const isActive = !isCompleted && index === completedSteps.length
          
          return (
            <div key={step} className="flex flex-col items-center">
              <div 
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-colors ${
                  isCompleted 
                    ? 'bg-bonde-green text-white' 
                    : isActive 
                      ? 'bg-bonde-green/20 text-bonde-green border-2 border-bonde-green'
                      : 'bg-gray-200 text-gray-500'
                }`}
                aria-label={`${step}: ${isCompleted ? 'fullført' : isActive ? 'pågår' : 'gjenstår'}`}
              >
                {isCompleted ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  index + 1
                )}
              </div>
              <span className="hidden sm:block text-xs mt-1 text-gray-600 capitalize">
                {step.replace('_', ' ')}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
