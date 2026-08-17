import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker
  output: 'standalone',
  
  // Optimize for production
  experimental: {
    optimizePackageImports: ['lucide-react', 'framer-motion']
  },
  
  // Image optimization
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.amazonaws.com',  // legacy AWS S3 URLs in old history rows
      },
      {
        protocol: 'https',
        hostname: '**.r2.cloudflarestorage.com',  // Cloudflare R2 direct API
      },
      {
        protocol: 'https',
        hostname: '**.r2.dev',  // Cloudflare R2 public bucket CDN
      },
    ],
  },
};

export default nextConfig;
