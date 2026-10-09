"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import { useEffect, useRef, useState } from "react";

export type PontoLocal = {
  local: number;
  nome: string;
  lat: number;
  lon: number;
  resumo: string; // ex.: "Seções 18, 19 · mais votado: ..."
};

// OpenFreeMap: tiles gratuitos e sem chave, com atribuição ao OpenStreetMap (D8).
const ESTILO = "https://tiles.openfreemap.org/styles/positron";

/** Mapa dos locais de votação. A tabela da página é a alternativa acessível. */
export function MapaLocais({ pontos }: { pontos: PontoLocal[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    if (!ref.current || pontos.length === 0) return;
    let mapa: import("maplibre-gl").Map | undefined;
    let cancelado = false;

    import("maplibre-gl")
      .then((maplibregl) => {
        if (cancelado || !ref.current) return;
        const limites = new maplibregl.LngLatBounds();
        pontos.forEach((p) => limites.extend([p.lon, p.lat]));
        const m = new maplibregl.Map({
          container: ref.current,
          style: ESTILO,
          bounds: limites,
          fitBoundsOptions: { padding: 48, maxZoom: 15 },
          attributionControl: { compact: true },
          cooperativeGestures: true,
        });
        mapa = m;
        m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
        for (const p of pontos) {
          const el = document.createElement("div");
          el.className = "size-3 rounded-full border-2 border-papel bg-ocre shadow";
          el.setAttribute("aria-hidden", "true");
          new maplibregl.Marker({ element: el })
            .setLngLat([p.lon, p.lat])
            .setPopup(
              new maplibregl.Popup({ offset: 10, closeButton: false }).setDOMContent(
                popup(p.nome, p.resumo),
              ),
            )
            .addTo(m);
        }
        // Falhas pontuais (um tile, um ícone) não invalidam o mapa: só avisa se ele não carregar.
        m.on("error", () => {
          if (!m.loaded()) setErro(true);
        });
        m.on("load", () => setErro(false));
      })
      .catch(() => setErro(true));

    return () => {
      cancelado = true;
      mapa?.remove();
    };
  }, [pontos]);

  if (pontos.length === 0) {
    return <p className="text-sm text-tinta-2">Sem coordenadas dos locais de votação nesta eleição.</p>;
  }
  return (
    <figure>
      <div
        ref={ref}
        role="img"
        aria-label={`Mapa com ${pontos.length} locais de votação de Itajubá; a lista completa está na tabela abaixo.`}
        className="h-96 w-full border border-regua bg-papel-2"
      />
      {erro ? (
        <figcaption className="mt-2 text-xs text-tinta-2">
          Não foi possível carregar o mapa; os locais estão listados na tabela.
        </figcaption>
      ) : null}
    </figure>
  );
}

function popup(nome: string, resumo: string): HTMLElement {
  const div = document.createElement("div");
  div.className = "font-sans text-xs text-[#1c1913]";
  const t = document.createElement("strong");
  t.textContent = nome;
  const r = document.createElement("p");
  r.textContent = resumo;
  div.append(t, r);
  return div;
}
