import React, { useRef, useMemo, useState, useEffect } from 'react';
import Globe from 'react-globe.gl';
import * as THREE from 'three';

// Color Mapping based on the video
const COUNTRY_COLORS: Record<string, string> = {
  'Russia': '#f43f5e', // Red
  'Canada': '#f43f5e',
  'China': '#0ea5e9',  // Sky Blue
  'USA': '#3b82f6',    // Blue
  'Brazil': '#10b981', // Green
  'Australia': '#10b981',
  'India': '#10b981',
  'Kazakhstan': '#f59e0b', // Yellow/Orange
  'Algeria': '#10b981',
  'Libya': '#f59e0b',
  'Egypt': '#0ea5e9',
};

const DEFAULT_COLOR = 'rgba(6, 78, 59, 0.4)'; // Dark Green for generic land
const DEFAULT_STROKE = 'rgba(4, 120, 87, 0.5)';

export const GlobeModel = ({ onCountryClick, selectedCountry }: { onCountryClick: (name: string) => void, selectedCountry: string | null }) => {
  const globeRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [geoData, setGeoData] = useState<any>(null);
  const [hoveredCountry, setHoveredCountry] = useState<any>(null);

  // Track the parent container's size so the globe fits whatever
  // layout it lives inside — fullscreen on the landing experience,
  // or a dashboard card on /dashboard.
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const update = () => setDimensions({ width: el.clientWidth, height: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    fetch('https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson')
      .then(res => res.json())
      .then(data => setGeoData(data));
  }, []);

  useEffect(() => {
    const globe = globeRef.current;
    if (globe) {
      globe.controls().autoRotate = !selectedCountry;
      globe.controls().autoRotateSpeed = 0.5;
      globe.controls().enableZoom = true;
      globe.controls().minDistance = 150;
      globe.controls().maxDistance = 400;
      if (!selectedCountry) {
        globe.pointOfView({ altitude: 2.5 });
      }
    }
  }, [globeRef.current, selectedCountry]);

  // If a country is selected and we didn't just fly to it, let's fly to it if we know its coordinates.
  // react-globe.gl has a method pointOfView({ lat, lng }) but we need to calculate it. For now, pause rotation.
  
  const arcsData = useMemo(() => {
    return Array.from({ length: 15 }).map(() => ({
      startLat: (Math.random() - 0.5) * 180,
      startLng: (Math.random() - 0.5) * 360,
      endLat: (Math.random() - 0.5) * 180,
      endLng: (Math.random() - 0.5) * 360,
      color: Math.random() > 0.5 ? '#f43f5e' : '#6366f1'
    }));
  }, []);

  const getCountryColor = (name: string, isHovered: boolean, isSelected: boolean) => {
    const baseColor = COUNTRY_COLORS[name] || DEFAULT_COLOR;
    if (isSelected) {
      return '#6366f1'; // Indigo for selected
    }
    if (isHovered) {
      return '#ffffff'; // White highlight on hover
    }
    if (baseColor.startsWith('#')) {
      return `${baseColor}b3`; // Add opacity to hex
    }
    return baseColor;
  };

  const getStrokeColor = (name: string, isHovered: boolean, isSelected: boolean) => {
    if (isSelected) return '#818cf8';
    if (isHovered) return '#ffffff';
    return COUNTRY_COLORS[name] || DEFAULT_STROKE;
  };

  return (
    <div
      ref={containerRef}
      className="w-full h-full cursor-grab active:cursor-grabbing flex items-center justify-center"
    >
      {dimensions.width > 0 && <Globe
        ref={globeRef}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="rgba(0,0,0,0)"
        showAtmosphere={true}
        atmosphereColor="#6366f1"
        atmosphereAltitude={0.15}
        globeMaterial={new THREE.MeshPhongMaterial({ color: '#020817', roughness: 0.8 })}
        polygonsData={geoData ? geoData.features : []}
        polygonAltitude={d => {
          const isSelected = d.properties.name === selectedCountry;
          const isHovered = d === hoveredCountry;
          return isSelected ? 0.08 : (isHovered ? 0.04 : 0.01);
        }}
        polygonCapColor={d => getCountryColor(d.properties.name, d === hoveredCountry, d.properties.name === selectedCountry)}
        polygonSideColor={() => 'rgba(0, 0, 0, 0.2)'}
        polygonStrokeColor={d => getStrokeColor(d.properties.name, d === hoveredCountry, d.properties.name === selectedCountry)}
        onPolygonHover={setHoveredCountry}
        onPolygonClick={(d: any) => onCountryClick(d.properties.name)}
        polygonLabel={({ properties: d }: any) => `
          <div class="bg-slate-900/90 border border-indigo-500/50 backdrop-blur-md px-3 py-1.5 rounded-lg text-white font-sans pointer-events-none shadow-2xl relative z-50">
            <div class="text-[10px] uppercase font-bold tracking-widest text-indigo-400 mb-0.5">Region Impact</div>
            <div class="text-sm font-medium whitespace-nowrap">${d.name}</div>
          </div>
        `}
        arcsData={arcsData}
        arcColor="color"
        arcDashLength={0.4}
        arcDashGap={0.2}
        arcDashAnimateTime={2000}
        arcsTransitionDuration={0}
      />}
    </div>
  );
};

