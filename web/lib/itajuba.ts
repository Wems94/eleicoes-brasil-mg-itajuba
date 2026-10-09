import type { Comparecimento, Historico, ItajubaSecoes } from "./tipos";

const NOMES_ESPECIAIS: Record<number, string> = { 95: "Brancos", 96: "Nulos", 97: "Anulados" };

export const NOME_CARGO: Record<number, string> = {
  1: "Presidente",
  3: "Governador",
  5: "Senador",
  6: "Deputado Federal",
  7: "Deputado Estadual",
  8: "Deputado Distrital",
};

export function secoesDisponiveis(d: ItajubaSecoes): { zona: number; secao: number }[] {
  return d.secoes
    .map(({ zona, secao }) => ({ zona, secao }))
    .sort((a, b) => a.zona - b.zona || a.secao - b.secao);
}

export type ResultadoSecao = {
  zona: number;
  secao: number;
  local: number | null;
  cargos: {
    codigo: number;
    nome: string;
    comparecimento: Comparecimento | null;
    votos: { numero: number; nome: string; votos: number }[];
  }[];
};

export function buscarSecao(d: ItajubaSecoes, zona: number, secao: number): ResultadoSecao | null {
  const s = d.secoes.find((x) => x.zona === zona && x.secao === secao);
  if (!s) return null;
  const codigos = [...new Set([...Object.keys(s.comparecimento), ...Object.keys(s.votos)])]
    .map(Number)
    .sort((a, b) => a - b);
  return {
    zona,
    secao,
    local: s.local,
    cargos: codigos.map((codigo) => {
      const nomes = d.votaveis[String(codigo)] ?? {};
      return {
        codigo,
        nome: NOME_CARGO[codigo] ?? `Cargo ${codigo}`,
        comparecimento: s.comparecimento[String(codigo)] ?? null,
        votos: (s.votos[String(codigo)] ?? [])
          .map(([numero, votos]) => ({
            numero,
            nome: NOMES_ESPECIAIS[numero] ?? nomes[String(numero)] ?? `Nº ${numero}`,
            votos,
          }))
          .sort((a, b) => b.votos - a.votos || a.numero - b.numero),
      };
    }),
  };
}

export type EleicaoHistorica = {
  ano: number;
  turno: number;
  partidos: Historico["partidos"];
  comparecimento: Historico["comparecimento"][number] | null;
};

/** Votação por partido e comparecimento de um cargo majoritário em cada eleição. */
export function historicoPorCargo(h: Historico, cargo: number): EleicaoHistorica[] {
  const chave = (ano: number, turno: number) => `${ano}/${turno}`;
  const grupos = new Map<string, EleicaoHistorica>();
  for (const p of h.partidos.filter((x) => x.cargo === cargo)) {
    const k = chave(p.ano, p.turno);
    if (!grupos.has(k)) grupos.set(k, { ano: p.ano, turno: p.turno, partidos: [], comparecimento: null });
    grupos.get(k)!.partidos.push(p);
  }
  for (const c of h.comparecimento.filter((x) => x.cargo === cargo)) {
    const g = grupos.get(chave(c.ano, c.turno));
    if (g) g.comparecimento = c;
  }
  return [...grupos.values()].sort((a, b) => a.ano - b.ano || a.turno - b.turno);
}
