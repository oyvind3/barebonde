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
    purple: 'bg-[#e8e7f8] text-[#43468b]',
    green: 'bg-[#e8f4e8] text-[#2d5016]',
    blue: 'bg-blue-100 text-blue-800',
    gray: 'bg-gray-100 text-gray-800',
  }

  return (
    <span
      className={`text-xs font-bold uppercase tracking-widest px-3 py-1 inline-block ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  )
}
