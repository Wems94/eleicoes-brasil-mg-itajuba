import Link from "next/link";
import type { ReactNode } from "react";

import { nomeTurno, numero, pct } from "@/lib/formato";
import type { Comparecimento, Eleicao } from "@/lib/tipos";

/** Card do painel. */
export function Secao({
  titulo,
  sobretitulo,
  children,
  id,
  acao,
  className = "",
}: {
  titulo: string;
  sobretitulo?: string;
  children: ReactNode;
  id?: string;
  acao?: ReactNode;
  className?: string;
}) {
  return (
    <section
      id={id}
      aria-labelledby={id && `${id}-t`}
      className={`scroll-mt-20 rounded-2xl border border-borda bg-superficie p-5 shadow-[0_1px_2px_rgb(0_0_0/0.04)] sm:p-6 ${className}`}
    >
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          {sobretitulo ? (
            <p className="text-xs font-medium uppercase tracking-wider text-texto-3">{sobretitulo}</p>
          ) : null}
          <h2 id={id && `${id}-t`} className="text-lg font-semibold tracking-tight">
            {titulo}
          </h2>
        </div>
        {acao}
      </header>
      {children}
    </section>
  );
}

/** Seletor de ano/turno em pílulas: só oferece as eleições do manifesto. */
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
    <nav
      aria-label="Escolher eleição"
      className="inline-flex flex-wrap gap-1 rounded-xl border border-borda bg-superficie p-1"
    >
      {eleicoes.map((e) => {
        const ativo = e.ano === atual.ano && e.turno === atual.turno;
        return (
          <Link
            key={`${e.ano}-${e.turno}`}
            href={href(e)}
            aria-current={ativo ? "page" : undefined}
            className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
              ativo ? "bg-texto text-superficie" : "text-texto-2 hover:bg-realce hover:text-texto"
            }`}
          >
            <span className="num font-semibold">{e.ano}</span>{" "}
            <span className="text-xs opacity-80">{nomeTurno(e.turno)}</span>
          </Link>
        );
      })}
    </nav>
  );
}

/** Indicadores grandes de participação (percentual + número absoluto). */
export function Participacao({ dados }: { dados: Comparecimento }) {
  const itens: [string, number, number | null | undefined, string][] = [
    ["Comparecimento", dados.comparecimento, dados.pct_comparecimento, "eleitores"],
    ["Abstenção", dados.abstencoes, dados.pct_abstencao, "eleitores"],
    ["Brancos", dados.brancos, dados.pct_brancos, "votos"],
    ["Nulos", dados.nulos, dados.pct_nulos, "votos"],
  ];
  return (
    <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {itens.map(([rotulo, n, p, unidade]) => (
        <div key={rotulo} className="rounded-2xl border border-borda bg-superficie p-4 sm:p-5">
          <dt className="text-sm text-texto-2">{rotulo}</dt>
          <dd className="num mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
            {p == null ? numero(n) : pct(p)}
          </dd>
          {p == null ? null : <dd className="num mt-0.5 text-xs text-texto-3">{numero(n)} {unidade}</dd>}
        </div>
      ))}
    </dl>
  );
}

/** Cabeçalho de página: sobretítulo, título, subtítulo e seletor. */
export function CabecalhoPagina({
  sobretitulo,
  titulo,
  subtitulo,
  children,
}: {
  sobretitulo: string;
  titulo: ReactNode;
  subtitulo?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <header className="space-y-4">
      <p className="text-sm font-medium text-texto-2">{sobretitulo}</p>
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{titulo}</h1>
      {subtitulo ? <p className="max-w-3xl text-lg text-texto-2">{subtitulo}</p> : null}
      {children}
    </header>
  );
}
