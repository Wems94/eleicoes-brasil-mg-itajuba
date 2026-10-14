"use client";

import Link from "next/link";

import { BarrasTabela } from "@/components/BarrasTabela";
import { NOME_UF, numero, pct } from "@/lib/formato";
import { coresDaDisputa } from "@/lib/partidos";
import type { BlocoDetalhe, DetalheUf, Eleicao } from "@/lib/tipos";

type Props = Eleicao & {
  codigo: string;
  uf: string;
  nomeMunicipio: string;
  nomeCargo: string;
  detalhe: DetalheUf | null; // null enquanto carrega
  erro: boolean;
  fotos: Record<string, string>; // número de urna -> caminho (só Presidente)
  itajuba: number | null;
  onFechar: () => void;
};

/** Painel do município: total e cada zona eleitoral (capability mapa-municipal). */
export function PainelMunicipio(p: Props) {
  const m = p.detalhe?.municipios[p.codigo];
  return (
    <aside
      aria-labelledby="painel-municipio-t"
      className="fixed inset-x-0 bottom-0 z-30 max-h-[72vh] overflow-y-auto rounded-t-2xl border border-borda bg-superficie p-5 shadow-[0_-8px_30px_rgb(0_0_0/0.18)] lg:static lg:z-auto lg:max-h-[44rem] lg:rounded-2xl lg:shadow-none"
    >
      <header className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-texto-3">
            {NOME_UF[p.uf] ?? p.uf} · {p.nomeCargo}
          </p>
          <h3 id="painel-municipio-t" className="text-lg font-semibold tracking-tight">
            {m?.nome ?? p.nomeMunicipio}
          </h3>
        </div>
        <button
          type="button"
          onClick={p.onFechar}
          className="rounded-lg border border-borda px-2.5 py-1 text-sm text-texto-2 hover:bg-realce hover:text-texto"
          aria-label="Fechar o painel do município"
        >
          ✕
        </button>
      </header>

      {p.erro ? (
        <p className="text-sm text-texto-2">Não foi possível carregar os dados deste município.</p>
      ) : !p.detalhe ? (
        <p className="text-sm text-texto-2" aria-live="polite">
          Carregando…
        </p>
      ) : !m ? (
        <p className="text-sm text-texto-2">Sem votação para este cargo neste município.</p>
      ) : (
        <div className="space-y-5">
          {p.itajuba != null && String(p.itajuba) === p.codigo ? (
            <Link
              href={`/itajuba/${p.ano}/${p.turno}/`}
              className="block rounded-lg border border-borda px-3 py-2 text-sm font-medium hover:bg-realce"
            >
              Deep dive de Itajubá: locais e seções →
            </Link>
          ) : null}
          <Bloco titulo="Total do município" bloco={m.total} {...p} />
          {m.zonas.length ? (
            <div>
              <h4 className="mb-2 text-sm font-semibold">
                {m.zonas.length === 1 ? "Zona eleitoral" : `${m.zonas.length} zonas eleitorais`}
              </h4>
              <div className="space-y-2">
                {m.zonas.map((z) => (
                  <details key={z.zona} className="rounded-xl border border-borda" open={m.zonas.length === 1}>
                    <summary className="flex cursor-pointer items-center justify-between gap-3 px-3 py-2 text-sm">
                      <span className="font-medium">Zona {z.zona}</span>
                      <span className="num text-xs text-texto-3">
                        abstenção {pct(z.comparecimento?.pct_abstencao)}
                      </span>
                    </summary>
                    <div className="px-3 pb-3">
                      {z.outros_municipios > 0 ? (
                        <p className="mb-2 text-xs text-texto-2">
                          A zona {z.zona} também atende{" "}
                          {z.outros_municipios === 1 ? "outro município" : `outros ${z.outros_municipios} municípios`}
                          ; os números abaixo são só de {m.nome ?? p.nomeMunicipio}.
                        </p>
                      ) : null}
                      <Bloco bloco={z} {...p} />
                    </div>
                  </details>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </aside>
  );
}

function Bloco({ titulo, bloco, detalhe, fotos }: Props & { titulo?: string; bloco: BlocoDetalhe }) {
  const d = detalhe!;
  const porPartido = d.por === "partido";
  const linhas = bloco.votos.map(([chave, votos, p]) => ({ v: d.votaveis[chave], chave, votos, p }));
  const cores = coresDaDisputa(linhas.map((l) => l.v?.partido));
  const comFoto = d.cargo === "presidente";
  const c = bloco.comparecimento;
  return (
    <div>
      {titulo ? <h4 className="mb-2 text-sm font-semibold">{titulo}</h4> : null}
      <BarrasTabela
        legenda={porPartido ? "Votos por partido (nominais e de legenda)" : "Votos por candidato"}
        rotuloColuna={porPartido ? "Partido" : "Candidato"}
        ocultarLegenda={!porPartido}
        linhas={linhas.map((l, i) => ({
          chave: l.chave,
          rotulo: porPartido ? (l.v?.partido ?? l.chave) : (l.v?.nome ?? l.chave),
          detalhe: porPartido ? null : [l.v?.numero != null ? `Nº ${l.v.numero}` : null, l.v?.partido].filter(Boolean).join(" · "),
          votos: l.votos,
          pct: l.p,
          destaque: i === 0,
          partido: l.v?.partido,
          foto: comFoto ? (fotos[l.chave] ?? null) : undefined,
          cor: cores.get(l.v?.partido ?? ""),
        }))}
      />
      {porPartido && bloco.candidatos?.length ? (
        <table className="mt-3 w-full text-sm">
          <caption className="mb-1 text-left text-xs font-semibold">Candidatos mais votados</caption>
          <thead className="sr-only">
            <tr>
              <th scope="col">Candidato</th>
              <th scope="col">Votos</th>
              <th scope="col">Percentual dos válidos</th>
            </tr>
          </thead>
          <tbody>
            {bloco.candidatos.map(([chave, votos, p]) => {
              const v = d.votaveis[chave];
              return (
                <tr key={chave} className="border-b border-borda last:border-0">
                  <th scope="row" className="py-1 text-left font-normal">
                    {v?.nome ?? chave} <span className="text-xs text-texto-3">{v?.partido}</span>
                  </th>
                  <td className="num py-1 text-right text-xs text-texto-3">{numero(votos)}</td>
                  <td className="num w-16 py-1 text-right">{pct(p)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : null}
      {c ? (
        <dl className="num mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-3">
          <Item rotulo="Aptos" valor={numero(c.aptos)} />
          <Item rotulo="Comparecimento" valor={`${numero(c.comparecimento)} (${pct(c.pct_comparecimento)})`} />
          <Item rotulo="Abstenção" valor={`${numero(c.abstencoes)} (${pct(c.pct_abstencao)})`} />
          <Item rotulo="Brancos" valor={`${numero(c.brancos)} (${pct(c.pct_brancos)})`} />
          <Item rotulo="Nulos" valor={`${numero(c.nulos)} (${pct(c.pct_nulos)})`} />
        </dl>
      ) : null}
    </div>
  );
}

function Item({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div>
      <dt className="text-texto-3">{rotulo}</dt>
      <dd className="font-medium">{valor}</dd>
    </div>
  );
}
