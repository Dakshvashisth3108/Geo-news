# GeoIntel Trade — Frontend

Next.js 15 (App Router) dashboard for the GeoIntel Trade platform.
Streams real-time trading signals from the FastAPI backend over WebSocket
and visualises geopolitical pressure on an interactive 3D globe.

## Stack
- **Next.js 15** (App Router, React 19)
- **TailwindCSS 3** + shadcn/ui-style design tokens (CSS variables in `app/globals.css`)
- **lucide-react** icons, **framer-motion** for the side panel
- **react-globe.gl** + **three** for the 3D globe (rendered client-only via `dynamic({ ssr: false })`)

## Project structure
```
frontend/
├── app/
│   ├── layout.tsx            # Root shell: fonts, ambient backgrounds
│   ├── globals.css           # Tailwind + shadcn-style design tokens
│   ├── page.tsx              # Landing page
│   └── dashboard/
│       └── page.tsx          # Main dashboard
├── components/
│   ├── ui/                   # shadcn-style primitives (Button, Card, Badge)
│   ├── layout/               # Navbar
│   ├── dashboard/            # SignalCard, LiveFeed, Heatmap, Timeline
│   └── globe/                # GlobeView + ported GlobeScene + SidePanel
└── lib/
    ├── utils.ts              # `cn()`, `timeAgo()`, `clamp()`
    ├── types.ts              # TS mirrors of backend Pydantic schemas
    └── api.ts                # Typed REST + WebSocket client
```

## Quick start
```bash
cd frontend
cp .env.example .env.local           # set NEXT_PUBLIC_API_URL
npm install
npm run dev                          # http://localhost:3000
```

> The first install pulls `three`, `@react-three/fiber`, `@react-three/drei`,
> and `react-globe.gl` — that's ~80 MB of dependencies. Subsequent installs
> are cached.

## Environment
| Variable | Default | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | FastAPI base URL (no trailing slash). Client appends `/api/v1`. |
| `NEXT_PUBLIC_WS_URL` | derived | Override only if the WebSocket terminates on a different host. |

## How the globe is wired
`app/dashboard/page.tsx` is a client component that imports the globe via:
```tsx
const GlobeView = dynamic(() => import("@/components/globe/GlobeView"), {
  ssr: false,
});
```
This is required because `react-globe.gl` reaches for `window` at module
load. The original Vite project at `../global-impact-dashboard/` is left
untouched and continues to work standalone — the components were ported
into `components/globe/` with `"use client"` directives and a
`ResizeObserver`-based sizing hook that adapts to whatever container the
globe sits in (no more `window.innerWidth`).

## Design tokens
All colours live in `app/globals.css` as HSL values mapped to CSS
variables (`--primary`, `--accent`, `--bull`, `--bear`, etc.). The
Tailwind config (`tailwind.config.ts`) re-exports these as named colours
so utility classes like `bg-primary` and `text-bull` work everywhere.

To restyle the dashboard, edit `:root` in `globals.css` — every component
inherits.
