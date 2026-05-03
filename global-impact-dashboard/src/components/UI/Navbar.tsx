import React from 'react';
import { Link, NavLink as RouterNavLink } from 'react-router-dom';
import { Activity, Beaker, Bell, Globe2, LineChart, Settings } from 'lucide-react';

import { Button } from './primitives/Button';
import { cn } from '../../lib/utils';

/** Top app navigation. Pure visual — no state. */
export const Navbar: React.FC = () => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border/50 bg-background/70 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-screen-2xl items-center gap-6 px-6">
        <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="grid h-8 w-8 place-items-center rounded-md bg-primary/15 text-primary">
            <Globe2 className="h-4 w-4" />
          </span>
          <span className="text-sm">
            GeoIntel <span className="text-primary">Trade</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-1 text-sm">
          <NavLink to="/dashboard" icon={<LineChart className="h-4 w-4" />}>Dashboard</NavLink>
          <NavLink to="/scenario" icon={<Beaker className="h-4 w-4" />}>Scenario</NavLink>
          <NavLink to="/dashboard#signals" icon={<Activity className="h-4 w-4" />}>Signals</NavLink>
          <NavLink to="/dashboard#alerts" icon={<Bell className="h-4 w-4" />}>Alerts</NavLink>
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 rounded-full border border-border bg-card/60 px-3 py-1 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live
          </div>
          <Button variant="ghost" size="icon" aria-label="Settings">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
};

const NavLink: React.FC<{ to: string; icon: React.ReactNode; children: React.ReactNode }> = ({
  to, icon, children,
}) => (
  <RouterNavLink
    to={to}
    className={({ isActive }) =>
      cn(
        'inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground',
        isActive && 'text-foreground bg-secondary/40',
      )
    }
  >
    {icon}
    {children}
  </RouterNavLink>
);
