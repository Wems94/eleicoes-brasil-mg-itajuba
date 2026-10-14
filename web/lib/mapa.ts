// Lógica pura do mapa municipal (capability mapa-municipal): cores de cada município,
// legenda, estado na URL e enquadramento. O componente só desenha o que sai daqui.
import {
  type Cor,
  FAIXAS_ABSTENCAO,
  FAIXAS_VENCEDOR,
  NEUTRO,
  type Tema,
  corAbstencao,
  corIntensidade,
  coresDaDisputa,
  rotuloFaixas,
} from "./partidos";
import { CARGOS_MAPA, type CamadaMapa, type CargoMapa, type CelulaMapa, type VotavelMapa } from "./tipos";

export type Camada = "vencedor" | "abstencao";

export type EstadoMapa = {
  cargo: CargoMapa;
  camada: Camada;
  uf: string | null;
  mun: string | null; // código IBGE
};

// --- cores ---------------------------------------------------------------------------

/** Presidente é uma disputa nacional; os demais cargos, uma disputa por UF. */
export const disputaNacional = (cargo: CargoMapa) => cargo === "presidente";

/**
 * Cor de cada votável vencedor, por recorte de disputa (UF ou "BR"). A ordem de
 * prioridade das cores é o número de municípios vencidos no recorte.
 */
export function coresPorRecorte(
  camada: CamadaMapa,
  ufDe: (codigo: string) => string | undefined,
): Map<string, Map<number, Cor>> {
  const nacional = disputaNacional(camada.cargo);
  const contagem = new Map<string, Map<number, number>>();
  for (const [codigo, [idx]] of Object.entries(camada.municipios)) {
    if (idx < 0) continue;
    const recorte = nacional ? "BR" : (ufDe(codigo) ?? "");
    const c = contagem.get(recorte) ?? new Map<number, number>();
    c.set(idx, (c.get(idx) ?? 0) + 1);
    contagem.set(recorte, c);
  }
  const out = new Map<string, Map<number, Cor>>();
  for (const [recorte, c] of contagem) {
    const ordem = [...c].sort((a, b) => b[1] - a[1] || a[0] - b[0]).map(([i]) => i);
    const porSigla = coresDaDisputa(ordem.map((i) => camada.votaveis[i].partido));
    out.set(recorte, new Map(ordem.map((i) => [i, porSigla.get(camada.votaveis[i].partido ?? "")!])));
  }
  return out;
}

export function corDoMunicipio(
  celula: CelulaMapa | undefined,
  camada: Camada,
  cores: Map<number, Cor> | undefined,
  tema: Tema,
): string {
  if (!celula) return NEUTRO.semDados[tema];
  const [idx, pct, abst] = celula;
  if (camada === "abstencao") return abst == null ? NEUTRO.semDados[tema] : corAbstencao(abst / 100, tema);
  if (idx < 0) return NEUTRO.empate[tema];
  const cor = cores?.get(idx);
  return cor && pct != null ? corIntensidade(cor.fundo, pct / 100, tema) : NEUTRO.semDados[tema];
}

// --- legenda --------------------------------------------------------------------------

export type ItemLegenda = { cor: string; rotulo: string; detalhe?: string };

export function legendaVencedores(
  camada: CamadaMapa,
  cores: Map<string, Map<number, Cor>>,
  recorte: string | null,
): ItemLegenda[] {
  const recortes = recorte ? [recorte] : [...cores.keys()];
  const vistos = new Map<string, ItemLegenda & { n: number }>();
  for (const r of recortes) {
    for (const [idx, cor] of cores.get(r) ?? []) {
      const v = camada.votaveis[idx];
      const rotulo = rotuloVotavel(v, camada.por);
      const k = `${rotulo}|${cor.fundo}`;
      const atual = vistos.get(k);
      vistos.set(k, { cor: cor.fundo, rotulo, detalhe: v.partido ?? undefined, n: (atual?.n ?? 0) + 1 });
    }
  }
  return [...vistos.values()].sort((a, b) => a.rotulo.localeCompare(b.rotulo, "pt-BR"));
}

