import type { NextConfig } from "next";

// Static export: Electron serves ./out through the app:// protocol (no Node server at runtime).
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  devIndicators: false,
};

export default nextConfig;
