import { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*', // Proxy to Backend
      },
    ];
  },

  webpack: (config) => {
    // Add TypeScript extensions if needed
    config.resolve.extensions.push(".ts", ".tsx");
    console.log("Alias:", config.resolve.alias); // Debug to check alias paths
    return config;
  },
};

export default nextConfig;
