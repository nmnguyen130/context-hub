import type { NextConfig } from "next";

const BACKEND_INTERNAL_URL = process.env.INTERNAL_API_URL || "http://backend:8000/api/v1";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${BACKEND_INTERNAL_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
