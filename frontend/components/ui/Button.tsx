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
  const baseStyles = 'inline-flex items-center justify-center font-medium tracking-wide uppercase transition-all duration-200 text-xs sm:text-sm px-6 py-3 rounded-lg'
  
  const variantStyles = {
    primary: 'bg-bonde-green hover:bg-bonde-sage text-white shadow-sm',
    secondary: 'bg-white hover:bg-bonde-light text-gray-900 border border-gray-200 shadow-sm',
    outline: 'border border-bonde-green text-bonde-green hover:bg-bonde-green hover:text-white',
    text: 'text-gray-700 hover:text-bonde-green px-3 py-2',
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
