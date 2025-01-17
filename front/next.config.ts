import { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },

  webpack: (config) => {
    // Add TypeScript extensions if needed
    config.resolve.extensions.push(".ts", ".tsx");
    console.log("Alias:", config.resolve.alias);
    return config;
  },

  transpilePackages: ['recharts'],
};

export default nextConfig;
