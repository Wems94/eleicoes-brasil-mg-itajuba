import { BarrasTabela } from "@/components/BarrasTabela";
import { TabelaDeputados } from "@/components/TabelaDeputados";
import { CabecalhoPagina, Participacao, SeletorEleicao, Secao } from "@/components/base";
import { BuscaSecao } from "@/components/itajuba/BuscaSecao";
import { MapaLocais, type PontoLocal } from "@/components/itajuba/MapaLocais";
import { dados } from "@/lib/dados";
import { deputadosDeItajuba } from "@/lib/deputados";
import { nomeTurno, numero, pct } from "@/lib/formato";
import { coresPorEntidade } from "@/lib/cores";
import { NOME_CARGO, historicoPorCargo } from "@/lib/itajuba";
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
  const uf = municipio?.uf ?? "MG";
  const deputados = deputadosDeItajuba(ano, turno);
  const principal = it.cargos.find((c) => c.comparecimento);
  const cargoMapa = MAJORITARIOS.find((cd) => it.cargos.some((c) => c.codigo === cd)) ?? 1;

  const pontos: PontoLocal[] = it.locais
    .filter((l) => l.lat != null && l.lon != null)
    .map((l) => {
      const v = maisVotado(l.cargos, cargoMapa);
      return {
        local: l.local,
        nome: l.nome ?? `Local ${l.local}`,
        lat: l.lat!,
        lon: l.lon!,
        resumo: `Seções ${l.secoes.join(", ")}${v ? ` · ${NOME_CARGO[cargoMapa]}: ${v.nome} (${pct(v.pct)})` : ""}`,
      };
    });

  return (
    <div className="space-y-6">
      <CabecalhoPagina
        sobretitulo={`Deep dive · ${municipio?.uf ?? "MG"} · ${nomeTurno(turno)} · ${ano}`}
        titulo="Itajubá"
        subtitulo="Resultados por cargo, zona, local de votação e seção, e a comparação entre eleições."
      >
        <SeletorEleicao
          eleicoes={dados.eleicoes()}
          atual={{ ano, turno }}
          href={(e) => `/itajuba/${e.ano}/${e.turno}/`}
        />
        <nav aria-label="Seções da página" className="flex flex-wrap gap-2 text-sm">
          {[
            ["#cargos", "Por cargo"],
            ["#zonas", "Por zona"],
            ["#locais", "Locais de votação"],
            ["#secao", "Busca de seção"],
            ["#comparacao", "Comparação histórica"],
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

      <div id="cargos" className="grid scroll-mt-20 items-start gap-6 md:grid-cols-2">
        {it.cargos
          .filter((c) => MAJORITARIOS.includes(c.codigo))
          .map((c) => (
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
                }))}
              />
              <BrancosNulos votaveis={c.votaveis} />
            </Secao>
          ))}
      </div>

      {it.cargos
        .filter((c) => !MAJORITARIOS.includes(c.codigo))
        .map((c) => (
          <Secao key={c.codigo} id={`cargo-${c.codigo}`} titulo={c.nome ?? NOME_CARGO[c.codigo]} sobretitulo="Itajubá · proporcional">
            <TabelaDeputados
              legenda={`${c.nome} em Itajubá`}
              candidatos={deputados[String(c.codigo)] ?? []}
              codigo={c.codigo}
              urlCompleta={`/dados/${ano}/${turno}/itajuba_deputados.json`}
            />
            <BrancosNulos votaveis={c.votaveis} />
            <p className="mt-1 text-xs text-texto-2">
              Situação: resultado do candidato em {uf}, onde a vaga é disputada.
            </p>
          </Secao>
        ))}

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

      <Secao id="locais" titulo="Locais de votação" sobretitulo={`${it.locais.length} locais`}>
        <MapaLocais pontos={pontos} />
        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[40rem] text-sm">
            <caption className="mb-2 text-left text-xs text-texto-2">
              Locais de votação e mais votado para {NOME_CARGO[cargoMapa]}
            </caption>
            <thead>
              <tr className="border-b border-borda text-left text-xs text-texto-2">
                <th scope="col" className="py-1 font-medium">Local</th>
                <th scope="col" className="py-1 font-medium">Bairro</th>
                <th scope="col" className="py-1 font-medium">Seções</th>
                <th scope="col" className="py-1 font-medium">Mais votado</th>
              </tr>
            </thead>
            <tbody>
              {it.locais.map((l) => {
                const v = maisVotado(l.cargos, cargoMapa);
                return (
                  <tr key={`${l.zona}-${l.local}`} className="border-b border-borda align-top">
                    <th scope="row" className="py-1.5 pr-3 text-left font-normal">
                      {l.nome}
                      {l.endereco ? <span className="block text-xs text-texto-2">{l.endereco}</span> : null}
                    </th>
                    <td className="py-1.5 pr-3">{l.bairro ?? "—"}</td>
                    <td className="num py-1.5 pr-3">{l.secoes.join(", ")}</td>
                    <td className="py-1.5">
                      {v ? <>{v.nome} <span className="num text-texto-2">{pct(v.pct)}</span></> : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Secao>

      <Secao id="secao" titulo="Busca de seção" sobretitulo="Sua seção">
        <BuscaSecao ano={ano} turno={turno} />
      </Secao>

      <Comparacao />
    </div>
  );
}

/** Comparação histórica: votação por partido e comparecimento nos majoritários. */
function Comparacao() {
  const h = dados.historico();
  return (
    <Secao id="comparacao" titulo="Comparação histórica" sobretitulo="2018 · 2022 · 2026">
      <div className="space-y-10">
        {MAJORITARIOS.map((cargo) => {
          const eleicoes = historicoPorCargo(h, cargo);
          if (!eleicoes.length) return null;
          // a cor segue o partido em todos os anos (ordem: total de votos no período)
          const total = new Map<string, number>();
          for (const e of eleicoes) for (const p of e.partidos) total.set(p.partido ?? "—", (total.get(p.partido ?? "—") ?? 0) + p.votos);
          const cores = coresPorEntidade([...total].sort((a, b) => b[1] - a[1]).map(([p]) => p));
          return (
            <div key={cargo}>
              <h3 className="mb-4 text-base font-semibold">{NOME_CARGO[cargo]}</h3>
              <div className="grid gap-8 md:grid-cols-2 xl:grid-cols-3">
                {eleicoes.map((e) => (
                  <BarrasTabela
                    key={`${e.ano}-${e.turno}`}
                    legenda={`${e.ano} · ${nomeTurno(e.turno)}`}
                    rotuloColuna="Partido"
                    linhas={e.partidos.map((p, i) => ({
                      chave: p.partido ?? String(i),
                      rotulo: p.partido ?? "—",
                      votos: p.votos,
                      pct: p.pct,
                      destaque: i === 0,
                      cor: cores.get(p.partido ?? "—"),
                    }))}
                  />
                ))}
              </div>
              <table className="mt-4 w-full max-w-xl text-sm">
                <caption className="mb-1 text-left text-xs text-texto-2">Comparecimento em Itajubá, {NOME_CARGO[cargo]}</caption>
                <thead>
                  <tr className="border-b border-borda text-left text-xs text-texto-2">
                    <th scope="col" className="py-1 font-medium">Eleição</th>
                    <th scope="col" className="py-1 text-right font-medium">Aptos</th>
                    <th scope="col" className="py-1 text-right font-medium">Comparecimento</th>
                    <th scope="col" className="py-1 text-right font-medium">Abstenção</th>
                  </tr>
                </thead>
                <tbody>
                  {eleicoes.map((e) =>
                    e.comparecimento ? (
                      <tr key={`${e.ano}-${e.turno}`} className="border-b border-borda">
                        <th scope="row" className="py-1 text-left font-normal">
                          {e.ano} · {nomeTurno(e.turno)}
                        </th>
                        <td className="num py-1 text-right">{numero(e.comparecimento.aptos)}</td>
                        <td className="num py-1 text-right">{pct(e.comparecimento.pct_comparecimento)}</td>
                        <td className="num py-1 text-right">{pct(e.comparecimento.pct_abstencao)}</td>
                      </tr>
                    ) : null,
                  )}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>
    </Secao>
  );
}
