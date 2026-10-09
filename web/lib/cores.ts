// Cores dos candidatos. A cor segue a entidade (o candidato ou partido), atribuída
// na ordem do resultado da eleição exibida; do 4º em diante, todos são "outros".
// A paleta (globals.css) foi validada para daltonismo em todos os pares.

const SERIES = 3;

export type Cor = { fundo: string; texto: string };

export function corDaPosicao(i: number): Cor {
  const s = i >= 0 && i < SERIES ? String(i + 1) : "outros";
  return { fundo: `var(--color-serie-${s})`, texto: `var(--color-sobre-serie-${s})` };
}

/** Mapa estável entidade -> cor, na ordem em que as chaves são dadas. */
export function coresPorEntidade(chaves: readonly (string | number)[]): Map<string, Cor> {
  const m = new Map<string, Cor>();
  for (const k of chaves) {
    if (!m.has(String(k))) m.set(String(k), corDaPosicao(m.size));
  }
  return m;
}
