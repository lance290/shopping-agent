/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker optimization
  output: 'standalone',
  
  // Image optimization settings
  images: {
    remotePatterns: [],
    formats: ['image/avif', 'image/webp'],
  },
  
  // Strict mode for better error catching
  reactStrictMode: true,
  
  // Reduce size by removing source maps in production
  productionBrowserSourceMaps: false,
  
  // Compress responses
  compress: true,
  
  // Power optimizations
  poweredByHeader: false,
  
  // Environment variables exposed to browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL, 
  },
  // NOTE: We use Next.js API routes (/app/api/*/route.ts) instead of rewrites.
  // This allows BFF_URL to be read at RUNTIME, not build-time.
  // See: /app/api/out/route.ts, /app/api/rows/route.ts, etc.
};

module.exports = nextConfig;
