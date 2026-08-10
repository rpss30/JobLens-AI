import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit .next/standalone with a self-contained server.js and only the runtime
  // dependencies, so the production image does not ship node_modules.
  output: "standalone",

  // Caddy already applies zstd/gzip at the edge, so compressing here would
  // spend CPU on the one small server twice for the same bytes.
  compress: false,
};

export default nextConfig;
