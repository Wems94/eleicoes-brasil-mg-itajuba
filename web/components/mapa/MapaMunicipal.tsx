"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import type { FeatureCollection, Geometry, MultiLineString } from "geojson";
import type { GeoJSONSource, Map as MapaLibre } from "maplibre-gl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { feature, mesh } from "topojson-client";
import type { GeometryCollection, Topology } from "topojson-specification";

import { PainelMunicipio } from "@/components/mapa/PainelMunicipio";
import { TabelaMapa } from "@/components/mapa/TabelaMapa";
import { NOME_UF, numero, pct } from "@/lib/formato";
import { LOCALE_PT, carregarMaplibre } from "@/lib/maplibre";
import {
  type Caixa,
  type Camada,
  type EstadoMapa,
  caixasPorUf,
  corDoMunicipio,
  coresPorRecorte,
  disputaNacional,
  escreverHash,
  legendaFaixas,
  legendaVencedores,
  lerHash,
  pctCem,
  rotuloVotavel,
  unirCaixas,
} from "@/lib/mapa";
import { NEUTRO, SUPERFICIE, type Tema } from "@/lib/partidos";
import type { CamadaMapa, CargoMapa, DetalheUf } from "@/lib/tipos";

type Props = {
  ano: number;
  turno: number;
  cargos: { cargo: CargoMapa; nome: string }[];
  ufInicial?: string | null; // página da UF: abre já enquadrado nela
  fixarUf?: boolean; // na página da UF, o mapa não sai da UF
  itajuba: number | null; // código IBGE do deep dive
  fotos: Record<string, string>; // sq -> caminho da foto (só Presidente)
};

type PropsMunicipio = { codigo: string; nome: string | null; uf: string | null; cor?: string };
type Feicoes = FeatureCollection<Geometry, PropsMunicipio>;

// --- carga sob demanda, com cache por URL (a malha vem uma vez só) ----------------------

const cache = new Map<string, Promise<unknown>>();
function carregar<T>(url: string): Promise<T> {
  if (!cache.has(url)) {
    const p = fetch(url).then((r) => {
      if (!r.ok) throw new Error(`${r.status} ${url}`);
      return r.json();
    });
    p.catch(() => cache.delete(url)); // tenta de novo numa próxima vez
    cache.set(url, p);
  }
  return cache.get(url) as Promise<T>;
}

type Malha = { feicoes: Feicoes; ufs: MultiLineString; contorno: MultiLineString; caixas: Map<string, Caixa> };

async function carregarMalha(): Promise<Malha> {
  const topo = await carregar<Topology<{ municipios: GeometryCollection<{ nome: string | null; uf: string | null }> }>>(
    "/dados/geo/municipios.topo.json",
  );
  const obj = topo.objects.municipios;
  const fc = feature(topo, obj) as unknown as FeatureCollection<Geometry, { nome: string | null; uf: string | null }>;
  const feicoes: Feicoes = {
    type: "FeatureCollection",
    features: fc.features.map((f) => ({
      ...f,
      properties: { codigo: String(f.id), nome: f.properties.nome, uf: f.properties.uf },
    })),
  };
  type G = { properties?: { uf?: string | null } };
  return {
    feicoes,
    ufs: mesh(topo, obj, (a: G, b: G) => a !== b && a.properties?.uf !== b.properties?.uf),
    contorno: mesh(topo, obj, (a: G, b: G) => a === b),
    caixas: caixasPorUf(feicoes.features),
  };
}

// O site tem tema único escuro (globals.css); as funções de cor aceitam os dois.
const TEMA: Tema = "escuro";
const COR_LIMITE = { claro: "#ffffff", escuro: "#12101c" } as const;
const COR_LIMITE_UF = { claro: "#ffffff", escuro: "#d9d2ff" } as const;
const COR_DESTAQUE = { claro: "#0f172a", escuro: "#f5f3ff" } as const;

