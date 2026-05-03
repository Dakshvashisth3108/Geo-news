import Link from "next/link";
import { ArrowRight, Activity, Globe2, Radio, Sparkles } from "lucide-react";

import { Navbar } from "@/components/layout/Navbar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function LandingPage() {
  return (
    <>
      <Navbar />

      <main className="mx-auto max-w-screen-2xl px-6 pb-24">
        {/* ---------------- Hero ---------------- */}
        <section className="relative pt-20 pb-24 text-center">
          <Badge variant="accent" className="mx-auto mb-6 inline-flex items-center gap-1.5 normal-case tracking-normal">
            <Sparkles className="h-3 w-3" />
            <span className="font-mono text-[11px]">v0.1 · early access</span>
          </Badge>

          <h1 className="mx-auto max-w-4xl text-balance text-5xl font-semibold leading-[1.05] tracking-tight md:text-6xl lg:text-7xl">
            Trade the world&apos;s next move,{" "}
            <span className="bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
              before it happens.
            </span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-pretty text-base leading-relaxed text-muted-foreground md:text-lg">
            GeoIntel Trade ingests live geopolitical events, scores them against the
            Global Tension Index, and streams correlated trading signals to your
            desk in seconds.
          </p>

          <div className="mt-10 flex items-center justify-center gap-3">
            <Button asChild size="lg">
              <Link href="/dashboard">
                Open Dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="https://github.com/Dakshvashisth3108/Geo-news" target="_blank">
                View Source
              </Link>
            </Button>
          </div>
        </section>

        {/* ---------------- Feature grid ---------------- */}
        <section className="grid gap-4 md:grid-cols-3">
          <Feature
            icon={<Globe2 className="h-5 w-5" />}
            title="Geopolitical engine"
            body="Ingestion of news + events, NER, financial sentiment, and zero-shot event classification — all distilled into a single 0–100 GTI score."
          />
          <Feature
            icon={<Activity className="h-5 w-5" />}
            title="Multi-asset signals"
            body="Each signal carries direction, confidence, uncertainty, and a list of correlated assets with expected impact and lag."
          />
          <Feature
            icon={<Radio className="h-5 w-5" />}
            title="Real-time stream"
            body="A single WebSocket fan-out delivers every new signal to the dashboard the moment the engine produces it."
          />
        </section>
      </main>
    </>
  );
}

function Feature({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <Card className="p-6">
      <span className="grid h-10 w-10 place-items-center rounded-lg bg-primary/10 text-primary">
        {icon}
      </span>
      <h3 className="mt-4 text-base font-semibold">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{body}</p>
    </Card>
  );
}
