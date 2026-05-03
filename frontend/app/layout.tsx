import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// next/font.google bakes the font CSS into the build — no runtime fetch.
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-jetbrains",
});

export const metadata: Metadata = {
  title: {
    default: "GeoIntel Trade — Geopolitical Intelligence for Algorithmic Trading",
    template: "%s · GeoIntel Trade",
  },
  description:
    "Real-time geopolitical intelligence and trading signals. Track the Global Tension Index, watch correlated assets, and react to events the moment they break.",
  metadataBase: new URL("https://geointel.trade"),
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrains.variable} dark`}
      suppressHydrationWarning
    >
      <body className="min-h-screen antialiased font-sans">
        {/* Ambient background — subtle radial glows behind every page. */}
        <div className="pointer-events-none fixed inset-0 -z-10">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,hsl(var(--primary)/0.10),transparent_55%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_90%,hsl(var(--accent)/0.08),transparent_55%)]" />
          <div
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage:
                "linear-gradient(hsl(var(--primary)/0.5) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--primary)/0.5) 1px, transparent 1px)",
              backgroundSize: "100px 100px",
            }}
          />
        </div>

        {children}
      </body>
    </html>
  );
}
