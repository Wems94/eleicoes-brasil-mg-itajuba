import { numero, pct } from "@/lib/formato";

export type LinhaBarra = {
  chave: string;
  rotulo: string;
  detalhe?: string | null; // partido, situação...
  votos: number;
  pct: number | null;
  destaque?: boolean;
};

/**
 * Gráfico de barras que é, ele mesmo, uma tabela semântica: o leitor de tela lê
 * os mesmos números que o gráfico mostra (a barra é decorativa, aria-hidden).
 */
export function BarrasTabela({
  legenda,
  linhas,
  rotuloColuna = "Candidato",
  ocultarLegenda = false,
}: {
  legenda: string;
  linhas: LinhaBarra[];
  rotuloColuna?: string;
  ocultarLegenda?: boolean;
}) {
  return (
    <table className="w-full border-collapse text-sm">
      <caption
        className={
          ocultarLegenda
            ? "sr-only"
            : "mb-3 text-left font-display text-lg font-semibold tracking-tight"
        }
      >
        {legenda}
      </caption>
      <thead className="sr-only">
        <tr>
          <th scope="col">{rotuloColuna}</th>
          <th scope="col">Percentual dos votos válidos</th>
          <th scope="col">Votos</th>
        </tr>
      </thead>
      <tbody>
        {linhas.map((l, i) => (
          <tr key={l.chave} className="border-t border-regua first:border-t-0">
            <th scope="row" className="w-[42%] py-2 pr-3 text-left align-top font-normal">
              <span className={l.destaque ? "font-semibold" : undefined}>{l.rotulo}</span>
              {l.detalhe ? (
                <span className="block text-xs text-tinta-2">{l.detalhe}</span>
              ) : null}
            </th>
            <td className="py-2 pr-3 align-middle">
              <div className="flex items-center gap-2">
                <div className="h-3 flex-1 bg-papel-2" aria-hidden="true">
                  <div
                    className={`barra h-full ${l.destaque ? "bg-ocre" : "bg-barra"}`}
                    style={{
                      // escala absoluta: a barra mede o percentual real, sem exagerar diferenças
                      width: `${Math.min(l.pct ?? 0, 100)}%`,
                      ["--i" as string]: i,
                    }}
                  />
                </div>
                <span className="num w-16 text-right">{pct(l.pct)}</span>
              </div>
            </td>
            <td className="num py-2 text-right align-middle text-tinta-2">{numero(l.votos)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
