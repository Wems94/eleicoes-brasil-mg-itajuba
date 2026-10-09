import Link from "next/link";
import type { ReactNode } from "react";

import { nomeTurno, numero, pct } from "@/lib/formato";
import type { Comparecimento, Eleicao } from "@/lib/tipos";

export function Secao({
  titulo,
  sobretitulo,
  children,
  id,
}: {
  titulo: string;
  sobretitulo?: string;
  children: ReactNode;
  id?: string;
}) {
  return (
    <section id={id} className="border-t-2 border-tinta pt-4" aria-labelledby={id && `${id}-t`}>
      {sobretitulo ? (
        <p className="mb-1 text-xs font-semibold uppercase tracking-[0.18em] text-ocre">
          {sobretitulo}
        </p>
      ) : null}
      <h2 id={id && `${id}-t`} className="mb-4 font-display text-2xl font-semibold tracking-tight">
        {titulo}
      </h2>
      {children}
    </section>
  );
}

/** Seletor de ano/turno: só oferece as eleições presentes no manifesto. */
export function SeletorEleicao({
  eleicoes,
  atual,
  href,
}: {
  eleicoes: Eleicao[];
  atual: Eleicao;
  href: (e: Eleicao) => string;
}) {
  return (
    <nav aria-label="Escolher eleição" className="flex flex-wrap gap-2">
      {eleicoes.map((e) => {
        const ativo = e.ano === atual.ano && e.turno === atual.turno;
        return (
          <Link
            key={`${e.ano}-${e.turno}`}
            href={href(e)}
            aria-current={ativo ? "page" : undefined}
            className={`border px-3 py-1.5 text-sm transition-colors ${
              ativo
                ? "border-tinta bg-tinta text-papel"
                : "border-regua hover:border-tinta"
            }`}
          >
            <span className="num font-semibold">{e.ano}</span>{" "}
            <span className="text-xs">{nomeTurno(e.turno)}</span>
          </Link>
        );
      })}
    </nav>
  );
}

/** Indicadores de participação, com os números absolutos ao lado dos percentuais. */
export function Participacao({ dados }: { dados: Comparecimento }) {
  const itens: [string, number, number | null | undefined][] = [
    ["Comparecimento", dados.comparecimento, dados.pct_comparecimento],
    ["Abstenção", dados.abstencoes, dados.pct_abstencao],
    ["Brancos", dados.brancos, dados.pct_brancos],
    ["Nulos", dados.nulos, dados.pct_nulos],
  ];
  return (
    <dl className="grid grid-cols-2 gap-px border border-regua bg-regua sm:grid-cols-4">
      {itens.map(([rotulo, n, p]) => (
        <div key={rotulo} className="bg-papel p-3">
          <dt className="text-xs uppercase tracking-wider text-tinta-2">{rotulo}</dt>
          <dd className="num mt-1 text-xl font-semibold">{p == null ? numero(n) : pct(p)}</dd>
          {p == null ? null : <dd className="num text-xs text-tinta-2">{numero(n)}</dd>}
        </div>
      ))}
    </dl>
  );
}
