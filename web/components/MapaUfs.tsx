import Link from "next/link";

import { coresPorEntidade, corDaPosicao } from "@/lib/cores";
import { NOME_UF, pct } from "@/lib/formato";
import type { Brasil } from "@/lib/tipos";

// Tile map: cada UF é um quadrado na posição aproximada (coluna, linha). Não exige
// geometria (D8). O exterior (ZZ) fica à parte.
const POSICAO: Record<string, [number, number]> = {
  RR: [1, 0], AP: [3, 0],
  AM: [0, 1], PA: [1, 1], MA: [2, 1], CE: [3, 1], RN: [4, 1],
  AC: [0, 2], RO: [1, 2], TO: [2, 2], PI: [3, 2], PB: [4, 2],
  MT: [1, 3], GO: [2, 3], BA: [3, 3], PE: [4, 3],
  MS: [1, 4], DF: [2, 4], MG: [3, 4], AL: [4, 4],
  PR: [1, 5], SP: [2, 5], ES: [3, 5], SE: [4, 5],
  SC: [1, 6], RJ: [3, 6],
  RS: [1, 7],
};

export function MapaUfs({ brasil }: { brasil: Brasil }) {
  // mesma cor do candidato no gráfico nacional (ordem do resultado no Brasil)
  const cores = coresPorEntidade(brasil.presidente?.candidatos.map((c) => c.numero) ?? []);
  const cor = (numero: number) => cores.get(String(numero)) ?? corDaPosicao(99);
  const base = `/${brasil.ano}/${brasil.turno}/uf`;
  const porUf = new Map(brasil.ufs.map((u) => [u.uf, u]));
  // o exterior (ZZ) não é UF: aparece à parte, fora da contagem
  const estados = brasil.ufs.filter((u) => u.uf !== "ZZ");
  const vencedores = [...new Map(estados.map((u) => [u.vencedor.numero, u.vencedor])).values()]
    .map((v) => ({ ...v, ufs: estados.filter((u) => u.vencedor.numero === v.numero).length }))
    .sort((a, b) => b.ufs - a.ufs);
  const exterior = porUf.get("ZZ");

  return (
    <figure>
      <div className="mx-auto grid max-w-sm grid-cols-5 gap-1.5" aria-hidden="true">
        {Object.entries(POSICAO).map(([uf, [x, y]]) => {
          const d = porUf.get(uf);
          const c = d ? cor(d.vencedor.numero) : null;
          return (
            <Link
              key={uf}
              href={d ? `${base}/${uf}/` : "#"}
              tabIndex={-1}
              style={{
                gridColumn: x + 1,
                gridRow: y + 1,
                ...(c ? { background: c.fundo, color: c.texto } : {}),
              }}
              className={`flex aspect-square flex-col items-center justify-center rounded-lg text-xs leading-tight transition hover:scale-105 hover:shadow-md ${
                d ? "" : "bg-realce text-texto-3"
              }`}
              title={d ? `${NOME_UF[uf]}: ${d.vencedor.nome} (${pct(d.vencedor.pct)})` : NOME_UF[uf]}
            >
              <span className="font-semibold">{uf}</span>
              {d ? <span className="num text-[10px] opacity-90">{Math.round(d.vencedor.pct ?? 0)}%</span> : null}
            </Link>
          );
        })}
      </div>

      <figcaption className="mt-4 space-y-1.5 text-sm">
        {vencedores.map((v) => (
          <div key={v.numero} className="flex items-center gap-2">
            <span className="size-3 rounded" style={{ background: cor(v.numero).fundo }} aria-hidden="true" />
            <span className="font-medium">{v.nome}</span>
            <span className="text-texto-3">
              venceu em {v.ufs} {v.ufs === 1 ? "UF" : "UFs"}
            </span>
          </div>
        ))}
        {exterior ? (
          <p className="text-xs text-texto-3">
            Exterior: {exterior.vencedor.nome} ({pct(exterior.vencedor.pct)})
          </p>
        ) : null}
      </figcaption>

      <details className="mt-4 rounded-xl border border-borda">
        <summary className="cursor-pointer px-4 py-2.5 text-sm font-medium text-texto-2 hover:text-texto">
          Ver tabela por UF
        </summary>
        <div className="overflow-x-auto px-4 pb-3">
          <table className="w-full text-sm">
            <caption className="sr-only">Mais votado para Presidente por UF</caption>
            <thead>
              <tr className="border-b border-borda text-left text-xs text-texto-3">
                <th scope="col" className="py-2 font-medium">UF</th>
                <th scope="col" className="py-2 font-medium">Mais votado</th>
                <th scope="col" className="py-2 text-right font-medium">Válidos</th>
                <th scope="col" className="py-2 text-right font-medium">Compar.</th>
              </tr>
            </thead>
            <tbody>
              {brasil.ufs.map((u) => (
                <tr key={u.uf} className="border-b border-borda last:border-0">
                  <th scope="row" className="py-1.5 text-left font-normal">
                    <Link href={`${base}/${u.uf}/`} className="hover:underline">
                      {NOME_UF[u.uf] ?? u.uf}
                    </Link>
                  </th>
                  <td className="py-1.5">{u.vencedor.nome}</td>
                  <td className="num py-1.5 text-right">{pct(u.vencedor.pct)}</td>
                  <td className="num py-1.5 text-right text-texto-2">{pct(u.pct_comparecimento)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