/** Mapa coroplético por município (capability mapa-municipal, decisão M5). */
export function MapaMunicipal({ ano, turno, cargos, ufInicial = null, fixarUf = false, itajuba, fotos }: Props) {
  const tema = TEMA;
  const padrao = useMemo<EstadoMapa>(
    () => ({ cargo: cargos[0]?.cargo ?? "presidente", camada: "vencedor", uf: ufInicial, mun: null }),
    [cargos, ufInicial],
  );
  const [estado, setEstado] = useState<EstadoMapa>(padrao);
  const [malha, setMalha] = useState<Malha | null>(null);
  const [camada, setCamada] = useState<CamadaMapa | null>(null);
  const [detalhe, setDetalhe] = useState<DetalheUf | null>(null);
  const [erro, setErro] = useState<"malha" | "camada" | "detalhe" | null>(null);
  const [dica, setDica] = useState<{ x: number; y: number; codigo: string } | null>(null);
  const [pronto, setPronto] = useState(false);
  const container = useRef<HTMLDivElement>(null);
  const mapa = useRef<MapaLibre | null>(null);
  const hover = useRef<string | null>(null);
  const selecionado = useRef<string | null>(null);
  const estadoRef = useRef(estado);
  estadoRef.current = estado;

  const listaCargos = useMemo(() => cargos.map((c) => c.cargo), [cargos]);
  const nomeCargo = cargos.find((c) => c.cargo === estado.cargo)?.nome ?? estado.cargo;
  const base = `/dados/${ano}/${turno}`;

  // estado inicial e navegação pelo hash (link compartilhado, voltar do navegador)
  useEffect(() => {
    const ler = () => {
      const e = lerHash(window.location.hash, padrao, listaCargos);
      setEstado(fixarUf ? { ...e, uf: padrao.uf } : e);
    };
    ler();
    window.addEventListener("hashchange", ler);
    return () => window.removeEventListener("hashchange", ler);
  }, [padrao, listaCargos, fixarUf]);

  useEffect(() => {
    const h = escreverHash(estado, padrao);
    if (h !== window.location.hash && !(h === "" && window.location.hash === "")) {
      window.history.replaceState(null, "", h || window.location.pathname + window.location.search);
    }
  }, [estado, padrao]);

  const mudar = useCallback((parcial: Partial<EstadoMapa>) => setEstado((e) => ({ ...e, ...parcial })), []);

  // dados
  useEffect(() => {
    carregarMalha()
      .then(setMalha)
      .catch(() => setErro("malha"));
  }, []);

  useEffect(() => {
    let vivo = true;
    setCamada(null);
    carregar<CamadaMapa>(`${base}/mapa/${estado.cargo}.json`)
      .then((c) => vivo && setCamada(c))
      .catch(() => vivo && setErro("camada"));
    return () => {
      vivo = false;
    };
  }, [base, estado.cargo]);

  const ufDoMunicipio = useMemo(() => {
    const m = new Map<string, string>();
    for (const f of malha?.feicoes.features ?? []) if (f.properties.uf) m.set(f.properties.codigo, f.properties.uf);
    return m;
  }, [malha]);
  const ufPainel = estado.mun ? (ufDoMunicipio.get(estado.mun) ?? null) : null;

  useEffect(() => {
    if (!estado.mun || !ufPainel) return;
    let vivo = true;
    setDetalhe(null);
    carregar<DetalheUf>(`${base}/municipios/${ufPainel}/${estado.cargo}.json`)
      .then((d) => vivo && setDetalhe(d))
      .catch(() => vivo && setErro("detalhe"));
    return () => {
      vivo = false;
    };
  }, [base, estado.cargo, estado.mun, ufPainel]);

  const cores = useMemo(
    () => (camada ? coresPorRecorte(camada, (k) => ufDoMunicipio.get(k)) : new Map()),
    [camada, ufDoMunicipio],
  );

  // mapa (uma vez, depois da malha)
  useEffect(() => {
    if (!malha || !container.current || mapa.current) return;
    let cancelado = false;
    carregarMaplibre()
      .then((maplibregl) => {
        if (cancelado || !container.current) return;
        const caixa = (estadoRef.current.uf && malha.caixas.get(estadoRef.current.uf)) || unirCaixas(malha.caixas.values())!;
        const m = new maplibregl.Map({
          container: container.current,
          style: { version: 8, sources: {}, layers: [] },
          bounds: caixa,
          fitBoundsOptions: { padding: 16 },
          attributionControl: false,
          cooperativeGestures: true,
          locale: LOCALE_PT,
          dragRotate: false,
          pitchWithRotate: false,
          renderWorldCopies: false,
          minZoom: 2,
          maxZoom: 11,
        });
        mapa.current = m;
        m.touchZoomRotate.disableRotation();
        m.on("load", () => {
          m.addSource("municipios", { type: "geojson", data: malha.feicoes, promoteId: "codigo" });
          m.addSource("ufs", { type: "geojson", data: { type: "Feature", properties: {}, geometry: malha.ufs } });
          m.addSource("contorno", { type: "geojson", data: { type: "Feature", properties: {}, geometry: malha.contorno } });
          m.addLayer({
            id: "mun-fill",
            type: "fill",
            source: "municipios",
            paint: { "fill-color": ["coalesce", ["get", "cor"], NEUTRO.semDados.claro], "fill-antialias": false },
          });
          m.addLayer({
            id: "mun-linha",
            type: "line",
            source: "municipios",
            paint: {
              "line-color": COR_LIMITE.claro,
              "line-opacity": 0.85,
              "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.15, 5, 0.4, 8, 0.9],
            },
          });
          m.addLayer({
            id: "uf-linha",
            type: "line",
            source: "ufs",
            paint: {
              "line-color": COR_LIMITE_UF.claro,
              "line-opacity": 0.75,
              "line-width": ["interpolate", ["linear"], ["zoom"], 3, 0.9, 7, 2.2],
            },
          });
          m.addLayer({
            id: "contorno-linha",
            type: "line",
            source: "contorno",
            paint: { "line-color": "#a78bfa", "line-width": 1, "line-opacity": 0.45 },
          });
          m.addLayer({
            id: "mun-destaque",
            type: "line",
            source: "municipios",
            paint: {
              "line-color": COR_DESTAQUE.claro,
              "line-width": [
                "case",
                ["boolean", ["feature-state", "selecionado"], false],
                2.6,
                ["boolean", ["feature-state", "hover"], false],
                1.6,
                0,
              ],
            },
          });
          setPronto(true);
        });

        const definirHover = (codigo: string | null) => {
          if (hover.current === codigo) return;
          if (hover.current) m.setFeatureState({ source: "municipios", id: hover.current }, { hover: false });
          hover.current = codigo;
          if (codigo) m.setFeatureState({ source: "municipios", id: codigo }, { hover: true });
        };
        m.on("mousemove", "mun-fill", (ev) => {
          const f = ev.features?.[0];
          if (!f) return;
          const codigo = String(f.properties.codigo);
          definirHover(codigo);
          m.getCanvas().style.cursor = "pointer";
          setDica({ x: ev.point.x, y: ev.point.y, codigo });
        });
        m.on("mouseleave", "mun-fill", () => {
          definirHover(null);
          m.getCanvas().style.cursor = "";
          setDica(null);
        });
        m.on("click", "mun-fill", (ev) => {
          const f = ev.features?.[0];
          if (!f) return;
          const codigo = String(f.properties.codigo);
          const uf = f.properties.uf as string | null;
          const atual = estadoRef.current;
          setDica(null);
          if (!uf) return;
          if (atual.uf !== uf) {
            if (fixarUf) return; // página da UF: municípios de fora não abrem
            setEstado((e) => ({ ...e, uf, mun: atual.uf ? codigo : null }));
          } else {
            setEstado((e) => ({ ...e, mun: codigo }));
          }
        });
      })
      .catch(() => setErro("malha"));
    return () => {
      cancelado = true;
    };
  }, [malha, fixarUf]);

  useEffect(
    () => () => {
      mapa.current?.remove();
      mapa.current = null;
    },
    [],
  );

  // cores (troca de cargo, de camada ou de tema: só setData, a malha não é baixada de novo)
  useEffect(() => {
    const m = mapa.current;
    if (!pronto || !m || !malha) return;
    const recorteDe = (uf: string | null) => (camada && disputaNacional(camada.cargo) ? "BR" : (uf ?? ""));
    const dados: Feicoes = {
      type: "FeatureCollection",
      features: malha.feicoes.features.map((f) => ({
        ...f,
        properties: {
          ...f.properties,
          cor: camada
            ? corDoMunicipio(camada.municipios[f.properties.codigo], estado.camada, cores.get(recorteDe(f.properties.uf)), tema)
            : NEUTRO.semDados[tema],
        },
      })),
    };
    (m.getSource("municipios") as GeoJSONSource).setData(dados);
    m.setPaintProperty("mun-linha", "line-color", COR_LIMITE[tema]);
    m.setPaintProperty("uf-linha", "line-color", COR_LIMITE_UF[tema]);
    m.setPaintProperty("mun-destaque", "line-color", COR_DESTAQUE[tema]);
  }, [pronto, malha, camada, cores, estado.camada, tema]);

  // UF aberta: enquadra e esmaece o resto
  useEffect(() => {
    const m = mapa.current;
    if (!pronto || !m || !malha) return;
    const caixa = (estado.uf && malha.caixas.get(estado.uf)) || unirCaixas(malha.caixas.values());
    if (caixa) m.fitBounds(caixa, { padding: 24, duration: 600 });
    m.setPaintProperty(
      "mun-fill",
      "fill-opacity",
      estado.uf ? ["case", ["==", ["get", "uf"], estado.uf], 1, 0.28] : 1,
    );
  }, [pronto, malha, estado.uf]);

  // município selecionado
  useEffect(() => {
    const m = mapa.current;
    if (!pronto || !m) return;
    if (selecionado.current) m.setFeatureState({ source: "municipios", id: selecionado.current }, { selecionado: false });
    selecionado.current = estado.mun;
    if (estado.mun) m.setFeatureState({ source: "municipios", id: estado.mun }, { selecionado: true });
  }, [pronto, estado.mun, camada]);

  const zoom = (d: number) => mapa.current?.zoomTo((mapa.current?.getZoom() ?? 4) + d, { duration: 250 });
  const enquadrar = () => {
    const caixa = (estado.uf && malha?.caixas.get(estado.uf)) || (malha && unirCaixas(malha.caixas.values()));
    if (caixa) mapa.current?.fitBounds(caixa, { padding: 24, duration: 400 });
  };

  const municipiosDaUf = useMemo(
    () =>
      estado.uf && malha
        ? malha.feicoes.features
            .filter((f) => f.properties.uf === estado.uf)
            .map((f) => ({ codigo: f.properties.codigo, nome: f.properties.nome ?? f.properties.codigo }))
            .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"))
        : [],
    [estado.uf, malha],
  );
  const nomeMunicipio = (codigo: string) =>
    malha?.feicoes.features.find((f) => f.properties.codigo === codigo)?.properties.nome ?? codigo;

  const recorteLegenda = camada && !disputaNacional(camada.cargo) ? estado.uf : null;
  const titulo = estado.uf
    ? `${NOME_UF[estado.uf] ?? estado.uf} · ${numero(municipiosDaUf.length)} municípios · clique num município para ver as zonas`
    : `Brasil · ${numero(malha?.feicoes.features.length ?? 5570)} municípios · clique num estado para abrir`;

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div role="group" aria-label="Cargo" className="inline-flex flex-wrap gap-1 rounded-xl border border-borda bg-white/[0.03] p-1">
          {cargos.map((c) => (
            <button
              key={c.cargo}
              type="button"
              aria-pressed={estado.cargo === c.cargo}
              onClick={() => mudar({ cargo: c.cargo })}
              className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                estado.cargo === c.cargo ? "bg-acento-claro text-texto ring-1 ring-acento/40" : "text-texto-2 hover:bg-realce hover:text-texto"
              }`}
            >
              {c.nome}
            </button>
          ))}
        </div>
        <div role="group" aria-label="Camada" className="inline-flex gap-1 rounded-xl border border-borda bg-white/[0.03] p-1">
          {(
            [
              ["vencedor", "Mais votado"],
              ["abstencao", "Abstenção"],
            ] as [Camada, string][]
          ).map(([k, rotulo]) => (
            <button
              key={k}
              type="button"
              aria-pressed={estado.camada === k}
              onClick={() => mudar({ camada: k })}
              className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                estado.camada === k ? "bg-acento-claro text-texto ring-1 ring-acento/40" : "text-texto-2 hover:bg-realce hover:text-texto"
              }`}
            >
              {rotulo}
            </button>
          ))}
        </div>
      </div>

      <div className={`grid items-start gap-4 ${estado.mun ? "lg:grid-cols-[minmax(0,1fr)_24rem]" : ""}`}>
        <figure className="min-w-0">
          <figcaption className="mb-2 text-sm font-semibold">{titulo}</figcaption>
          <div className="relative">
            <div
              ref={container}
              role="img"
              aria-label={`Mapa dos municípios: ${nomeCargo}, ${estado.camada === "abstencao" ? "abstenção" : "mais votado"}. A tabela abaixo traz os mesmos dados.`}
              className="h-[min(78vh,40rem)] w-full overflow-hidden rounded-xl"
              style={{ background: SUPERFICIE[tema] }}
            />
            {!pronto || !camada ? (
              <p className="absolute inset-0 flex items-center justify-center text-sm text-texto-2" aria-live="polite">
                {erro === "malha" || erro === "camada" ? "Não foi possível carregar o mapa; use a tabela abaixo." : "Carregando o mapa…"}
              </p>
            ) : null}
            <div className="absolute right-2 top-2 flex flex-col gap-2">
              {[
                ["+", "Aproximar", () => zoom(1)],
                ["−", "Afastar", () => zoom(-1)],
                ["⤢", estado.uf ? "Enquadrar a UF" : "Enquadrar o Brasil", enquadrar],
              ].map(([s, rotulo, fn]) => (
                <button
                  key={rotulo as string}
                  type="button"
                  onClick={fn as () => void}
                  aria-label={rotulo as string}
                  title={rotulo as string}
                  className="flex size-10 items-center justify-center rounded-xl border border-borda bg-superficie text-lg font-semibold shadow-sm hover:bg-realce"
                >
                  {s as string}
                </button>
              ))}
            </div>
            {estado.uf && !fixarUf ? (
              <button
                type="button"
                onClick={() => mudar({ uf: null, mun: null })}
                className="absolute left-2 top-2 rounded-xl border border-borda bg-superficie px-3 py-2 text-sm font-medium shadow-sm hover:bg-realce"
              >
                ← Brasil
              </button>
            ) : null}
            {dica && camada ? <Dica {...dica} camada={camada} modo={estado.camada} malha={malha} /> : null}
          </div>

          {camada ? (
            <Legenda camada={camada} modo={estado.camada} cores={cores} recorte={recorteLegenda} tema={tema} />
          ) : null}
          {camada?.exterior && estado.cargo === "presidente" ? (
            <p className="mt-2 text-xs text-texto-3">
              Exterior (sem geometria): {rotuloVotavel(camada.votaveis[camada.exterior[0]], camada.por)}{" "}
              {camada.votaveis[camada.exterior[0]]?.partido} ({pct(pctCem(camada.exterior[1]))}) · abstenção{" "}
              {pct(pctCem(camada.exterior[2]))}
            </p>
          ) : null}
          {camada ? (
            <TabelaMapa
              camada={camada}
              modo={estado.camada}
              uf={estado.uf}
              municipios={municipiosDaUf}
              onAbrirUf={(uf) => mudar({ uf, mun: null })}
              onAbrirMunicipio={(codigo) => mudar({ mun: codigo })}
            />
          ) : null}
        </figure>

        {estado.mun && ufPainel ? (
          <PainelMunicipio
            ano={ano}
            turno={turno}
            codigo={estado.mun}
            uf={ufPainel}
            nomeMunicipio={nomeMunicipio(estado.mun)}
            nomeCargo={nomeCargo}
            detalhe={detalhe?.uf === ufPainel && detalhe.cargo === estado.cargo ? detalhe : null}
            erro={erro === "detalhe"}
            fotos={fotos}
            itajuba={itajuba}
            onFechar={() => mudar({ mun: null })}
          />
        ) : null}
      </div>
    </div>
  );
}

