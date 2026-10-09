import type { NextConfig } from "next";

// Site 100% estático (D8): todas as rotas são pré-geradas a partir dos snapshots.
const config: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default config;
