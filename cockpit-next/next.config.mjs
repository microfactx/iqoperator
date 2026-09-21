import path from "path"
import { fileURLToPath } from "url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: { serverActions: { allowedOrigins: ["*"] } },
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  // Add path alias support (tsconfig paths are also applied by Next.js)
  webpack(config) {
    config.resolve.alias["@"] = __dirname
    return config
  },
}

export default nextConfig