/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker optimization
  output: 'standalone',
  
  // Disable telemetry in production
  telemetry: {
    enabled: false,
  },
  
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
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080',
  },
};

module.exports = nextConfig;
