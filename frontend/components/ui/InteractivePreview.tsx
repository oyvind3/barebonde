import React from 'react'

interface InteractivePreviewProps {
  className?: string
}

export const InteractivePreview: React.FC<InteractivePreviewProps> = ({ className = '' }) => {
  return (
    <div className={`w-full bg-white border border-gray-200 shadow-card p-6 sm:p-8 ${className}`}>
      {/* Top Header of Simulated Dashboard */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-6 border-b border-gray-100 gap-4">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#43468b] bg-[#e8e7f8] px-2 py-0.5 mb-1 inline-block">
            Gårdsid: 928 371 002
          </span>
          <h3 className="text-2xl font-serif text-gray-900">Solbakken Gård — Live Oversikt</h3>
        </div>
        <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 border border-emerald-200">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Synkronisert mot Landbruksdir.</span>
        </div>
      </div>

      {/* Grid of Simulated Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 my-6">
        <div className="p-4 bg-gray-50 border border-gray-100">
          <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500 block">Driftsinntekter MHI</span>
          <span className="text-2xl font-serif font-bold text-gray-900 mt-1 block">kr 842 500</span>
          <span className="text-xs text-emerald-600 mt-1 block">↑ +12.4% fra i fjor</span>
        </div>

        <div className="p-4 bg-gray-50 border border-gray-100">
          <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500 block">Neste MVA-Frist</span>
          <span className="text-2xl font-serif font-bold text-[#43468b] mt-1 block">10. Aug 2026</span>
          <span className="text-xs text-gray-500 mt-1 block">Klargjort for innsending</span>
        </div>

        <div className="p-4 bg-gray-50 border border-gray-100">
          <span className="text-[11px] font-bold uppercase tracking-wider text-gray-500 block">Aktive Forpaktningsavtaler</span>
          <span className="text-2xl font-serif font-bold text-gray-900 mt-1 block">3 Kontrakter</span>
          <span className="text-xs text-emerald-600 mt-1 block">✓ Alle eSignert</span>
        </div>
      </div>

      {/* Simulated Recent Activity Table */}
      <div className="mt-6">
        <h4 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">Siste Bilag og Avtaler</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-gray-700">
            <thead className="bg-gray-100 text-gray-900 uppercase tracking-wider font-bold">
              <tr>
                <th className="p-3">Dato</th>
                <th className="p-3">Beskrivelse</th>
                <th className="p-3">Kategori</th>
                <th className="p-3 text-right">Beløp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              <tr>
                <td className="p-3 font-mono">01.08.2026</td>
                <td className="p-3 font-medium text-gray-900">Felleskjøpet — Gjødsel KAS 27-0-0</td>
                <td className="p-3"><span className="bg-gray-100 px-2 py-0.5">Drift & Råvarer</span></td>
                <td className="p-3 text-right font-mono font-semibold">kr 34 200,-</td>
              </tr>
              <tr>
                <td className="p-3 font-mono">28.07.2026</td>
                <td className="p-3 font-medium text-gray-900">Tine SA — Melkeoppgjør Juli</td>
                <td className="p-3"><span className="bg-emerald-100 text-emerald-800 px-2 py-0.5">Salgsinntekt</span></td>
                <td className="p-3 text-right font-mono font-semibold text-emerald-700">+ kr 128 400,-</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
