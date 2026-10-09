import { ListaCompleta } from "@/components/ListaCompleta";
import { CabecaDeputados, LinhasDeputados } from "@/components/LinhasDeputados";
import { eleito, visiveis } from "@/lib/deputados";
import { numero } from "@/lib/formato";
import type { Candidato } from "@/lib/tipos";

/**
 * Deputados: os mais votados e todos os eleitos vêm prontos na página; a lista
 * completa (milhares de nomes em SP) é carregada sob demanda de um JSON estático.
 */
export function TabelaDeputados({
  legenda,
  candidatos,
  urlCompleta,
  codigo,
}: {
  legenda: string;
  candidatos: Candidato[];
  urlCompleta: string;
  codigo: number;
}) {
  const mostrados = visiveis(candidatos);
  const eleitos = candidatos.filter((c) => eleito(c.situacao)).length;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[36rem] text-sm">
        <caption className="mb-2 text-left text-xs text-texto-2">
          {legenda}: {numero(candidatos.length)} candidatos, {numero(eleitos)} eleitos
          {mostrados.length < candidatos.length
            ? ` (mostrando os ${numero(mostrados.length)} mais votados e eleitos)`
            : ""}
        </caption>
        <CabecaDeputados />
        <tbody>
          <LinhasDeputados candidatos={mostrados} />
        </tbody>
      </table>
      {mostrados.length < candidatos.length ? (
        <ListaCompleta
          url={urlCompleta}
          codigo={codigo}
          legenda={legenda}
          ocultos={candidatos.length - mostrados.length}
          jaMostrados={mostrados.map((c) => c.numero)}
        />
      ) : null}
    </div>
  );
}
