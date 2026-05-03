import React from 'react';
import { Clock } from 'lucide-react';

import { Card } from '../UI/primitives/Card';
import { cn } from '../../lib/utils';

type Severity = 'low' | 'medium' | 'high' | 'critical';

interface Marker {
  hour: string;
  label: string;
  severity: Severity;
}

const MARKERS: Marker[] = [
  { hour: '06:00', label: 'OPEC+ statement',           severity: 'medium' },
  { hour: '09:30', label: 'US CPI release',            severity: 'high' },
  { hour: '11:15', label: 'Sanction package proposed', severity: 'high' },
  { hour: '14:00', label: 'Election poll update',      severity: 'low' },
  { hour: '17:45', label: 'Border skirmish reported',  severity: 'critical' },
  { hour: '21:00', label: 'Central bank presser',      severity: 'medium' },
];

interface TimelinePlaceholderProps {
  className?: string;
}

/** 24h horizontal timeline placeholder. */
export const TimelinePlaceholder: React.FC<TimelinePlaceholderProps> = ({ className }) => {
  return (
    <Card className={cn('flex h-full flex-col p-5', className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-primary" />
          <h2 className="text-sm font-semibold">Event Timeline · 24h</h2>
        </div>
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">UTC</span>
      </div>

      <div className="relative mt-8 flex-1">
        <div className="absolute left-0 right-0 top-1/2 h-px -translate-y-1/2 bg-border" />
        <div className="absolute inset-0 flex justify-between">
          {Array.from({ length: 9 }, (_, i) => (
            <div key={i} className="flex flex-col items-center">
              <span className="h-2 w-px bg-border" />
              <span className="mt-2 text-[10px] font-mono text-muted-foreground">
                {String(i * 3).padStart(2, '0')}:00
              </span>
            </div>
          ))}
        </div>

        {MARKERS.map((m) => <MarkerEl key={`${m.hour}-${m.label}`} marker={m} />)}
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Legend severity="low" label="Low" />
        <Legend severity="medium" label="Medium" />
        <Legend severity="high" label="High" />
        <Legend severity="critical" label="Critical" />
      </div>
    </Card>
  );
};

const MarkerEl: React.FC<{ marker: Marker }> = ({ marker }) => {
  const [h, m] = marker.hour.split(':').map(Number);
  const left = ((h * 60 + m) / (24 * 60)) * 100;

  return (
    <div className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 group" style={{ left: `${left}%` }}>
      <div className={cn('h-3 w-3 rounded-full ring-4 ring-background', severityColor(marker.severity))} />
      <div className="absolute -top-9 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded-md border border-border bg-card px-2 py-1 text-[10px] font-medium text-foreground group-hover:block">
        {marker.label}
      </div>
    </div>
  );
};

const Legend: React.FC<{ severity: Severity; label: string }> = ({ severity, label }) => (
  <span className="inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
    <span className={cn('h-2 w-2 rounded-full', severityColor(severity))} />
    {label}
  </span>
);

function severityColor(severity: Severity) {
  return {
    low: 'bg-emerald-400',
    medium: 'bg-primary',
    high: 'bg-amber-400',
    critical: 'bg-bear',
  }[severity];
}
