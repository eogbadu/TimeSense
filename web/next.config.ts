import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Hide the on-screen Next.js dev-tools indicator (the "N" badge in the corner).
  devIndicators: false,
  // Emit a self-contained server (.next/standalone) for a small production container image.
  output: "standalone",
};

export default nextConfig;
