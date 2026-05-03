import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // `react-globe.gl` and `three` ship as ESM but transpile poorly through
  // Next's default rules — listing them here forces SWC to rewrite their
  // imports correctly for both server bundles (it's still rendered client-only)
  // and the client bundle.
  transpilePackages: ["three", "react-globe.gl"],
};

export default nextConfig;
