import type { Itajuba, ItajubaSecoes, Votavel } from "./tipos";

/** Cargos majoritários mostrados nos mapas de Itajubá. */
export const CARGOS_ITAJUBA = [1, 3, 5] as const;

export type Participacao = { aptos: number; comparecimento: number; abstencoes: number; brancos: number; nulos: number };
export type Metrica = "abstencao" | "brancos" | "nulos";

export type VotoCandidato = { numero: number; nome: string; partido: string | null; votos: number };
export type Colocado = VotoCandidato & { pct: number };

export type SecaoItajuba = { secao: number; participacao: Record<string, Participacao> };

/** Um ponto do mapa: um local de votação ou um bairro (soma dos seus locais). */
export type PontoItajuba = {
  id: string;
  nome: string;
  bairro: string;
  detalhe: string | null; // endereço do local ou lista de locais do bairro
  lat: number;
  lon: number;
  aptos: number;
  participacao: Record<string, Participacao>; // por código de cargo
  votos: Record<string, VotoCandidato[]>; // por código de cargo: candidatos, do mais votado ao menos
  secoes: SecaoItajuba[];
};

const VAZIA: Participacao = { aptos: 0, comparecimento: 0, abstencoes: 0, brancos: 0, nulos: 0 };

function somar(a: Participacao, b: Participacao): Participacao {
  return {
    aptos: a.aptos + b.aptos,
    comparecimento: a.comparecimento + b.comparecimento,
    abstencoes: a.abstencoes + b.abstencoes,
    brancos: a.brancos + b.brancos,
    nulos: a.nulos + b.nulos,
  };
}

function somarPorCargo(itens: Record<string, Participacao>[]): Record<string, Participacao> {
  const total: Record<string, Participacao> = {};
  for (const item of itens)
    for (const [cargo, p] of Object.entries(item)) total[cargo] = somar(total[cargo] ?? VAZIA, p);
  return total;
}

function candidatos(votaveis: Votavel[] | undefined): VotoCandidato[] {
  return (votaveis ?? [])
    .filter((v) => v.tipo === "candidato")
    .map((v) => ({ numero: v.numero, nome: v.nome ?? `Nº ${v.numero}`, partido: v.partido, votos: v.votos }))
    .sort((a, b) => b.votos - a.votos || a.numero - b.numero);
}

function somarVotos(listas: VotoCandidato[][]): VotoCandidato[] {
  const total = new Map<number, VotoCandidato>();
  for (const v of listas.flat()) {
    const t = total.get(v.numero);
    total.set(v.numero, t ? { ...t, votos: t.votos + v.votos } : { ...v });
  }
  return [...total.values()].sort((a, b) => b.votos - a.votos || a.numero - b.numero);
}

/** Os `n` mais votados do ponto, com o percentual sobre os votos nos candidatos. */
export function colocados(p: PontoItajuba, cargo: number, n = 3): Colocado[] {
  const lista = p.votos[String(cargo)] ?? [];
  const total = lista.reduce((s, v) => s + v.votos, 0);
  return lista.slice(0, n).map((v) => ({ ...v, pct: total ? (100 * v.votos) / total : 0 }));
}

/** Locais de votação com coordenadas, com a participação somada das suas seções. */
export function pontosPorLocal(it: Itajuba, secoes: ItajubaSecoes): PontoItajuba[] {
  const porLocal = new Map<string, SecaoItajuba[]>();
  for (const s of secoes.secoes) {
    if (s.local == null) continue;
    const chave = `${s.zona}-${s.local}`;
    const participacao: Record<string, Participacao> = {};
    for (const cargo of CARGOS_ITAJUBA) {
      const c = s.comparecimento[String(cargo)];
      if (c) participacao[cargo] = { aptos: c.aptos, comparecimento: c.comparecimento, abstencoes: c.abstencoes, brancos: c.brancos, nulos: c.nulos };
    }
    porLocal.set(chave, [...(porLocal.get(chave) ?? []), { secao: s.secao, participacao }]);
  }
  return it.locais
    .filter((l) => l.lat != null && l.lon != null)
    .map((l) => {
      const chave = `${l.zona}-${l.local}`;
      const secoesLocal = (porLocal.get(chave) ?? []).sort((a, b) => a.secao - b.secao);
      const participacao = somarPorCargo(secoesLocal.map((s) => s.participacao));
      return {
        id: `local-${chave}`,
        nome: l.nome ?? `Local ${l.local}`,
        bairro: l.bairro ?? "Sem bairro",
        detalhe: l.endereco,
        lat: l.lat!,
        lon: l.lon!,
        aptos: participacao[CARGOS_ITAJUBA[0]]?.aptos ?? Math.max(0, ...Object.values(participacao).map((p) => p.aptos)),
        participacao,
        votos: Object.fromEntries(
          CARGOS_ITAJUBA.map((cargo) => [cargo, candidatos(l.cargos.find((c) => c.codigo === cargo)?.votaveis)]),
        ),
        secoes: secoesLocal,
      };
    })
    .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
}

/** Agrupa os locais por bairro: o ponto fica no centro dos locais do bairro. */
export function pontosPorBairro(locais: PontoItajuba[]): PontoItajuba[] {
  const grupos = new Map<string, PontoItajuba[]>();
  for (const l of locais) grupos.set(l.bairro, [...(grupos.get(l.bairro) ?? []), l]);
  return [...grupos.entries()]
    .map(([bairro, ls]) => ({
      id: `bairro-${bairro}`,
      nome: bairro,
      bairro,
      detalhe: ls.map((l) => l.nome).join(" · "),
      lat: ls.reduce((s, l) => s + l.lat, 0) / ls.length,
      lon: ls.reduce((s, l) => s + l.lon, 0) / ls.length,
      aptos: ls.reduce((s, l) => s + l.aptos, 0),
      participacao: somarPorCargo(ls.map((l) => l.participacao)),
      votos: Object.fromEntries(CARGOS_ITAJUBA.map((c) => [c, somarVotos(ls.map((l) => l.votos[String(c)] ?? []))])),
      secoes: ls.flatMap((l) => l.secoes).sort((a, b) => a.secao - b.secao),
    }))
    .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
}

/**
 * Taxa em %: abstenção sobre os aptos; brancos e nulos sobre quem compareceu
 * (mesma base do TSE). Nula quando não há eleitores.
 */
export function taxa(p: Participacao | undefined, metrica: Metrica): number | null {
  if (!p) return null;
  if (metrica === "abstencao") return p.aptos ? (100 * p.abstencoes) / p.aptos : null;
  if (!p.comparecimento) return null;
  return (100 * (metrica === "brancos" ? p.brancos : p.nulos)) / p.comparecimento;
}

/** Faixas fixas (limite inferior, em %) de cada métrica, para comparar entre anos. */
export const FAIXAS_METRICA: Record<Metrica, readonly number[]> = {
  abstencao: [0, 15, 20, 25, 30],
  brancos: [0, 2, 4, 6, 8],
  nulos: [0, 2, 4, 6, 8],
};

export const NOME_METRICA: Record<Metrica, string> = { abstencao: "Abstenção", brancos: "Brancos", nulos: "Nulos" };
export const BASE_METRICA: Record<Metrica, string> = {
  abstencao: "sobre os aptos",
  brancos: "sobre quem compareceu",
  nulos: "sobre quem compareceu",
};

/** Raio do círculo (px) proporcional à raiz do eleitorado: a área acompanha os aptos. */
export function raio(aptos: number, maximo: number, min = 4, max = 13): number {
  if (maximo <= 0) return min;
  return min + (max - min) * Math.sqrt(Math.max(0, aptos) / maximo);
}
