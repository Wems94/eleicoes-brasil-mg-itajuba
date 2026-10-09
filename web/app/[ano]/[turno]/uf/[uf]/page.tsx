import type { Metadata } from "next";
import Link from "next/link";

import { BarrasTabela } from "@/components/BarrasTabela";
import { TabelaDeputados } from "@/components/TabelaDeputados";
import { Participacao, SeletorEleicao, Secao } from "@/components/base";
import { dados } from "@/lib/dados";
import { NOME_UF, nomeTurno, numero, pct } from "@/lib/formato";

type Params = Promise<{ ano: string; turno: string; uf: string }>;

const MAJORITARIOS = new Set([1, 3, 5]);

export const dynamicParams = false;

export function generateStaticParams() {
  return dados.eleicoes().flatMap(({ ano, turno }) =>
    dados.ufs(ano, turno).map((uf) => ({ ano: String(ano), turno: String(turno), uf })),
  );
}

async function ler(params: Params) {
  const p = await params;
  return { ano: Number(p.ano), turno: Number(p.turno), uf: p.uf };
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { ano, turno, uf } = await ler(params);
  return { title: `${NOME_UF[uf] ?? uf} ${ano}, ${nomeTurno(turno)}` };
}

export default async function PaginaUf({ params }: { params: Params }) {
  const { ano, turno, uf } = await ler(params);
  const d = dados.uf(ano, turno, uf);
  // O comparecimento de referência é o do cargo de maior abrangência disputado na UF.
  const principal = d.comparecimento[0];

  return (
    <div className="space-y-12">
      <header className="space-y-5">
        <p className="text-sm">
          <Link href={`/${ano}/${turno}/`} className="text-tinta-2 hover:text-ocre">
            ← Brasil {ano}
          </Link>
        </p>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ocre">
          {uf} · {nomeTurno(turno)}
        </p>
        <h1 className="font-display text-4xl font-semibold tracking-tight sm:text-6xl">
          {NOME_UF[uf] ?? uf} <span className="font-normal italic text-tinta-2">{ano}</span>
        </h1>
        <SeletorEleicao
          eleicoes={dados.eleicoes()}
          atual={{ ano, turno }}
          href={(e) =>
            dados.ufs(e.ano, e.turno).includes(uf) ? `/${e.ano}/${e.turno}/uf/${uf}/` : `/${e.ano}/${e.turno}/`
          }
        />
      </header>

      {principal ? (
        <Secao id="participacao" titulo="Participação" sobretitulo={principal.nome}>
          <Participacao dados={principal} />
          <p className="num mt-2 text-xs text-tinta-2">{numero(principal.aptos)} eleitores aptos</p>
        </Secao>
      ) : null}

      <div className="grid gap-12 md:grid-cols-2">
        {d.cargos
          .filter((c) => MAJORITARIOS.has(c.codigo))
          .map((c) => (
            <Secao key={c.codigo} id={`cargo-${c.codigo}`} titulo={c.nome} sobretitulo="Majoritário">
              <BarrasTabela
                legenda={`${c.nome}, ${NOME_UF[uf] ?? uf}: percentual dos votos válidos`}
                ocultarLegenda
                linhas={c.candidatos.map((k) => ({
                  chave: String(k.numero),
                  rotulo: `${k.numero} · ${k.nome}`,
                  detalhe: [k.partido, k.situacao].filter(Boolean).join(" · "),
                  votos: k.votos,
                  pct: k.pct,
                  destaque: k.situacao === "ELEITO",
                }))}
              />
              <p className="num mt-3 text-xs text-tinta-2">{numero(c.votos_validos)} votos válidos</p>
            </Secao>
          ))}
      </div>

      {d.cargos
        .filter((c) => !MAJORITARIOS.has(c.codigo))
        .map((c) => (
          <Secao key={c.codigo} id={`cargo-${c.codigo}`} titulo={c.nome} sobretitulo="Proporcional">
            <TabelaDeputados legenda={c.nome} candidatos={c.candidatos} />
            <p className="mt-3 text-xs text-tinta-2">
              Percentual sobre os {numero(c.votos_validos)} votos válidos (nominais e de legenda).
            </p>
          </Secao>
        ))}

      {d.comparecimento.length > 1 ? (
        <Secao id="comparecimento" titulo="Comparecimento por cargo" sobretitulo="Detalhe">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] text-sm">
              <thead>
                <tr className="border-b border-tinta text-left text-xs text-tinta-2">
                  <th scope="col" className="py-1 font-medium">Cargo</th>
                  <th scope="col" className="py-1 text-right font-medium">Comparecimento</th>
                  <th scope="col" className="py-1 text-right font-medium">Abstenção</th>
                  <th scope="col" className="py-1 text-right font-medium">Brancos</th>
                  <th scope="col" className="py-1 text-right font-medium">Nulos</th>
                </tr>
              </thead>
              <tbody>
                {d.comparecimento.map((c) => (
                  <tr key={c.codigo} className="border-b border-regua">
                    <th scope="row" className="py-1 text-left font-normal">{c.nome}</th>
                    <td className="num py-1 text-right">{pct(c.pct_comparecimento)}</td>
                    <td className="num py-1 text-right">{pct(c.pct_abstencao)}</td>
                    <td className="num py-1 text-right">{pct(c.pct_brancos)}</td>
                    <td className="num py-1 text-right">{pct(c.pct_nulos)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Secao>
      ) : null}
    </div>
  );
}
