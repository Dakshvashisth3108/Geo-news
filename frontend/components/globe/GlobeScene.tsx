"use client";

/**
 * Ported from `global-impact-dashboard/src/components/Globe/GlobeScene.tsx`.
 * Changes vs. the original Vite version:
 *   * "use client" directive (required in App Router).
 *   * Initial `dimensions` state defaults to 0/0 instead of `window.innerWidth`,
 *     so the module is safe even if it ever loads on the server (it shouldn't —
 *     dashboard/page.tsx imports this via `dynamic({ ssr: false })`).
 *   * `globeRef.current` removed from the controls effect's dep list — refs
 *     don't trigger re-renders, listing them is a React lint nit.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import Globe from "react-globe.gl";
import * as THREE from "three";

const COUNTRY_COLORS: Record<string, string> = {
  Russia: "#f43f5e",
  Canada: "#f43f5e",
  China: "#0ea5e9",
  USA: "#3b82f6",
  Brazil: "#10b981",
  Australia: "#10b981",
  India: "#10b981",
  Kazakhstan: "#f59e0b",
  Algeria: "#10b981",
  Libya: "#f59e0b",
  Egypt: "#0ea5e9",
};

const DEFAULT_COLOR = "rgba(6, 78, 59, 0.4)";
const DEFAULT_STROKE = "rgba(4, 120, 87, 0.5)";

interface GlobeSceneProps {
  onCountryClick: (name: string) => void;
  selectedCountry: string | null;
}

export function GlobeScene({ onCountryClick, selectedCountry }: GlobeSceneProps) {
  const globeRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [geoData, setGeoData] = useState<any>(null);
  const [hoveredCountry, setHoveredCountry] = useState<any>(null);

  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // Track the parent container's size — works whether the globe is fullscreen
  // or laid out inside a dashboard card.
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const update = () =>
      setDimensions({ width: el.clientWidth, height: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    fetch(
      "https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson",
    )
      .then((res) => res.json())
      .then((data) => setGeoData(data))
      .catch(() => {
        /* leave geoData null — globe still renders the sphere */
      });
  }, []);

  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;
    globe.controls().autoRotate = !selectedCountry;
    globe.controls().autoRotateSpeed = 0.5;
    globe.controls().enableZoom = true;
    globe.controls().minDistance = 150;
    globe.controls().maxDistance = 400;
    if (!selectedCountry) {
      globe.pointOfView({ altitude: 2.5 });
    }
  }, [selectedCountry]);

  const arcsData = useMemo(
    () =>
      Array.from({ length: 15 }).map(() => ({
        startLat: (Math.random() - 0.5) * 180,
        startLng: (Math.random() - 0.5) * 360,
        endLat: (Math.random() - 0.5) * 180,
        endLng: (Math.random() - 0.5) * 360,
        color: Math.random() > 0.5 ? "#f43f5e" : "#6366f1",
      })),
    [],
  );

  const getCountryColor = (name: string, isHovered: boolean, isSelected: boolean) => {
    const baseColor = COUNTRY_COLORS[name] || DEFAULT_COLOR;
    if (isSelected) return "#6366f1";
    if (isHovered) return "#ffffff";
    return baseColor.startsWith("#") ? `${baseColor}b3` : baseColor;
  };

  const getStrokeColor = (name: string, isHovered: boolean, isSelected: boolean) => {
    if (isSelected) return "#818cf8";
    if (isHovered) return "#ffffff";
    return COUNTRY_COLORS[name] || DEFAULT_STROKE;
  };

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full cursor-grab overflow-hidden active:cursor-grabbing"
    >
      {dimensions.width > 0 && (
        <Globe
          ref={globeRef}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor="rgba(0,0,0,0)"
          showAtmosphere
          atmosphereColor="#6366f1"
          atmosphereAltitude={0.15}
          globeMaterial={
            new THREE.MeshPhongMaterial({ color: "#020817" })
          }
          polygonsData={geoData ? geoData.features : []}
          polygonAltitude={(d: any) => {
            const isSelected = d.properties.name === selectedCountry;
            const isHovered = d === hoveredCountry;
            return isSelected ? 0.08 : isHovered ? 0.04 : 0.01;
          }}
          polygonCapColor={(d: any) =>
            getCountryColor(
              d.properties.name,
              d === hoveredCountry,
              d.properties.name === selectedCountry,
            )
          }
          polygonSideColor={() => "rgba(0, 0, 0, 0.2)"}
          polygonStrokeColor={(d: any) =>
            getStrokeColor(
              d.properties.name,
              d === hoveredCountry,
              d.properties.name === selectedCountry,
            )
          }
          onPolygonHover={setHoveredCountry}
          onPolygonClick={(d: any) => onCountryClick(d.properties.name)}
          polygonLabel={({ properties: d }: any) => `
            <div class="bg-slate-900/90 border border-indigo-500/50 backdrop-blur-md px-3 py-1.5 rounded-lg text-white font-sans pointer-events-none shadow-2xl relative z-50">
              <div class="text-[10px] uppercase font-bold tracking-widest text-indigo-400 mb-0.5">Region Impact</div>
              <div class="text-sm font-medium whitespace-nowrap">${d.name}</div>
            </div>
          `}
          arcsData={arcsData}
          arcColor={"color" as never}
          arcDashLength={0.4}
          arcDashGap={0.2}
          arcDashAnimateTime={2000}
          arcsTransitionDuration={0}
        />
      )}
    </div>
  );
}
