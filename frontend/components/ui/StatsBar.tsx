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
  { value: '12 000+', label: 'Norske bønder' },
  { value: '98%', label: 'Tid spart på bilag' },
  { value: 'EHF / Peppol', label: 'Innebygd fakturering' },
  { value: 'Altinn & MVA', label: 'Direkte rapportering' },
]

export const StatsBar: React.FC<StatsBarProps> = ({
  stats = defaultStats,
  className = '',
}) => {
  return (
    <div className={`w-full py-12 border-t border-b border-stone-200/60 bg-bonde-oat/50 ${className}`}>
      <div className="max-w-6xl mx-auto px-4 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
        {stats.map((stat, index) => (
          <div key={index} className="flex flex-col items-center">
            <span className="text-3xl md:text-4xl font-bold font-sans text-bonde-green tracking-tight">
              {stat.value}
            </span>
            <span className="text-xs uppercase tracking-wider text-stone-600 font-semibold mt-2">
              {stat.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
