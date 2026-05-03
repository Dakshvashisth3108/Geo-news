import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendingUp, TrendingDown, Crosshair, X } from 'lucide-react';
import { cn } from '../../lib/utils';

interface SidePanelProps {
  isOpen: boolean;
  onClose: () => void;
  countryName: string | null;
}

const ASSETS = [
  { name: 'HSI', value: '16.2', change: '+0.00%', positive: true },
  { name: 'CNY', value: '7.24', change: '+0.12%', positive: true },
  { name: 'COPPER', value: '8420', change: '-0.34%', positive: false },
];

export const SidePanel: React.FC<SidePanelProps> = ({ isOpen, countryName, onClose }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: '100%', opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          className="fixed right-0 top-0 h-full w-full md:w-[480px] bg-[#020617]/90 border-l border-white/10 backdrop-blur-2xl z-50 p-8 flex flex-col shadow-[0_0_100px_rgba(0,0,0,0.5)] overflow-y-auto scrollbar-none"
          id="side-panel"
        >
          <div className="relative z-10 flex flex-col h-full">
            <div className="flex items-center justify-between mb-10">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center">
                  <Crosshair size={20} className="text-indigo-400" />
                </div>
                <div>
                  <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Market Analysis</p>
                  <p className="text-xs font-bold text-indigo-400">SELECT ASSET</p>
                </div>
              </div>
              <button 
                onClick={onClose}
                className="p-3 bg-slate-800/40 hover:bg-slate-800 border border-slate-700/50 rounded-xl text-slate-400 transition-all group active:scale-95"
              >
                <X size={20} className="group-hover:rotate-90 transition-transform" />
              </button>
            </div>

            <h2 className="text-4xl font-light mb-10 tracking-tight text-white/90">
              {countryName || 'Global Market'}
            </h2>

            <div className="grid grid-cols-1 gap-4 mb-10">
              <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-none">
                {ASSETS.map((asset) => (
                  <div 
                    key={asset.name}
                    className="min-w-[140px] bg-slate-800/30 border border-slate-700/50 p-4 rounded-2xl flex flex-col gap-2 hover:border-indigo-500/50 transition-all cursor-pointer group hover:bg-slate-800/50"
                  >
                    <span className="text-[10px] font-mono font-bold text-slate-500 tracking-wider">
                      {asset.name}
                    </span>
                    <div className="flex items-end gap-1.5">
                      <span className="text-xl font-medium text-white">{asset.value}</span>
                      <span className={cn(
                        "text-[10px] font-bold mb-1",
                        asset.positive ? "text-emerald-400" : "text-rose-400"
                      )}>
                        {asset.change}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex-1 min-h-[250px] bg-slate-900/50 rounded-3xl border border-slate-800 p-6 flex flex-col relative overflow-hidden group">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(99,102,241,0.1),transparent_70%)]" />
              
              <div className="relative z-10 flex justify-between items-center mb-6">
                 <span className="text-xs font-mono font-bold text-slate-400 tracking-widest uppercase italic">Price Index</span>
                 <div className="flex gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                    <span className="text-[10px] text-indigo-400 font-bold">LIVE DATA</span>
                 </div>
              </div>
              
              <div className="flex-1">
                <svg className="w-full h-full" viewBox="0 0 400 200" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#6366f1" stopOpacity="0.5" />
                      <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path
                    d="M 0 160 Q 50 140, 100 150 T 200 100 T 300 120 T 400 80 V 200 H 0 Z"
                    fill="url(#lineGrad)"
                  />
                  <path
                    d="M 0 160 Q 50 140, 100 150 T 200 100 T 300 120 T 400 80"
                    fill="none"
                    stroke="#6366f1"
                    strokeWidth="3"
                    className="drop-shadow-[0_0_8px_rgba(99,102,241,0.8)]"
                  />
                </svg>
              </div>

              <div className="grid grid-cols-2 gap-8 mt-6 pt-6 border-t border-slate-800">
                <div className="flex flex-col">
                  <span className="text-[10px] font-mono text-slate-500 uppercase italic">Volatility</span>
                  <span className="text-lg font-bold text-white">0.24%</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-[10px] font-mono text-slate-500 uppercase italic">Spread</span>
                  <span className="text-lg font-bold text-white">0.002</span>
                </div>
              </div>
            </div>

            <div className="mt-10 pt-10 border-t border-slate-800" id="sector-exposure">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2 text-xs font-bold tracking-widest text-indigo-400 uppercase">
                  <TrendingUp size={16} />
                  <span>Sector Exposure</span>
                </div>
                <div className="px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 rounded text-[10px] text-indigo-400 font-mono">
                  UPDATED
                </div>
              </div>
              
              <div className="space-y-6">
                <SectorRow name="Energy" value={35} color="bg-emerald-500" />
                <SectorRow name="Defense" value={65} color="bg-rose-500" />
                <SectorRow name="Technology" value={82} color="bg-indigo-500" />
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

const SectorRow = ({ name, value, color }: { name: string, value: number, color: string }) => (
  <div className="space-y-2 group">
    <div className="flex justify-between text-[11px] uppercase font-bold tracking-widest text-slate-500 group-hover:text-indigo-300 transition-colors">
      <span>{name}</span>
      <span className="text-slate-200">{value}%</span>
    </div>
    <div className="h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-800/50 p-0.5">
      <motion.div 
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 1.5, ease: 'circOut' }}
        className={cn("h-full rounded-full shadow-[0_0_15px_rgba(99,102,241,0.3)]", color)} 
      />
    </div>
  </div>
);

