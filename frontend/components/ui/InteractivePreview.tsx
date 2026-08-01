import React from 'react'

interface InteractivePreviewProps {
  className?: string
}

export const InteractivePreview: React.FC<InteractivePreviewProps> = ({ className = '' }) => {
  return (
    <div className={`w-full bg-white border border-stone-200/90 shadow-card rounded-2xl p-6 sm:p-8 ${className}`}>
      {/* Top Header of Simulated Dashboard */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-6 border-b border-stone-200/60 gap-4">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-widest text-bonde-green bg-bonde-light px-2.5 py-1 rounded-md mb-1.5 inline-block">
            Gårdsid: 928 371 002 — Melk & Grovfôr
          </span>
          <h3 className="text-2xl font-serif text-stone-900">Solbakken Gård — Oversikt</h3>
        </div>
        <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200/80">
          <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse"></span>
          <span>Synkronisert mot Landbruksdirektoratet</span>
        </div>
      </div>

      {/* Grid of Simulated Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 my-6">
        <div className="p-4 bg-bonde-oat/40 rounded-xl border border-stone-200/60">
          <span className="text-[11px] font-bold uppercase tracking-wider text-stone-600 block">Driftsinntekter</span>
          <span className="text-2xl font-serif font-bold text-bonde-green mt-1 block">kr 842 500</span>
          <span className="text-xs text-emerald-700 font-medium mt-1 block">↑ +12.4% fra i fjor</span>
        </div>

        <div className="p-4 bg-bonde-oat/40 rounded-xl border border-stone-200/60">
          <span className="text-[11px] font-bold uppercase tracking-wider text-stone-600 block">Neste MVA-Frist</span>
          <span className="text-2xl font-serif font-bold text-bonde-green mt-1 block">10. Aug 2026</span>
          <span className="text-xs text-stone-600 mt-1 block">Klargjort for Altinn</span>
        </div>

        <div className="p-4 bg-bonde-oat/40 rounded-xl border border-stone-200/60">
          <span className="text-[11px] font-bold uppercase tracking-wider text-stone-600 block">Forpaktningsavtaler</span>
          <span className="text-2xl font-serif font-bold text-stone-900 mt-1 block">3 Kontrakter</span>
          <span className="text-xs text-emerald-700 font-medium mt-1 block">✓ Alle eSignert med BankID</span>
        </div>
      </div>

      {/* Simulated Recent Activity Table */}
      <div className="mt-6">
        <h4 className="text-xs font-bold uppercase tracking-wider text-stone-600 mb-3">Siste Bilag & Landbruksoppgjør</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-stone-700">
            <thead className="bg-stone-100/80 text-stone-900 uppercase tracking-wider font-bold rounded-lg">
              <tr>
                <th className="p-3 rounded-l-lg">Dato</th>
                <th className="p-3">Beskrivelse</th>
                <th className="p-3">Kategori</th>
                <th className="p-3 text-right rounded-r-lg">Beløp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              <tr>
                <td className="p-3 font-mono text-stone-600">01.08.2026</td>
                <td className="p-3 font-medium text-stone-900">Felleskjøpet — Gjødsel KAS 27-0-0</td>
                <td className="p-3"><span className="bg-stone-100 text-stone-700 px-2 py-0.5 rounded text-[11px]">Drift & Råvarer</span></td>
                <td className="p-3 text-right font-mono font-semibold text-stone-900">kr 34 200,-</td>
              </tr>
              <tr>
                <td className="p-3 font-mono text-stone-600">28.07.2026</td>
                <td className="p-3 font-medium text-stone-900">Tine SA — Melkeoppgjør Juli</td>
                <td className="p-3"><span className="bg-emerald-100/80 text-emerald-900 px-2 py-0.5 rounded text-[11px]">Salgsinntekt</span></td>
                <td className="p-3 text-right font-mono font-semibold text-emerald-700">+ kr 128 400,-</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
