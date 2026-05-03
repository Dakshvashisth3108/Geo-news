import React from 'react';
import { Globe as GlobeIcon, Activity, Settings2, Target, ChevronRight } from 'lucide-react';

export const Header = () => {
  return (
    <header className="fixed top-0 left-0 w-full z-40 p-6 flex items-center justify-between pointer-events-none" id="dashboard-header">
      <div className="flex items-center gap-6 pointer-events-auto">
        <div className="flex items-center gap-2 bg-slate-900/40 border border-white/10 px-4 py-2 rounded-full backdrop-blur-md">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px] font-bold tracking-widest text-slate-200 uppercase">Live</span>
        </div>
        
        <div className="flex items-center gap-4 bg-slate-900/40 border border-white/10 px-4 py-2 rounded-full backdrop-blur-md group cursor-default">
          <div className="flex items-center gap-2">
            <GlobeIcon size={14} className="text-white/60 group-hover:text-indigo-400 transition-colors" />
            <span className="text-[10px] font-bold text-white/40 uppercase tracking-widest">Global GTI</span>
          </div>
          <span className="text-xs font-bold text-white tracking-widest">55.0</span>
        </div>
      </div>

      <div className="flex items-center gap-3 pointer-events-auto">
        <button className="p-2.5 bg-slate-900/40 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all shadow-lg active:scale-95">
          <Activity size={18} />
        </button>
        <button className="p-2.5 bg-indigo-600/80 border border-indigo-400/50 rounded-xl text-white hover:bg-indigo-600 transition-all shadow-[0_0_20px_rgba(99,102,241,0.3)] active:scale-95">
          <Settings2 size={18} />
        </button>
      </div>
    </header>
  );
};

export const Footer = () => {
  return (
    <footer className="fixed bottom-8 left-1/2 -translate-x-1/2 z-40" id="dashboard-footer">
      <div className="flex items-center gap-3 bg-slate-900/80 border border-white/10 px-6 py-2.5 rounded-full shadow-2xl backdrop-blur-xl group cursor-pointer hover:border-white/20 transition-all">
        <Target size={14} className="text-indigo-400 animate-pulse" />
        <span className="text-[10px] font-bold tracking-[0.2em] text-white/60 group-hover:text-white transition-colors uppercase">
          Click any country to view market impact
        </span>
        <ChevronRight size={14} className="text-white/20 group-hover:translate-x-1 group-hover:text-white transition-all ml-2" />
      </div>
    </footer>
  );
};

