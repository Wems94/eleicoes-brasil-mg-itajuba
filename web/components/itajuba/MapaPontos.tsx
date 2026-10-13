"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import type { FeatureCollection, Point } from "geojson";
import type { GeoJSONSource, Map as MapaLibre } from "maplibre-gl";
import { useEffect, useRef, useState } from "react";

import { LOCALE_PT, carregarMaplibre } from "@/lib/maplibre";

export type Ponto = {
  id: string;
  nome: string;
  lat: number;
  lon: number;
  cor: string;
  raio: number;
  linhas: string[]; // texto do tooltip, abaixo do nome
};

// OpenFreeMap: tiles gratuitos e sem chave, com atribuição ao OpenStreetMap (D8).
const ESTILO = "https://tiles.openfreemap.org/styles/dark";

/**
 * Caixa inicial: os pontos mais próximos do centro (mediana), para abrir na área
 * urbana; os distritos rurais ficam a um zoom de distância.
 */
export function caixaInicial(pontos: { lat: number; lon: number }[], fracao = 0.8): [number, number, number, number] | null {
  if (!pontos.length) return null;
  const mediana = (xs: number[]) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];
  const c = [mediana(pontos.map((p) => p.lon)), mediana(pontos.map((p) => p.lat))];
  const perto = [...pontos]
    .sort((a, b) => Math.hypot(a.lon - c[0], a.lat - c[1]) - Math.hypot(b.lon - c[0], b.lat - c[1]))
    .slice(0, Math.max(1, Math.ceil(pontos.length * fracao)));
  const lons = perto.map((p) => p.lon);
  const lats = perto.map((p) => p.lat);
  return [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)];
}

function geojson(pontos: Ponto[]): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: pontos.map((p) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [p.lon, p.lat] },
      properties: { id: p.id, cor: p.cor, raio: p.raio },
    })),
  };
}

/**
 * Mapa de ruas de Itajubá com um círculo por ponto (local de votação ou bairro).
 * Decorativo para leitores de tela: a tabela ao lado traz os mesmos números.
 */
