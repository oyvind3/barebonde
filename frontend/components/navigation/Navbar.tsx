'use client'

import React, { useState } from 'react'
import Link from 'next/link'

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <header className="w-full bg-white border-b border-gray-100 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-20">
        {/* Left: Brand Logo & Title */}
        <div className="flex items-center space-x-8">
          <Link href="/" className="flex items-center space-x-3 group">
            <span className="bg-black text-white px-3 py-1.5 font-bold text-lg tracking-wider uppercase">
              Barebonde
            </span>
            <span className="text-sm font-semibold text-gray-800 hidden sm:inline-block">
              Bedrift
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center space-x-8 text-sm font-medium text-gray-700">
            <div className="relative group cursor-pointer py-2">
              <span className="flex items-center hover:text-gray-900">
                Produkter <span className="ml-1 text-xs">∨</span>
              </span>
            </div>
            <div className="relative group cursor-pointer py-2">
              <span className="flex items-center hover:text-gray-900">
                Bruksområder <span className="ml-1 text-xs">∨</span>
              </span>
            </div>
            <div className="relative group cursor-pointer py-2">
              <span className="flex items-center hover:text-gray-900">
                Innsikt <span className="ml-1 text-xs">∨</span>
              </span>
            </div>
            <Link href="#" className="hover:text-gray-900 py-2">
              Kontakt
            </Link>
            <Link href="#" className="hover:text-gray-900 py-2">
              Priser
            </Link>
          </nav>
        </div>

        {/* Right CTA / Auth Buttons */}
        <div className="hidden sm:flex items-center space-x-6">
          <Link
            href="/farm/setup"
            className="text-xs font-bold uppercase tracking-wider text-gray-900 hover:text-gray-600 transition"
          >
            LOGG INN
          </Link>
          <Link
            href="/farm/setup"
            className="bg-[#43468b] hover:bg-[#34376f] text-white text-xs font-bold uppercase tracking-wider px-5 py-2.5 transition shadow-sm"
          >
            PRØV GRATIS
          </Link>
        </div>

        {/* Mobile menu toggle */}
        <div className="sm:hidden flex items-center">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="text-gray-700 hover:text-gray-900 focus:outline-none p-2"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Menu dropdown */}
      {mobileMenuOpen && (
        <div className="sm:hidden border-b border-gray-200 bg-white px-4 pt-2 pb-6 space-y-3">
          <Link href="#" className="block text-sm font-medium text-gray-700 py-2">
            Produkter
          </Link>
          <Link href="#" className="block text-sm font-medium text-gray-700 py-2">
            Bruksområder
          </Link>
          <Link href="#" className="block text-sm font-medium text-gray-700 py-2">
            Innsikt
          </Link>
          <Link href="#" className="block text-sm font-medium text-gray-700 py-2">
            Kontakt
          </Link>
          <Link href="#" className="block text-sm font-medium text-gray-700 py-2">
            Priser
          </Link>
          <div className="pt-4 border-t border-gray-100 flex flex-col space-y-2">
            <Link
              href="/farm/setup"
              className="w-full text-center bg-[#43468b] text-white font-bold text-xs uppercase tracking-wider py-3"
            >
              PRØV GRATIS
            </Link>
            <Link
              href="/farm/setup"
              className="w-full text-center text-xs font-bold uppercase tracking-wider py-2 text-gray-800"
            >
              LOGG INN
            </Link>
          </div>
        </div>
      )}
    </header>
  )
}
