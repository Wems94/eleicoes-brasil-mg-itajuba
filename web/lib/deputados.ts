// Listas de deputados (cargos proporcionais), usadas nas páginas e nos JSON estáticos
// carregados sob demanda ("ver todos os candidatos"). Lê os snapshots: só no servidor.
import { dados } from "./dados";
import type { Candidato } from "./tipos";

export const PROPORCIONAIS = [6, 7, 8];
export const VISIVEIS = 30;

export type ListasDeputados = Record<string, Candidato[]>;

export const eleito = (s: string | null) => !!s && s.startsWith("ELEITO");

/** Os mais votados e todos os eleitos (nenhum eleito fica fora da página). */
export function visiveis(candidatos: Candidato[]): Candidato[] {
  return candidatos.filter((c, i) => i < VISIVEIS || eleito(c.situacao));
}

export function deputadosDaUf(ano: number, turno: number, uf: string): ListasDeputados {
  return Object.fromEntries(
    dados
      .uf(ano, turno, uf)
      .cargos.filter((c) => PROPORCIONAIS.includes(c.codigo))
      .map((c) => [String(c.codigo), c.candidatos]),
  );
}

/** Deputados votados em Itajubá, com a situação do candidato no estado. */
export function deputadosDeItajuba(ano: number, turno: number): ListasDeputados {
  const it = dados.itajuba(ano, turno);
  const uf = dados.manifesto().municipio?.uf ?? "MG";
  const situacao = new Map<string, string | null>(
    dados.ufs(ano, turno).includes(uf)
      ? dados
          .uf(ano, turno, uf)
          .cargos.flatMap((c) => c.candidatos.map((k) => [`${c.codigo}-${k.numero}`, k.situacao]))
      : [],
  );
  return Object.fromEntries(
    it.cargos
      .filter((c) => PROPORCIONAIS.includes(c.codigo))
      .map((c) => [
        String(c.codigo),
        c.votaveis
          .filter((v) => v.tipo === "candidato")
          .map((v) => ({
            numero: v.numero,
            nome: v.nome ?? `Nº ${v.numero}`,
            partido: v.partido,
            federacao: null,
            votos: v.votos,
            pct: v.pct,
            situacao: situacao.get(`${c.codigo}-${v.numero}`) ?? null,
            posicao: v.posicao ?? 0,
          })),
      ]),
  );
}
