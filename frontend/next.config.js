/** @type {import('next').NextConfig} */

// The browser always calls same-origin `/api/*`; Next rewrites proxy those
// requests to the backend API. On Vercel, set API_PROXY_TARGET (or
// NEXT_PUBLIC_API_URL) in the project's environment variables to the
// deployed backend URL. Falls back to the local dev server.
const API_TARGET =
  process.env.API_PROXY_TARGET ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_TARGET}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
