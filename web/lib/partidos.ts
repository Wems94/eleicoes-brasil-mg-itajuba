// Cores partidárias (capability cores-partidarias, decisão M6).
//
// A cor segue o partido, em todo o site. Cada disputa exibida (cargo × eleição ×
// recorte) passa pelos partidos em ordem de votos: se um partido ficar perto demais
// (ΔE em OKLab) de outro já colorido, a luminosidade dele é ajustada, mantendo o
// matiz. A cor nunca é a única pista: legenda, dica e tabela trazem a sigla.

export type Cor = { fundo: string; texto: string };

// Cores de identidade usuais na imprensa, por sigla (como aparece em cada ano).
// Siglas antigas e renomeadas ficam como entradas próprias, sem fundir partidos.
export const PALETA: Readonly<Record<string, string>> = {
  PT: "#c8102e",
  "PC do B": "#9b1b1f",
  PCdoB: "#9b1b1f",
  PSOL: "#f2b705",
  PSTU: "#b71c1c",
  PCO: "#7b241c",
  PCB: "#922b21",
  UP: "#a93226",
  REDE: "#2bb5a9",
  PV: "#2f9e44",
  PSB: "#e8a100",
  PDT: "#e4572e",
  CIDADANIA: "#e0218a",
  PPS: "#e0218a",
  MDB: "#3e8e41",
  PMDB: "#3e8e41",
  PSDB: "#0a78d1",
  PSD: "#f0a830",
  PL: "#1b3a8c",
  PR: "#1b3a8c",
  PSL: "#1e7145",
  "UNIÃO": "#2d5fb4",
  DEM: "#7cb342",
  PP: "#4169b1",
  REPUBLICANOS: "#00838f",
  PRB: "#00838f",
  PODE: "#29abe2",
  PTN: "#29abe2",
  NOVO: "#f37021",
  PTB: "#6d4c41",
  SOLIDARIEDADE: "#ef6c00",
  SD: "#ef6c00",
  AVANTE: "#8e44ad",
  "PT do B": "#8e44ad",
  PATRIOTA: "#1e8449",
  PATRI: "#1e8449",
  PEN: "#1e8449",
  PRD: "#2c3e50",
  PSC: "#148f77",
  PROS: "#d35400",
  PRTB: "#0e6655",
  DC: "#2874a6",
  PSDC: "#2874a6",
  AGIR: "#b7950b",
  PTC: "#b7950b",
  PMN: "#cd6155",
  PMB: "#d81b60",
  PRP: "#7d3c98",
  PHS: "#45b39d",
  PPL: "#a04000",
  MOBILIZA: "#c9a00a",
};

// Cores neutras, fora de qualquer partido (a reserva nunca cai nelas: tem croma).
export const NEUTRO = {
  semDados: { claro: "#dfe2e6", escuro: "#34373d" },
  empate: { claro: "#9aa0a8", escuro: "#6b7079" },
} as const;

export const SUPERFICIE = { claro: "#ffffff", escuro: "#1a1a19" } as const;
export type Tema = keyof typeof SUPERFICIE;

// --- conversões (sRGB <-> OKLab/OKLCH) --------------------------------------------------

type Rgb = [number, number, number]; // 0–1, sRGB
type Lab = [number, number, number];

function hexParaRgb(hex: string): Rgb {
  const h = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255) as Rgb;
}

function rgbParaHex(rgb: Rgb): string {
  return (
    "#" +
    rgb
      .map((v) => Math.round(Math.min(1, Math.max(0, v)) * 255).toString(16).padStart(2, "0"))
      .join("")
  );
}

const linear = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const gama = (c: number) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);