function Dica({
  x,
  y,
  codigo,
  camada,
  modo,
  malha,
}: {
  x: number;
  y: number;
  codigo: string;
  camada: CamadaMapa;
  modo: Camada;
  malha: Malha | null;
}) {
  const f = malha?.feicoes.features.find((g) => g.properties.codigo === codigo);
  const celula = camada.municipios[codigo];
  const v = celula && celula[0] >= 0 ? camada.votaveis[celula[0]] : undefined;
  return (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-10 max-w-64 rounded-lg border border-borda bg-superficie px-3 py-2 text-xs shadow-lg"
      style={{ left: x + 14, top: y + 14 }}
    >
      <p className="font-semibold">
        {f?.properties.nome} <span className="font-normal text-texto-3">{f?.properties.uf}</span>
      </p>
      {!celula ? (
        <p className="text-texto-2">Sem disputa neste turno</p>
      ) : modo === "abstencao" ? (
        <p className="num">Abstenção {pct(pctCem(celula[2]))}</p>
      ) : celula[0] < 0 ? (
        <p>Empate · {pct(pctCem(celula[1]))}</p>
      ) : (
        <p>
          {rotuloVotavel(v, camada.por)}
          {camada.por === "candidato" && v?.partido ? ` (${v.partido})` : ""} ·{" "}
          <span className="num">{pct(pctCem(celula[1]))}</span>
        </p>
      )}
    </div>
  );
}

