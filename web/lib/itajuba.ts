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

export type VariacaoPartido = { partido: string; antes: number; depois: number; delta: number };

/**
 * Variação, em pontos percentuais, entre os dois 1º turnos mais recentes de um cargo,
 * para os partidos presentes nos dois. Ordenada pelo percentual mais recente.
 */
export function variacaoPrimeiroTurno(
  eleicoes: EleicaoHistorica[],
): { de: number; para: number; partidos: VariacaoPartido[] } | null {
  const primeiros = eleicoes.filter((e) => e.turno === 1);
  if (primeiros.length < 2) return null;
  const [a, b] = primeiros.slice(-2);
  const antes = new Map(a.partidos.map((p) => [p.partido, p.pct]));
  const partidos = b.partidos
    .filter((p) => p.partido && p.pct != null && antes.get(p.partido) != null)
    .map((p) => {
      const ant = antes.get(p.partido)!;
      return { partido: p.partido!, antes: ant, depois: p.pct!, delta: Math.round((p.pct! - ant) * 100) / 100 };
    })
    .sort((x, y) => y.depois - x.depois);
  return { de: a.ano, para: b.ano, partidos };
}

/** Comparecimento por eleição (o do Presidente, que é o de todos os cargos no turno). */
export function comparecimentoPorEleicao(h: Historico): Historico["comparecimento"] {
  const porEleicao = new Map<string, Historico["comparecimento"][number]>();
  for (const c of [...h.comparecimento].sort((a, b) => a.cargo - b.cargo)) {
    const k = `${c.ano}/${c.turno}`;
    if (!porEleicao.has(k)) porEleicao.set(k, c);
  }
  return [...porEleicao.values()].sort((a, b) => a.ano - b.ano || a.turno - b.turno);
}

const pct2 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Frase-resumo da comparação histórica, a partir dos próprios dados. */
export function resumoHistorico(h: Historico): string {
  const partes: string[] = [];
  const presidente = historicoPorCargo(h, 1);
  const ultimo = presidente[presidente.length - 1];
  const lider = ultimo?.partidos[0];
  if (ultimo && lider?.partido && lider.pct != null) {
    partes.push(
      `${lider.partido} liderou para Presidente em ${ultimo.ano} (${ultimo.turno}º turno) com ${pct2.format(lider.pct)}%.`,
    );
  }
  const gov = historicoPorCargo(h, 3).filter((e) => e.turno === 1);
  const lideresGov = new Set(gov.map((e) => e.partidos[0]?.partido));
  if (gov.length > 1 && lideresGov.size === 1) {
    partes.push(`${[...lideresGov][0]} liderou para Governador em todas as eleições.`);
  }
  const comp = comparecimentoPorEleicao(h)
    .map((c) => c.pct_comparecimento)
    .filter((v): v is number => v != null);
  if (comp.length > 1) {
    partes.push(
      `O comparecimento variou entre ${pct2.format(Math.min(...comp))}% e ${pct2.format(Math.max(...comp))}%.`,
    );
  }
  return partes.join(" ");
}
