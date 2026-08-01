/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  reactStrictMode: true,
  swcMinify: true,
  
  // Enable API proxy to backend
  rewrites: async () => {
    return {
      fallback: [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/api/:path*',
        },
      ],
    };
  },
};

module.exports = nextConfig;
