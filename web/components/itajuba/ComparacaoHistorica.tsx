import { dados } from "@/lib/dados";
import { nomeTurno, numero, pct } from "@/lib/formato";
import {
  type EleicaoHistorica,
  NOME_CARGO,
  comparecimentoPorEleicao,
  historicoPorCargo,
  resumoHistorico,
  variacaoPrimeiroTurno,
} from "@/lib/itajuba";
import { type Cor, coresDaDisputa } from "@/lib/partidos";

const MAJORITARIOS = [1, 3, 5] as const;

const pp = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  signDisplay: "always",
});

/**
 * Comparação histórica de Itajubá: um card por eleição em cada cargo majoritário,
 * a variação entre os dois últimos 1º turnos e o comparecimento numa tabela só.
 * Cada card é uma tabela semântica (a barra é decorativa).
 */
export function ComparacaoHistorica() {
  const h = dados.historico();
  const comparecimento = comparecimentoPorEleicao(h);
  const anos = [...new Set(h.partidos.map((p) => p.ano))].sort();
  return (
    <section
      id="comparacao"
      aria-labelledby="comparacao-t"
      className="scroll-mt-24 rounded-2xl border border-borda bg-white/[0.02] p-5 sm:p-8"
    >
      <header className="mb-2">
        <p className="text-[11px] font-medium uppercase tracking-wider text-acento">Itajubá · {anos.join(" · ")}</p>
        <h2 id="comparacao-t" className="mt-1 text-2xl font-semibold sm:text-3xl">
          Comparação histórica
        </h2>
        <p className="mt-2 max-w-[62ch] text-texto-2">{resumoHistorico(h)}</p>
      </header>

      {MAJORITARIOS.map((cargo) => {
        const eleicoes = historicoPorCargo(h, cargo);
        if (!eleicoes.length) return null;
        // a cor segue o partido em todos os anos (prioridade: total de votos no período)
        const total = new Map<string, number>();
        for (const e of eleicoes)
          for (const p of e.partidos) total.set(p.partido ?? "—", (total.get(p.partido ?? "—") ?? 0) + p.votos);
        const cores = coresDaDisputa([...total].sort((a, b) => b[1] - a[1]).map(([p]) => p));
        const variacao = variacaoPrimeiroTurno(eleicoes);
        return (
          <section key={cargo} aria-labelledby={`hist-${cargo}`} className="mt-10">
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3 border-b border-borda pb-3">
              <h3 id={`hist-${cargo}`} className="text-xl font-semibold">
                {NOME_CARGO[cargo]}
              </h3>
              {variacao?.partidos.length ? (
                <div className="flex flex-wrap items-center gap-2 text-xs text-texto-2">
                  <span>
                    1º turno, {variacao.de} → {variacao.para}:
                  </span>
                  {variacao.partidos.map((v) => (
                    <span
                      key={v.partido}
                      className="num inline-flex items-center gap-1.5 rounded-full border border-borda px-2 py-0.5 text-texto"
                      title={`${pct(v.antes)} → ${pct(v.depois)}`}
                    >
                      <span
                        className="size-2 rounded-full"
                        style={{ background: cores.get(v.partido)?.fundo }}
                        aria-hidden="true"
                      />
                      {v.partido}{" "}
                      <span className={v.delta > 0 ? "text-emerald-300" : v.delta < 0 ? "text-rose-300" : ""}>
                        {pp.format(v.delta)} p.p.
                      </span>
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
            <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,18rem),1fr))]">
              {eleicoes.map((e) => (
                <CardEleicao key={`${e.ano}-${e.turno}`} eleicao={e} cargo={cargo} cores={cores} />
              ))}
            </div>
            {cargo === 5 && h.partidos.some((p) => p.cargo === 5 && p.ano === 2018) ? (
              <p className="mt-3 text-xs text-texto-3">
                Em 2018 e 2026 são eleitas duas vagas ao Senado e cada eleitor vota duas vezes; por isso o total de
                votos é maior que em 2022.
              </p>
            ) : null}
          </section>
        );
      })}

      {comparecimento.length ? (
        <section aria-labelledby="hist-comp" className="mt-10">
          <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3 border-b border-borda pb-3">
            <h3 id="hist-comp" className="text-xl font-semibold">
              Comparecimento
            </h3>
            <span className="text-xs text-texto-3">Igual para todos os cargos em cada turno</span>
          </div>
          <div className="overflow-x-auto rounded-2xl border border-borda bg-white/[0.02] p-4 sm:p-5">
            <table className="num w-full text-sm">
              <caption className="sr-only">Comparecimento e abstenção em Itajubá por eleição</caption>
              <thead>
                <tr className="border-b border-borda text-left text-xs text-texto-3">
                  <th scope="col" className="pb-2 font-medium">Eleição</th>
                  <th scope="col" className="pb-2 text-right font-medium">Eleitores aptos</th>
                  <th scope="col" className="pb-2 text-right font-medium">Comparecimento</th>
                  <th scope="col" className="hidden pb-2 text-right font-medium sm:table-cell">Abstenção</th>
                </tr>
              </thead>
              <tbody>
                {comparecimento.map((c) => (
                  <tr key={`${c.ano}-${c.turno}`} className="border-b border-borda last:border-0">
                    <th scope="row" className="py-2.5 text-left font-normal">
                      {c.ano} · {nomeTurno(c.turno)}
                    </th>
                    <td className="py-2.5 text-right">{numero(c.aptos)}</td>
                    <td className="py-2.5">
                      <div className="flex items-center justify-end gap-3">
                        <div className="h-2.5 w-[clamp(3rem,14vw,9rem)] overflow-hidden rounded-full bg-white/[0.06]" aria-hidden="true">
                          <div className="barra h-full rounded-full bg-acento" style={{ width: `${c.pct_comparecimento ?? 0}%` }} />
                        </div>
                        <span className="w-16 text-right">{pct(c.pct_comparecimento)}</span>
                      </div>
                    </td>
                    <td className="hidden py-2.5 text-right text-texto-2 sm:table-cell">{pct(c.pct_abstencao)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </section>
  );
}

function CardEleicao({ eleicao, cargo, cores }: { eleicao: EleicaoHistorica; cargo: number; cores: Map<string, Cor> }) {
  const validos = eleicao.partidos.reduce((s, p) => s + p.votos, 0);
  return (
    <div className="rounded-2xl border border-borda bg-white/[0.02] p-5 shadow-[inset_0_1px_0_rgb(255_255_255/0.04)]">
      <table className="w-full border-collapse text-sm">
        <caption className="mb-4 text-left">
          <span className="flex items-baseline justify-between gap-2">
            <span className="text-base font-semibold">
              {eleicao.ano} · {nomeTurno(eleicao.turno)}
            </span>
            <span className="num text-xs text-texto-3">{numero(validos)} votos válidos</span>
          </span>
          <span className="sr-only">
            {NOME_CARGO[cargo]} em Itajubá: votos por partido e percentual dos válidos
          </span>
        </caption>
        <thead className="sr-only">
          <tr>
            <th scope="col">Partido</th>
            <th scope="col">Percentual dos válidos</th>
            <th scope="col">Votos</th>
          </tr>
        </thead>
        <tbody>
          {eleicao.partidos.map((p, i) => {
            const cor = cores.get(p.partido ?? "—")?.fundo;
            return (
              <tr key={p.partido ?? i} className="grid grid-cols-[4.5rem_1fr_auto] items-center gap-x-3 gap-y-1 pb-4 last:pb-0">
                <th scope="row" className="flex items-center gap-1.5 text-left font-medium">
                  <span className="size-2 shrink-0 rounded-full" style={{ background: cor }} aria-hidden="true" />
                  {p.partido ?? "—"}
                </th>
                <td aria-hidden="true">
                  <div className="h-2.5 overflow-hidden rounded-full bg-white/[0.06]">
                    <div
                      className="barra h-full rounded-full"
                      style={{ width: `${p.pct ?? 0}%`, background: cor, opacity: i === 0 ? 1 : 0.75, ["--i" as string]: i }}
                    />
                  </div>
                </td>
                <td className={`num min-w-16 text-right ${i === 0 ? "font-semibold" : ""}`}>{pct(p.pct)}</td>
                <td className="num col-start-2 col-end-4 text-xs text-texto-3">
                  {numero(p.votos)} votos
                  {i === 0 ? (
                    <span className="ml-1.5 rounded-full border border-borda px-1.5 py-px text-[10px] text-texto-2">
                      mais votado
                    </span>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
