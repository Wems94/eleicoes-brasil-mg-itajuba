// Carrega o MapLibre no navegador já apontando para o worker em public/maplibre
// (copiado por scripts/copiar-maplibre.mjs; a versão na URL evita cache antigo).
export async function carregarMaplibre() {
  const maplibregl = await import("maplibre-gl");
  maplibregl.setWorkerUrl(`/maplibre/maplibre-gl-worker.mjs?v=${maplibregl.getVersion()}`);
  return maplibregl;
}

/** Textos da interface do MapLibre em português. */
export const LOCALE_PT = {
  "CooperativeGesturesHandler.WindowsHelpText": "Use Ctrl + rolagem para aproximar o mapa",
  "CooperativeGesturesHandler.MacHelpText": "Use ⌘ + rolagem para aproximar o mapa",
  "CooperativeGesturesHandler.MobileHelpText": "Use dois dedos para mover o mapa",
  "NavigationControl.ZoomIn": "Aproximar",
  "NavigationControl.ZoomOut": "Afastar",
};
