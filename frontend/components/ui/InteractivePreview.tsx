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
            Eksempeldata
          </span>
          <h3 className="text-2xl font-serif text-stone-900">Solbakken Gård</h3>
        </div>
        <div className="flex items-center space-x-2 text-xs font-medium text-stone-600 bg-stone-50 px-3 py-1.5 rounded-full border border-stone-200/80">
          <span className="w-2 h-2 rounded-full bg-stone-400"></span>
          <span>Konseptvisning</span>
        </div>
      </div>

      {/* Grid of Simulated Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 my-6">
        <div className="p-4 bg-bonde-oat/40 rounded-xl border border-stone-200/60">
          <span className="text-[11px] font-bold uppercase tracking-wider text-stone-500 block">Inngående (Inntekter)</span>
          <span className="text-2xl font-serif font-bold text-emerald-700 mt-1 block">kr 842 500</span>
          <span className="text-xs text-stone-500 mt-1 block">Eksempel: Tine, Nortura, Tilskudd</span>
        </div>

        <div className="p-4 bg-bonde-oat/40 rounded-xl border border-stone-200/60">
          <span className="text-[11px] font-bold uppercase tracking-wider text-stone-500 block">Utgående (Kostnader)</span>
          <span className="text-2xl font-serif font-bold text-stone-800 mt-1 block">kr 310 200</span>
          <span className="text-xs text-stone-500 mt-1 block">Eksempel: Gjødsel, Fôr, Diesel</span>
        </div>

        <div className="p-4 bg-bonde-oat/40 rounded-xl border border-stone-200/60">
          <span className="text-[11px] font-bold uppercase tracking-wider text-stone-500 block">Registrerte bilag</span>
          <span className="text-2xl font-serif font-bold text-bonde-green mt-1 block">47 bilag</span>
          <span className="text-xs text-stone-500 mt-1 block">Eksempel: siste 30 dager</span>
        </div>
      </div>

      {/* Simulated Recent Activity Table */}
      <div className="mt-6">
        <h4 className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-3">Siste registrerte bilag (eksempel)</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-stone-700">
            <thead className="bg-stone-100/80 text-stone-900 uppercase tracking-wider font-bold rounded-lg">
              <tr>
                <th className="p-3 rounded-l-lg">Dato</th>
                <th className="p-3">Beskrivelse</th>
                <th className="p-3">Type</th>
                <th className="p-3 text-right rounded-r-lg">Beløp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              <tr>
                <td className="p-3 font-mono text-stone-500">01.08.2026</td>
                <td className="p-3 font-medium text-stone-900">Felleskjøpet — Gjødsel KAS 27-0-0</td>
                <td className="p-3"><span className="bg-stone-100 text-stone-700 px-2 py-0.5 rounded text-[11px]">Utgående</span></td>
                <td className="p-3 text-right font-mono font-semibold text-stone-900">kr 34 200,-</td>
              </tr>
              <tr>
                <td className="p-3 font-mono text-stone-500">28.07.2026</td>
                <td className="p-3 font-medium text-stone-900">Tine SA — Melkeoppgjør Juli</td>
                <td className="p-3"><span className="bg-emerald-100/80 text-emerald-900 px-2 py-0.5 rounded text-[11px]">Inngående</span></td>
                <td className="p-3 text-right font-mono font-semibold text-emerald-700">+ kr 128 400,-</td>
              </tr>
              <tr>
                <td className="p-3 font-mono text-stone-500">15.07.2026</td>
                <td className="p-3 font-medium text-stone-900">Fôrimport — Kraftfôr melkeku</td>
                <td className="p-3"><span className="bg-stone-100 text-stone-700 px-2 py-0.5 rounded text-[11px]">Utgående</span></td>
                <td className="p-3 text-right font-mono font-semibold text-stone-900">kr 18 600,-</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <p className="mt-6 text-xs text-stone-500">
        Dette er en konseptvisning med eksempeldata. MVA-rapportering og avtaler er under utvikling.
      </p>
    </div>
  )
}