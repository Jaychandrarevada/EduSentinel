/** @type {import('next').NextConfig} */
const nextConfig = {
  // "standalone" output is used by Docker only; Vercel manages its own build
  ...(process.env.BUILD_STANDALONE === "true" ? { output: "standalone" } : {}),
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
