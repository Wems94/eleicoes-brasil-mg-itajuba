// Copia o worker do MapLibre para public/: no bundle do Next ele seria procurado ao
// lado do chunk (import.meta.url) e não existiria. Os mapas usam setWorkerUrl().
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const dist = path.dirname(require.resolve("maplibre-gl/dist/maplibre-gl.css"));
const destino = path.join(import.meta.dirname, "..", "public", "maplibre");
mkdirSync(destino, { recursive: true });
copyFileSync(path.join(dist, "maplibre-gl-worker.mjs"), path.join(destino, "maplibre-gl-worker.mjs"));
