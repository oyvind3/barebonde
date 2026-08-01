import React from 'react'

interface StatsItem {
  value: string
  label: string
}

interface StatsBarProps {
  stats?: StatsItem[]
  className?: string
}

const defaultStats: StatsItem[] = [
  { value: '1M+', label: 'Solgte bilag' },
  { value: '200K+', label: 'Oppgaver utført' },
  { value: '50K+', label: 'Aktive brukere' },
  { value: '60K+', label: 'Gårdsbruk registrert' },
]

export const StatsBar: React.FC<StatsBarProps> = ({
  stats = defaultStats,
  className = '',
}) => {
  return (
    <div className={`w-full py-12 border-t border-gray-100 ${className}`}>
      <div className="max-w-6xl mx-auto px-4 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
        {stats.map((stat, index) => (
          <div key={index} className="flex flex-col items-center">
            <span className="text-4xl md:text-5xl font-bold font-sans text-gray-900 tracking-tight">
              {stat.value}
            </span>
            <span className="text-xs uppercase tracking-wider text-gray-500 font-semibold mt-2">
              {stat.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
