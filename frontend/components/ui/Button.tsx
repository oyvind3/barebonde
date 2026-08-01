import React from 'react'
import Link from 'next/link'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'text'
  href?: string
  children: React.ReactNode
  showArrow?: boolean
  fullWidth?: boolean
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  href,
  children,
  showArrow = false,
  fullWidth = false,
  className = '',
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium tracking-wide uppercase transition-all duration-200 text-xs sm:text-sm px-6 py-3 rounded-none'
  
  const variantStyles = {
    primary: 'bg-[#43468b] hover:bg-[#34376f] text-white shadow-sm',
    secondary: 'bg-white hover:bg-gray-50 text-gray-900 border border-gray-300 shadow-sm',
    outline: 'border border-[#43468b] text-[#43468b] hover:bg-[#43468b] hover:text-white',
    text: 'text-gray-700 hover:text-gray-900 px-3 py-2',
  }

  const widthStyle = fullWidth ? 'w-full' : ''
  const combinedClasses = `${baseStyles} ${variantStyles[variant]} ${widthStyle} ${className}`.trim()

  const content = (
    <>
      <span>{children}</span>
      {showArrow && <span className="ml-2 text-base">→</span>}
    </>
  )

  if (href) {
    return (
      <Link href={href} className={combinedClasses}>
        {content}
      </Link>
    )
  }

  return (
    <button className={combinedClasses} {...props}>
      {content}
    </button>
  )
}