export function MapaPontos({
  pontos,
  selecionado,
  onSelecionar,
  rotulo,
}: {
  pontos: Ponto[];
  selecionado: string | null;
  onSelecionar: (id: string | null) => void;
  rotulo: string;
}) {
  const container = useRef<HTMLDivElement>(null);
  const mapa = useRef<MapaLibre | null>(null);
  const pontosRef = useRef(pontos);
  pontosRef.current = pontos;
  const aoSelecionar = useRef(onSelecionar);
  aoSelecionar.current = onSelecionar;
  const [pronto, setPronto] = useState(false);
  const [erro, setErro] = useState(false);
  const [dica, setDica] = useState<{ x: number; y: number; ponto: Ponto } | null>(null);

  useEffect(() => {
    let cancelado = false;
    let m: MapaLibre | undefined;
    carregarMaplibre()
      .then((maplibregl) => {
        if (cancelado || !container.current) return;
        const caixa = caixaInicial(pontosRef.current);
        m = new maplibregl.Map({
          container: container.current,
          style: ESTILO,
          bounds: caixa ?? undefined,
          center: caixa ? undefined : [-45.45, -22.42],
          zoom: caixa ? undefined : 12,
          fitBoundsOptions: { padding: 32, maxZoom: 15 },
          attributionControl: { compact: true },
          cooperativeGestures: true,
          locale: LOCALE_PT,
        });
        mapa.current = m;
        m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
        m.on("load", () => {
          setErro(false);
          m!.addSource("pontos", { type: "geojson", data: geojson(pontosRef.current), promoteId: "id" });
          m!.addLayer({
            id: "pontos",
            type: "circle",
            source: "pontos",
            paint: {
              "circle-color": ["get", "cor"],
              "circle-radius": ["get", "raio"],
              "circle-opacity": ["case", ["boolean", ["feature-state", "apagado"], false], 0.25, 0.9],
              "circle-stroke-color": "#ffffff",
              "circle-stroke-width": [
                "case",
                ["boolean", ["feature-state", "selecionado"], false],
                3,
                ["boolean", ["feature-state", "hover"], false],
                2,
                0.75,
              ],
              "circle-stroke-opacity": ["case", ["boolean", ["feature-state", "apagado"], false], 0.3, 0.9],
            },
          });
          setPronto(true);
        });
        let hover: string | null = null;
        const definirHover = (id: string | null) => {
          if (hover === id) return;
          if (hover) m!.setFeatureState({ source: "pontos", id: hover }, { hover: false });
          hover = id;
          if (id) m!.setFeatureState({ source: "pontos", id }, { hover: true });
        };
        m.on("mousemove", "pontos", (ev) => {
          const id = ev.features?.[0]?.properties?.id as string | undefined;
          const ponto = pontosRef.current.find((p) => p.id === id);
          definirHover(id ?? null);
          m!.getCanvas().style.cursor = "pointer";
          setDica(ponto ? { x: ev.point.x, y: ev.point.y, ponto } : null);
        });
        m.on("mouseleave", "pontos", () => {
          definirHover(null);
          m!.getCanvas().style.cursor = "";
          setDica(null);
        });
        m.on("click", (ev) => {
          const f = m!.queryRenderedFeatures(ev.point, { layers: ["pontos"] })[0];
          const id = (f?.properties?.id as string | undefined) ?? null;
          aoSelecionar.current(id);
        });
        // Falhas pontuais (um tile, um ícone) não invalidam o mapa: só avisa se ele não carregar.
        m.on("error", () => {
          if (!m!.loaded()) setErro(true);
        });
      })
      .catch(() => setErro(true));
    return () => {
      cancelado = true;
      m?.remove();
      mapa.current = null;
    };
  }, []);

  // dados (cor, raio, conjunto de pontos)
  useEffect(() => {
    const m = mapa.current;
    if (!pronto || !m) return;
    (m.getSource("pontos") as GeoJSONSource).setData(geojson(pontos));
  }, [pronto, pontos]);

  // seleção: destaca o ponto, apaga os outros e aproxima nele
  useEffect(() => {
    const m = mapa.current;
    if (!pronto || !m) return;
    const alvo = pontos.find((p) => p.id === selecionado);
    if (alvo) m.easeTo({ center: [alvo.lon, alvo.lat], zoom: Math.max(m.getZoom(), 13.5), duration: 500 });
    for (const p of pontos)
      m.setFeatureState(
        { source: "pontos", id: p.id },
        { selecionado: p.id === selecionado, apagado: selecionado != null && p.id !== selecionado },
      );
  }, [pronto, pontos, selecionado]);

  return (
    <figure className="relative">
      <div
        ref={container}
        role="img"
        aria-label={rotulo}
        className="h-[26rem] w-full overflow-hidden rounded-xl border border-borda bg-realce"
      />
      {dica ? (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute z-10 max-w-64 rounded-lg border border-borda bg-[#12101c]/95 px-3 py-2 text-xs shadow-lg"
          style={{ left: dica.x + 14, top: dica.y + 14 }}
        >
          <p className="font-semibold text-texto">{dica.ponto.nome}</p>
          {dica.ponto.linhas.map((l) => (
            <p key={l} className="num text-texto-2">
              {l}
            </p>
          ))}
        </div>
      ) : null}
      {erro ? (
        <figcaption className="mt-2 text-xs text-texto-2">
          Não foi possível carregar o mapa; os números estão na tabela.
        </figcaption>
      ) : null}
    </figure>
  );
}

/** Grupo de botões no estilo das pílulas do mapa do Brasil. */
export function Pilulas<T extends string | number>({
  rotulo,
  opcoes,
  valor,
  onMudar,
}: {
  rotulo: string;
  opcoes: readonly (readonly [T, string])[];
  valor: T;
  onMudar: (v: T) => void;
}) {
  return (
    <div role="group" aria-label={rotulo} className="inline-flex flex-wrap gap-1 rounded-xl border border-borda bg-white/[0.03] p-1">
      {opcoes.map(([v, nome]) => (
        <button
          key={String(v)}
          type="button"
          aria-pressed={valor === v}
          onClick={() => onMudar(v)}
          className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
            valor === v ? "bg-acento-claro text-texto ring-1 ring-acento/40" : "text-texto-2 hover:bg-realce hover:text-texto"
          }`}
        >
          {nome}
        </button>
      ))}
    </div>
  );
}
