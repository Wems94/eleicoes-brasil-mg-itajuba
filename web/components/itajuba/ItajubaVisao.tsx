import { BarrasTabela } from "@/components/BarrasTabela";
import { CabecalhoPagina, Participacao, SeletorEleicao, Secao } from "@/components/base";
import { BuscaSecao } from "@/components/itajuba/BuscaSecao";
import { MapaParticipacaoItajuba, MapaVotosItajuba } from "@/components/itajuba/MapasItajuba";
import { dados } from "@/lib/dados";
import { nomeTurno, numero, pct } from "@/lib/formato";
import { NOME_CARGO } from "@/lib/itajuba";
import { pontosPorLocal } from "@/lib/itajubaMapa";
import type { CargoVotaveis, Eleicao, Votavel } from "@/lib/tipos";

const MAJORITARIOS = [1, 3, 5];
const validos = (v: Votavel) => v.tipo === "candidato" || v.tipo === "legenda";

function rotulo(v: Votavel): string {
  return v.tipo === "legenda" ? `Legenda ${v.partido ?? v.numero}` : (v.nome ?? `Nº ${v.numero}`);
}

function maisVotado(cargos: CargoVotaveis[], codigo: number): Votavel | undefined {
  return cargos.find((c) => c.codigo === codigo)?.votaveis.find((v) => v.tipo === "candidato");
}

function BrancosNulos({ votaveis }: { votaveis: Votavel[] }) {
  const outros = votaveis.filter((v) => !validos(v));
  if (!outros.length) return null;
  return (
    <p className="num mt-3 text-xs text-texto-2">
      {outros.map((v) => `${v.tipo === "branco" ? "Brancos" : v.tipo === "nulo" ? "Nulos" : "Anulados"}: ${numero(v.votos)}`).join(" · ")}
    </p>
  );
}

export function ItajubaVisao({ ano, turno }: Eleicao) {
  const it = dados.itajuba(ano, turno);
  const municipio = dados.manifesto().municipio;
  const principal = it.cargos.find((c) => c.comparecimento);
  const locais = pontosPorLocal(it, dados.itajubaSecoes(ano, turno));
  // fotos dos presidenciáveis (só Presidente), pelo número de urna
  const fotos = new Map((dados.brasil(ano, turno).presidente?.candidatos ?? []).map((c) => [c.numero, c.foto]));
  const majoritarios = MAJORITARIOS.map((cd) => it.cargos.find((c) => c.codigo === cd)).filter((c) => c != null);
  const ordemPartidos = Object.fromEntries(
    majoritarios.map((c) => [c.codigo, c.votaveis.filter((v) => v.tipo === "candidato").map((v) => v.partido)]),
  );
  const cartao = (c: (typeof majoritarios)[number]) => (
    <Secao key={c.codigo} id={`cargo-${c.codigo}`} titulo={c.nome ?? NOME_CARGO[c.codigo]} sobretitulo="Itajubá">
      <BarrasTabela
        legenda={`${c.nome}, Itajubá: percentual dos votos válidos`}
        ocultarLegenda
        linhas={c.votaveis.filter(validos).map((v) => ({
          chave: `${v.tipo}-${v.numero}`,
          rotulo: rotulo(v),
          detalhe: [v.tipo === "candidato" ? `Nº ${v.numero}` : null, v.partido].filter(Boolean).join(" · "),
          votos: v.votos,
          pct: v.pct,
          destaque: v.posicao === 1,
          partido: v.partido,
          ...(c.codigo === 1 && v.tipo === "candidato" ? { foto: fotos.get(v.numero) ?? null } : {}),
        }))}
      />
      <BrancosNulos votaveis={c.votaveis} />
    </Secao>
  );
  const [presidente, ...outros] = majoritarios;

  return (
    <div className="space-y-6">
      <CabecalhoPagina
        sobretitulo={`Deep dive · ${municipio?.uf ?? "MG"} · ${nomeTurno(turno)} · ${ano}`}
        titulo="Itajubá"
        subtitulo="Resultados por cargo, bairro, local de votação e seção, com abstenção, brancos e nulos."
      >
        <SeletorEleicao
          eleicoes={dados.eleicoes()}
          atual={{ ano, turno }}
          href={(e) => `/itajuba/${e.ano}/${e.turno}/`}
        />
        <nav aria-label="Seções da página" className="flex flex-wrap gap-2 text-sm">
          {[
            ["#cargos", "Por cargo"],
            ["#mapa-votos", "Mapa de votos"],
            ["#participacao", "Abstenção, brancos e nulos"],
            ["#zonas", "Por zona"],
            ["#secao", "Busca de seção"],
          ].map(([href, t]) => (
            <a key={href} href={href} className="rounded-full border border-borda bg-superficie px-3 py-1 text-texto-2 hover:bg-realce hover:text-texto">
              {t}
            </a>
          ))}
        </nav>
      </CabecalhoPagina>

      {it.cargos.length === 0 ? (
        <p className="text-texto-2">Sem votação em Itajubá neste turno.</p>
      ) : null}

      {principal?.comparecimento ? (
        <Participacao
          dados={{
            ...principal.comparecimento,
            pct_brancos: (100 * principal.comparecimento.brancos) / principal.comparecimento.comparecimento,
            pct_nulos: (100 * principal.comparecimento.nulos) / principal.comparecimento.comparecimento,
          }}
        />
      ) : null}

      {presidente ? (
        <div id="cargos" className="grid scroll-mt-20 items-start gap-6 md:grid-cols-2">
          {cartao(presidente)}
          <Secao id="mapa-votos" titulo="Mapa de votos" sobretitulo={`Itajubá · ${locais.length} locais de votação`}>
            {locais.length ? (
              <MapaVotosItajuba locais={locais} ordemPartidos={ordemPartidos} />
            ) : (
              <p className="text-sm text-texto-2">Sem coordenadas dos locais de votação nesta eleição.</p>
            )}
          </Secao>
          {outros.map(cartao)}
        </div>
      ) : null}

      {locais.length ? (
        <Secao id="participacao" titulo="Abstenção, brancos e nulos" sobretitulo="Onde os eleitores não votaram">
          <MapaParticipacaoItajuba locais={locais} />
        </Secao>
      ) : null}

      {it.zonas.length ? (
        <Secao id="zonas" titulo="Por zona eleitoral" sobretitulo="Zonas">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] text-sm">
              <caption className="sr-only">Mais votado por zona eleitoral de Itajubá</caption>
              <thead>
                <tr className="border-b border-borda text-left text-xs text-texto-2">
                  <th scope="col" className="py-1 font-medium">Zona</th>
                  {MAJORITARIOS.filter((cd) => it.cargos.some((c) => c.codigo === cd)).map((cd) => (
                    <th key={cd} scope="col" className="py-1 font-medium">{NOME_CARGO[cd]}: mais votado</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {it.zonas.map((z) => (
                  <tr key={z.zona} className="border-b border-borda">
                    <th scope="row" className="num py-1 text-left font-normal">{z.zona}</th>
                    {MAJORITARIOS.filter((cd) => it.cargos.some((c) => c.codigo === cd)).map((cd) => {
                      const v = maisVotado(z.cargos, cd);
                      return (
                        <td key={cd} className="py-1">
                          {v ? <>{v.nome} <span className="num text-texto-2">{pct(v.pct)}</span></> : "—"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Secao>
      ) : null}

      <Secao id="secao" titulo="Busca de seção" sobretitulo="Sua seção">
        <BuscaSecao ano={ano} turno={turno} />
      </Secao>

    </div>
  );
}
