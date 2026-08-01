import React from 'react'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'purple' | 'green' | 'blue' | 'gray'
  className?: string
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'purple',
  className = '',
}) => {
  const variantStyles = {
    purple: 'bg-bonde-light text-bonde-green border border-bonde-sage/20',
    green: 'bg-emerald-100 text-emerald-900 border border-emerald-200',
    blue: 'bg-amber-100 text-amber-900 border border-amber-200',
    gray: 'bg-stone-100 text-stone-700 border border-stone-200',
  }

  return (
    <span
      className={`text-xs font-bold uppercase tracking-widest px-3 py-1 inline-block rounded-full ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  )
}
