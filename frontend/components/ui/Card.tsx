import React from 'react'

interface CardProps {
  children: React.ReactNode
  className?: string
  hoverEffect?: boolean
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  hoverEffect = true,
}) => {
  return (
    <div
      className={`bg-white border border-gray-200/80 rounded-xl p-8 transition-all duration-300 ${
        hoverEffect ? 'hover:shadow-card hover:-translate-y-0.5 hover:border-bonde-sage/40' : 'shadow-soft'
      } ${className}`}
    >
      {children}
    </div>
  )
}