function Legenda({
  camada,
  modo,
  cores,
  recorte,
  tema,
}: {
  camada: CamadaMapa;
  modo: Camada;
  cores: ReturnType<typeof coresPorRecorte>;
  recorte: string | null;
  tema: Tema;
}) {
  const faixas = legendaFaixas(modo, tema);
  const itens = modo === "vencedor" ? legendaVencedores(camada, cores, recorte) : [];
  return (
    <div className="mt-3 space-y-2 text-sm">
      {itens.length ? (
        <ul className="flex flex-wrap gap-x-4 gap-y-1.5" aria-label="Legenda: vencedores">
          {itens.map((i) => (
            <li key={`${i.rotulo}-${i.cor}`} className="flex items-center gap-1.5">
              <span className="size-3 rounded" style={{ background: i.cor }} aria-hidden="true" />
              <span className="font-medium">{i.rotulo}</span>
              {camada.por === "candidato" && i.detalhe ? <span className="text-texto-3">{i.detalhe}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-texto-2">
        <span>{modo === "abstencao" ? "Abstenção sobre os aptos:" : "% dos válidos do vencedor:"}</span>
        {faixas.map((f) => (
          <span key={f.rotulo} className="flex items-center gap-1">
            <span className="h-3 w-5 rounded-sm" style={{ background: f.cor }} aria-hidden="true" />
            {f.rotulo}
          </span>
        ))}
        {modo === "vencedor" ? (
          <span className="flex items-center gap-1">
            <span className="h-3 w-5 rounded-sm" style={{ background: NEUTRO.empate[tema] }} aria-hidden="true" />
            empate
          </span>
        ) : null}
        <span className="flex items-center gap-1">
          <span className="h-3 w-5 rounded-sm" style={{ background: NEUTRO.semDados[tema] }} aria-hidden="true" />
          sem disputa neste turno
        </span>
      </div>
    </div>
  );
}
