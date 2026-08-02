'use client'

import React, { useState } from 'react'
import Link from 'next/link'

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <header className="w-full bg-white/95 backdrop-blur-md border-b border-stone-200/80 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-20">
        {/* Left: Brand Logo & Title */}
        <div className="flex items-center space-x-8">
          <Link href="/" className="flex items-center space-x-3 group">
            <span className="bg-bonde-green text-white px-3.5 py-1.5 font-bold text-lg tracking-wider uppercase rounded-md shadow-xs flex items-center gap-1.5">
              <span>🌱</span> Barebonde
            </span>
            <span className="text-xs font-bold tracking-widest text-bonde-earth uppercase bg-amber-50 px-2.5 py-1 rounded-full border border-amber-200/60 hidden sm:inline-block">
              Landbruk
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center space-x-8 text-sm font-medium text-stone-700">
            <Link href="/dashboard" className="hover:text-bonde-green transition-colors py-2">
              Dashboard
            </Link>
            <Link href="/bilag" className="hover:text-bonde-green transition-colors py-2">
              Bilag
            </Link>
            <Link href="/reports" className="hover:text-bonde-green transition-colors py-2">
              Rapporter
            </Link>
          </nav>
        </div>

        {/* Right CTA / Auth Buttons */}
        <div className="hidden sm:flex items-center space-x-6">
          <Link
            href="/farm/setup"
            className="text-xs font-bold uppercase tracking-wider text-stone-800 hover:text-bonde-green transition"
          >
            LOGG INN
          </Link>
          <Link
            href="/farm/setup"
            className="bg-bonde-green hover:bg-bonde-sage text-white text-xs font-bold uppercase tracking-wider px-5 py-2.5 rounded-lg transition shadow-xs"
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
          <Link href="/dashboard" className="block text-sm font-medium text-gray-700 py-2">
            Dashboard
          </Link>
          <Link href="/bilag" className="block text-sm font-medium text-gray-700 py-2">
            Bilag
          </Link>
          <Link href="/reports" className="block text-sm font-medium text-gray-700 py-2">
            Rapporter
          </Link>
          <Link href="/farm/setup" className="block text-sm font-medium text-gray-700 py-2">
            Gårdsoppsett
          </Link>
          <div className="pt-4 border-t border-gray-100 flex flex-col space-y-2">
            <Link
              href="/farm/setup"
              className="w-full text-center bg-bonde-green text-white font-bold text-xs uppercase tracking-wider py-3 rounded-lg"
            >
              OPPDATER GÅRD
            </Link>
            <Link
              href="/"
              className="w-full text-center text-xs font-bold uppercase tracking-wider py-2 text-gray-800"
            >
              HJEM
            </Link>
          </div>
        </div>
      )}
    </header>
  )
}
