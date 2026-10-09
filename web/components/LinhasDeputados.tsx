import { numero, pct } from "@/lib/formato";
import type { Candidato } from "@/lib/tipos";

// Sem acesso a arquivos: usado tanto no servidor quanto no componente de cliente.
const eleito = (s: string | null) => !!s && s.startsWith("ELEITO");

export function LinhasDeputados({ candidatos }: { candidatos: Candidato[] }) {
  return candidatos.map((c) => (
    <tr key={c.numero} className="border-b border-borda last:border-0">
      <td className="num py-1.5 pr-2 text-right text-texto-2">{c.posicao}º</td>
      <th scope="row" className="py-1.5 pr-2 text-left font-normal">
        <span className={eleito(c.situacao) ? "font-semibold" : undefined}>{c.nome}</span>
        <span className="num ml-1.5 text-xs text-texto-2">{c.numero}</span>
      </th>
      <td className="py-1.5 pr-2 text-texto-2">{c.partido}</td>
      <td className="num py-1.5 pr-2 text-right">{numero(c.votos)}</td>
      <td className="num py-1.5 pr-2 text-right">{pct(c.pct)}</td>
      <td className="py-1.5 text-xs">
        {c.situacao ? (
          <span
            className={`inline-block rounded-md px-1.5 py-0.5 font-medium ${
              eleito(c.situacao) ? "bg-texto text-superficie" : "bg-realce text-texto-2"
            }`}
          >
            {c.situacao}
          </span>
        ) : (
          "—"
        )}
      </td>
    </tr>
  ));
}

export function CabecaDeputados() {
  return (
    <thead>
      <tr className="border-b border-borda text-left text-xs text-texto-2">
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