export function legendaFaixas(camada: Camada, tema: Tema): ItemLegenda[] {
  if (camada === "abstencao") {
    return rotuloFaixas(FAIXAS_ABSTENCAO).map((rotulo, i) => ({
      rotulo,
      cor: corAbstencao(FAIXAS_ABSTENCAO[i], tema),
    }));
  }
  // intensidade: tons de um cinza escuro, só para mostrar a escala
  return rotuloFaixas(FAIXAS_VENCEDOR).map((rotulo, i) => ({
    rotulo,
    cor: corIntensidade("#3d4350", FAIXAS_VENCEDOR[i], tema),
  }));
}

export function rotuloVotavel(v: VotavelMapa | undefined, por: "candidato" | "partido"): string {
  if (!v) return "—";
  if (por === "partido") return v.partido ?? "—";
  return v.nome ?? (v.numero != null ? `Nº ${v.numero}` : "—");
}

// --- estado na URL (hash) ---------------------------------------------------------------

export function lerHash(hash: string, padrao: EstadoMapa, cargos: readonly CargoMapa[]): EstadoMapa {
  const p = new URLSearchParams(hash.replace(/^#/, ""));
  const cargo = p.get("cargo") as CargoMapa | null;
  const camada = p.get("camada");
  const uf = p.get("uf");
  const mun = p.get("mun");
  return {
    cargo: cargo && cargos.includes(cargo) ? cargo : padrao.cargo,
    camada: camada === "abstencao" || camada === "vencedor" ? camada : padrao.camada,
    uf: uf && /^[A-Z]{2}$/.test(uf) ? uf : padrao.uf,
    mun: mun && /^\d{7}$/.test(mun) ? mun : padrao.mun,
  };
}

export function escreverHash(e: EstadoMapa, padrao: EstadoMapa): string {
  const p = new URLSearchParams();
  if (e.cargo !== padrao.cargo) p.set("cargo", e.cargo);
  if (e.camada !== padrao.camada) p.set("camada", e.camada);
  if (e.uf && e.uf !== padrao.uf) p.set("uf", e.uf);
  if (e.mun) p.set("mun", e.mun);
  const s = p.toString();
  return s ? `#${s}` : "";
}

export const cargoValido = (c: string): c is CargoMapa => (CARGOS_MAPA as readonly string[]).includes(c);

// --- geometria -------------------------------------------------------------------------

export type Caixa = [number, number, number, number]; // oeste, sul, leste, norte

/** Caixa envolvente de cada UF a partir dos polígonos (GeoJSON) dos municípios. */
export function caixasPorUf(
  feicoes: { properties: { uf: string | null }; geometry: GeoJSON.Geometry }[],
): Map<string, Caixa> {
  const out = new Map<string, Caixa>();
  const visitar = (uf: string, c: GeoJSON.Position) => {
    const b = out.get(uf) ?? [Infinity, Infinity, -Infinity, -Infinity];
    out.set(uf, [Math.min(b[0], c[0]), Math.min(b[1], c[1]), Math.max(b[2], c[0]), Math.max(b[3], c[1])]);
  };
  for (const f of feicoes) {
    const uf = f.properties.uf;
    if (!uf) continue;
    const g = f.geometry;
    const aneis =
      g.type === "Polygon" ? g.coordinates : g.type === "MultiPolygon" ? g.coordinates.flat() : [];
    for (const anel of aneis) for (const c of anel) visitar(uf, c);
  }
  return out;
}

export function unirCaixas(caixas: Iterable<Caixa>): Caixa | null {
  let b: Caixa | null = null;
  for (const c of caixas) {
    b = b ? [Math.min(b[0], c[0]), Math.min(b[1], c[1]), Math.max(b[2], c[2]), Math.max(b[3], c[3])] : c;
  }
  return b;
}

/** "62,37%" a partir do inteiro em centésimos dos arquivos do mapa. */
export const pctCem = (v: number | null): number | null => (v == null ? null : v / 100);
