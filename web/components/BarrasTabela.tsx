import { type Cor, corDaPosicao } from "@/lib/cores";
import { numero, pct } from "@/lib/formato";

export type LinhaBarra = {
  chave: string;
  rotulo: string;
  detalhe?: string | null; // partido, situação...
  votos: number;
  pct: number | null;
  destaque?: boolean;
  cor?: Cor; // padrão: cor da posição na lista
};

/**
 * Gráfico de barras que é, ele mesmo, uma tabela semântica: o leitor de tela lê
 * os mesmos números que o gráfico mostra (a barra é decorativa, aria-hidden).
 * Escala absoluta (0–100% dos válidos) e rótulos sempre visíveis.
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
      <caption className={ocultarLegenda ? "sr-only" : "mb-3 text-left text-sm font-semibold"}>
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
        {linhas.map((l, i) => {
          const cor = l.cor ?? corDaPosicao(i);
          return (
            <tr key={l.chave} className="group">
              <th scope="row" className="py-2.5 pr-3 text-left align-top font-normal">
                <div className="flex items-center gap-2">
                  <span
                    className="size-2.5 shrink-0 rounded-full"
                    style={{ background: cor.fundo }}
                    aria-hidden="true"
                  />
                  <span className={l.destaque ? "font-semibold" : "font-medium"}>{l.rotulo}</span>
                </div>
                {l.detalhe ? (
                  <span className="mt-0.5 block pl-4.5 text-xs text-texto-3">{l.detalhe}</span>
                ) : null}
                <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-realce" aria-hidden="true">
                  <div
                    className="barra h-full rounded-full"
                    style={{
                      width: `${Math.min(l.pct ?? 0, 100)}%`,
                      background: cor.fundo,
                      ["--i" as string]: i,
                    }}
                  />
                </div>
              </th>
              <td className="num w-20 py-2.5 pl-2 text-right align-top text-base font-semibold">
                {pct(l.pct)}
              </td>
              <td className="num w-24 py-2.5 pl-2 text-right align-top text-xs text-texto-3 sm:text-sm">
                {numero(l.votos)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
