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
    // This is used for client-side calls if needed, though mostly we use rewrites
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL, 
  },

  async rewrites() {
    // In production (Railway), BFF_URL should be set to the private service URL
    // e.g. http://bff.railway.internal:8080
    const bffUrl = process.env.BFF_URL || 'http://localhost:8080';
    return [
      {
        source: '/api/:path*',
        destination: `${bffUrl}/api/:path*`, // Proxy to BFF
      },
    ];
  },
};

module.exports = nextConfig;