export function paraOklab(hex: string): Lab {
  const [r, g, b] = hexParaRgb(hex).map(linear);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

export function deOklab([L, a, b]: Lab): string {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return rgbParaHex(
    [
      4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
      -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
      -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
    ].map(gama) as Rgb,
  );
}

/** Distância perceptual em OKLab (0 = idênticas; ~0,1 já distingue no mapa). */
export function deltaE(a: string, b: string): number {
  const [x, y] = [paraOklab(a), paraOklab(b)];
  return Math.hypot(x[0] - y[0], x[1] - y[1], x[2] - y[2]);
}

function luminancia(hex: string): number {
  const [r, g, b] = hexParaRgb(hex).map(linear);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Razão de contraste WCAG 2.x entre duas cores. */
export function contraste(a: string, b: string): number {
  const [l1, l2] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

const TEXTO_CLARO = "#ffffff";
// preto puro: com qualquer fundo, o melhor entre branco e preto passa de 4,58:1
const TEXTO_ESCURO = "#000000";

/** Texto claro ou escuro, o que tiver mais contraste com o fundo. */
export function textoSobre(fundo: string): string {
  return contraste(fundo, TEXTO_CLARO) >= contraste(fundo, TEXTO_ESCURO) ? TEXTO_CLARO : TEXTO_ESCURO;
}

// --- cor de cada partido --------------------------------------------------------------

function hash(s: string): number {
  let h = 2166136261;
  for (const ch of s) h = Math.imul(h ^ ch.codePointAt(0)!, 16777619);
  return h >>> 0;
}

/** Cor de reserva estável: matiz derivado da sigla, luminosidade e croma fixos. */
export function corReserva(sigla: string): string {
  const matiz = ((hash(sigla) % 360) * Math.PI) / 180;
  return deOklab([0.62, 0.13 * Math.cos(matiz), 0.13 * Math.sin(matiz)]);
}

export function corBase(sigla: string | null | undefined): string {
  if (!sigla) return NEUTRO.empate.claro;
  return PALETA[sigla] ?? PALETA[sigla.toUpperCase()] ?? corReserva(sigla);
}

export const DELTA_MINIMO = 0.1;
const PASSO_L = 0.07;

/**
 * Cores de uma disputa: `siglas` em ordem de votos (a primeira é a mais votada e
 * nunca muda). Um partido perto demais de um anterior é clareado ou escurecido.
 */
export function coresDaDisputa(siglas: readonly (string | null | undefined)[]): Map<string, Cor> {
  const out = new Map<string, Cor>();
  const usadas: string[] = [];
  for (const s of siglas) {
    const chave = s ?? "";
    if (out.has(chave)) continue;
    let hex = corBase(s);
    const [L, a, b] = paraOklab(hex);
    // alterna: mais escuro, mais claro, mais escuro (2 passos)...
    for (let i = 1; usadas.some((u) => deltaE(u, hex) < DELTA_MINIMO) && i <= 8; i++) {
      const sinal = i % 2 === 1 ? -1 : 1;
      const novoL = Math.min(0.9, Math.max(0.28, L + sinal * Math.ceil(i / 2) * PASSO_L * 1.4));
      hex = deOklab([novoL, a, b]);
    }
    usadas.push(hex);
    out.set(chave, { fundo: hex, texto: textoSobre(hex) });
  }
  return out;
}

// --- faixas do mapa -------------------------------------------------------------------

/** Faixas do percentual do vencedor (limite inferior de cada faixa, em %). */
export const FAIXAS_VENCEDOR = [0, 50, 60, 70] as const;
const PESOS_VENCEDOR = [0.38, 0.58, 0.8, 1] as const;

export function faixa(pct: number, limites: readonly number[]): number {
  let i = 0;
  while (i + 1 < limites.length && pct >= limites[i + 1]) i++;
  return i;
}

/** Mistura em OKLab: `peso` 1 = cor pura, 0 = superfície. */
export function misturar(cor: string, superficie: string, peso: number): string {
  const [x, y] = [paraOklab(cor), paraOklab(superficie)];
  return deOklab([0, 1, 2].map((i) => y[i] + (x[i] - y[i]) * peso) as Lab);
}

/** Cor do município na camada "Mais votado". */
export function corIntensidade(base: string, pct: number, tema: Tema = "claro"): string {
  return misturar(base, SUPERFICIE[tema], PESOS_VENCEDOR[faixa(pct, FAIXAS_VENCEDOR)]);
}

/** Faixas fixas da abstenção (%), para comparar entre anos. */
export const FAIXAS_ABSTENCAO = [0, 15, 20, 25, 30] as const;
const ESCALA_ABSTENCAO = {
  claro: ["#e7e9f7", "#bfc5ec", "#8d97d8", "#5361bd", "#27348b"],
  escuro: ["#2a2f52", "#3d4785", "#5865b8", "#8a95dd", "#c3c9f2"],
} as const;

export function corAbstencao(pct: number, tema: Tema = "claro"): string {
  return ESCALA_ABSTENCAO[tema][faixa(pct, FAIXAS_ABSTENCAO)];
}

export function rotuloFaixas(limites: readonly number[]): string[] {
  return limites.map((l, i) =>
    i === 0 ? `< ${limites[1]}%` : i === limites.length - 1 ? `≥ ${l}%` : `${l}–${limites[i + 1]}%`,
  );
}
