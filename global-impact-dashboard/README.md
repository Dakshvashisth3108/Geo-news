<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# GeoIntel Trade — Frontend

Vite + React 19 + TailwindCSS v4 dashboard for the GeoIntel Trade
platform. The interactive 3D globe (react-globe.gl + three.js) is the
centrepiece, surrounded by real-time signal cards, a live WebSocket
feed, a tension heatmap, and an event timeline.

## Pages
- `/`            → marketing landing page
- `/dashboard`   → main dashboard (your globe + new widgets)

## Project layout
```
global-impact-dashboard/
├── src/
│   ├── App.tsx                       # router shell
│   ├── main.tsx                      # BrowserRouter mount
│   ├── index.css                     # Tailwind v4 + design tokens
│   ├── pages/
│   │   ├── Landing.tsx
│   │   └── Dashboard.tsx             # uses your existing GlobeModel + SidePanel
│   ├── components/
│   │   ├── Globe/GlobeScene.tsx      # existing — now layout-aware (ResizeObserver)
│   │   ├── UI/
│   │   │   ├── Layout.tsx            # existing Header / Footer (still used by globe overlay)
│   │   │   ├── SidePanel.tsx         # existing — slides in on country click
│   │   │   ├── Navbar.tsx            # NEW — top app navigation
│   │   │   └── primitives/           # shadcn-style Button, Card, Badge
│   │   └── Dashboard/
│   │       ├── SignalCard.tsx
│   │       ├── LiveFeed.tsx          # REST backfill + WebSocket fan-out
│   │       ├── HeatmapPlaceholder.tsx
│   │       └── TimelinePlaceholder.tsx
│   └── lib/
│       ├── utils.ts                  # cn(), timeAgo(), clamp()
│       ├── types.ts                  # mirrors backend Pydantic schemas
│       └── api.ts                    # typed REST + WS client
```

## Run locally

**Prereqs:** Node.js 18+

```bash
cd global-impact-dashboard
cp .env.example .env.local            # set VITE_API_URL
npm install
npm run dev                           # http://localhost:3000
```

## Environment

| Variable | Default | Notes |
| --- | --- | --- |
| `VITE_API_URL` | `http://localhost:8000` | FastAPI base URL (no trailing slash). Client appends `/api/v1`. |
| `VITE_WS_URL` | derived | Override only if the WebSocket terminates on a different host. |
| `GEMINI_API_KEY` | — | AI Studio injects this at runtime. |

## Design tokens

Every colour is an HSL value declared in `src/index.css` inside the
Tailwind v4 `@theme {}` block (`--color-primary`, `--color-bull`,
`--color-bear`, etc.). Edit those once and the whole app re-skins.

## How the globe is wired

`src/pages/Dashboard.tsx` imports your existing `GlobeModel` and
`SidePanel` directly — no duplication, no copy/paste. The globe was
updated to size itself from a `ResizeObserver` on its container, so it
now fills whatever box you put it in (a fullscreen `<main>` or a
560-pixel dashboard card).

The country-click → SidePanel flow is unchanged.
