import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  // Emit a self-contained server bundle for the production Docker image
  // (consumed by the Dockerfile `runner` stage).
  output: "standalone",
};

export default nextConfig;
