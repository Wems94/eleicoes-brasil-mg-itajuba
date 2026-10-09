import Link from "next/link";

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

// Marcas neutras por colocação nacional do vencedor: nunca cores partidárias.
const MARCA = [
  "bg-tinta text-papel",
  "text-tinta bg-[repeating-linear-gradient(135deg,var(--color-barra-2)_0_3px,transparent_3px_7px)]",
  "text-tinta border-2 border-dashed border-barra",
];

export function MapaUfs({ brasil }: { brasil: Brasil }) {
  const ordem = new Map(brasil.presidente?.candidatos.map((c, i) => [c.numero, i]) ?? []);
  const marca = (numero: number) => MARCA[Math.min(ordem.get(numero) ?? 2, MARCA.length - 1)];
  const base = `/${brasil.ano}/${brasil.turno}/uf`;
  const porUf = new Map(brasil.ufs.map((u) => [u.uf, u]));
  const vencedores = [
    ...new Map(brasil.ufs.map((u) => [u.vencedor.numero, u.vencedor])).values(),
  ].sort((a, b) => (ordem.get(a.numero) ?? 99) - (ordem.get(b.numero) ?? 99));

  return (
    <figure>
      <div
        className="grid aspect-[5/8] max-w-sm grid-cols-5 grid-rows-8 gap-1"
        aria-hidden="true"
      >
        {Object.entries(POSICAO).map(([uf, [x, y]]) => {
          const d = porUf.get(uf);
          return (
            <Link
              key={uf}
              href={d ? `${base}/${uf}/` : "#"}
              tabIndex={-1}
              style={{ gridColumn: x + 1, gridRow: y + 1 }}
              className={`flex flex-col items-center justify-center text-xs leading-tight transition-transform hover:scale-105 ${
                d ? marca(d.vencedor.numero) : "border border-regua text-tinta-2"
              }`}
              title={d ? `${NOME_UF[uf]}: ${d.vencedor.nome} (${pct(d.vencedor.pct)})` : uf}
            >
              <span className="font-semibold">{uf}</span>
              {d ? <span className="num text-[10px] opacity-80">{d.vencedor.numero}</span> : null}
            </Link>
          );
        })}
      </div>
      <figcaption className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-tinta-2">
        {vencedores.map((v) => (
          <span key={v.numero} className="flex items-center gap-1.5">
            <span className={`inline-block size-3 ${marca(v.numero)}`} aria-hidden="true" />
            {v.numero} · {v.nome}
          </span>
        ))}
      </figcaption>

      <table className="mt-6 w-full text-sm">
        <caption className="mb-2 text-left text-xs uppercase tracking-wider text-tinta-2">
          Mais votado para Presidente por UF
        </caption>
        <thead>
          <tr className="border-b border-tinta text-left text-xs text-tinta-2">
            <th scope="col" className="py-1 font-medium">UF</th>
            <th scope="col" className="py-1 font-medium">Mais votado</th>
            <th scope="col" className="py-1 text-right font-medium">Válidos</th>
            <th scope="col" className="py-1 text-right font-medium">Comparecimento</th>
          </tr>
        </thead>
        <tbody>
          {brasil.ufs.map((u) => (
            <tr key={u.uf} className="border-b border-regua">
              <th scope="row" className="py-1 text-left font-normal">
                <Link href={`${base}/${u.uf}/`} className="underline decoration-regua underline-offset-2 hover:decoration-ocre">
                  {NOME_UF[u.uf] ?? u.uf}
                </Link>
              </th>
              <td className="py-1">
                {u.vencedor.nome} <span className="text-tinta-2">({u.vencedor.partido})</span>
              </td>
              <td className="num py-1 text-right">{pct(u.vencedor.pct)}</td>
              <td className="num py-1 text-right">{pct(u.pct_comparecimento)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
