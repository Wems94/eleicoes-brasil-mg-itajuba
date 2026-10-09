import { numero, pct } from "@/lib/formato";
import type { Candidato } from "@/lib/tipos";

const VISIVEIS = 25;

const eleito = (s: string | null) => !!s && s.startsWith("ELEITO");

function Linhas({ candidatos }: { candidatos: Candidato[] }) {
  return candidatos.map((c) => (
    <tr key={c.numero} className={`border-b border-regua ${eleito(c.situacao) ? "bg-ocre-claro/40" : ""}`}>
      <td className="num py-1.5 pr-2 text-right text-tinta-2">{c.posicao}º</td>
      <th scope="row" className="py-1.5 pr-2 text-left font-normal">
        <span className={eleito(c.situacao) ? "font-semibold" : undefined}>{c.nome}</span>
        <span className="num ml-1.5 text-xs text-tinta-2">{c.numero}</span>
      </th>
      <td className="py-1.5 pr-2 text-tinta-2">{c.partido}</td>
      <td className="num py-1.5 pr-2 text-right">{numero(c.votos)}</td>
      <td className="num py-1.5 pr-2 text-right">{pct(c.pct)}</td>
      <td className="py-1.5 text-xs">{c.situacao ?? "—"}</td>
    </tr>
  ));
}

function Cabeca() {
  return (
    <thead>
      <tr className="border-b border-tinta text-left text-xs text-tinta-2">
        <th scope="col" className="py-1 pr-2 text-right font-medium">#</th>
        <th scope="col" className="py-1 pr-2 font-medium">Candidato</th>
        <th scope="col" className="py-1 pr-2 font-medium">Partido</th>
        <th scope="col" className="py-1 pr-2 text-right font-medium">Votos</th>
        <th scope="col" className="py-1 pr-2 text-right font-medium">Válidos</th>
        <th scope="col" className="py-1 font-medium">Situação</th>
      </tr>
    </thead>
  );
}

/** Deputados: os mais votados à vista e a lista completa sob demanda. */
export function TabelaDeputados({ legenda, candidatos }: { legenda: string; candidatos: Candidato[] }) {
  const resto = candidatos.slice(VISIVEIS);
  const eleitos = candidatos.filter((c) => eleito(c.situacao)).length;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[36rem] text-sm">
        <caption className="mb-2 text-left text-xs text-tinta-2">
          {legenda}: {numero(candidatos.length)} candidatos, {numero(eleitos)} eleitos
        </caption>
        <Cabeca />
        <tbody>
          <Linhas candidatos={candidatos.slice(0, VISIVEIS)} />
        </tbody>
      </table>
      {resto.length ? (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm text-ocre hover:underline">
            Ver os outros {numero(resto.length)} candidatos
          </summary>
          <table className="mt-2 w-full min-w-[36rem] text-sm">
            <caption className="sr-only">{legenda}: demais candidatos</caption>
            <Cabeca />
            <tbody>
              <Linhas candidatos={resto} />
            </tbody>
          </table>
        </details>
      ) : null}
    </div>
  );
}
