/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",          // enables Docker multi-stage copy
  reactStrictMode: true,
  poweredByHeader: false,        // hide framework fingerprint

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/:path*`,
      },
    ];
  },

  images: {
    domains: ["localhost"],
  },
};

module.exports = nextConfig;
