import { BarrasTabela } from "@/components/BarrasTabela";
import { TabelaDeputados } from "@/components/TabelaDeputados";
import { Participacao, SeletorEleicao, Secao } from "@/components/base";
import { BuscaSecao } from "@/components/itajuba/BuscaSecao";
import { MapaLocais, type PontoLocal } from "@/components/itajuba/MapaLocais";
import { dados } from "@/lib/dados";
import { nomeTurno, numero, pct } from "@/lib/formato";
import { NOME_CARGO, historicoPorCargo } from "@/lib/itajuba";
import type { CargoVotaveis, Eleicao, Votavel } from "@/lib/tipos";

const MAJORITARIOS = [1, 3, 5];
const validos = (v: Votavel) => v.tipo === "candidato" || v.tipo === "legenda";

function rotulo(v: Votavel): string {
  return v.tipo === "legenda" ? `Legenda ${v.partido ?? v.numero}` : `${v.numero} · ${v.nome}`;
}

function maisVotado(cargos: CargoVotaveis[], codigo: number): Votavel | undefined {
  return cargos.find((c) => c.codigo === codigo)?.votaveis.find((v) => v.tipo === "candidato");
}

function BrancosNulos({ votaveis }: { votaveis: Votavel[] }) {
  const outros = votaveis.filter((v) => !validos(v));
  if (!outros.length) return null;
  return (
    <p className="num mt-3 text-xs text-tinta-2">
      {outros.map((v) => `${v.tipo === "branco" ? "Brancos" : v.tipo === "nulo" ? "Nulos" : "Anulados"}: ${numero(v.votos)}`).join(" · ")}
    </p>
  );
}

export function ItajubaVisao({ ano, turno }: Eleicao) {
  const it = dados.itajuba(ano, turno);
  const municipio = dados.manifesto().municipio;
  // Situação do deputado (eleito, suplente...) é estadual: vem da página da UF.
  const uf = municipio?.uf ?? "MG";
  const situacaoNaUf = new Map<string, string | null>(
    dados.ufs(ano, turno).includes(uf)
      ? dados
          .uf(ano, turno, uf)
          .cargos.flatMap((c) => c.candidatos.map((k) => [`${c.codigo}-${k.numero}`, k.situacao]))
      : [],
  );
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
    <div className="space-y-12">
      <header className="space-y-5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ocre">
          Deep dive · {municipio?.uf ?? "MG"} · {nomeTurno(turno)}
        </p>
        <h1 className="font-display text-4xl font-semibold tracking-tight sm:text-6xl">
          Itajubá <span className="font-normal italic text-tinta-2">{ano}</span>
        </h1>
        <SeletorEleicao
          eleicoes={dados.eleicoes()}
          atual={{ ano, turno }}
          href={(e) => `/itajuba/${e.ano}/${e.turno}/`}
        />
        <nav aria-label="Seções da página" className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
          {[
            ["#cargos", "Por cargo"],
            ["#zonas", "Por zona"],
            ["#locais", "Locais de votação"],
            ["#secao", "Busca de seção"],
            ["#comparacao", "Comparação histórica"],
          ].map(([href, t]) => (
            <a key={href} href={href} className="underline decoration-regua underline-offset-4 hover:decoration-ocre">
              {t}
            </a>
          ))}
        </nav>
      </header>

      {it.cargos.length === 0 ? (
        <p className="text-tinta-2">Sem votação em Itajubá neste turno.</p>
      ) : null}

      {principal?.comparecimento ? (
        <Secao id="participacao" titulo="Participação" sobretitulo={principal.nome ?? undefined}>
          <Participacao
            dados={{
              ...principal.comparecimento,
              pct_brancos: (100 * principal.comparecimento.brancos) / principal.comparecimento.comparecimento,
              pct_nulos: (100 * principal.comparecimento.nulos) / principal.comparecimento.comparecimento,
            }}
          />
          <p className="num mt-2 text-xs text-tinta-2">{numero(principal.comparecimento.aptos)} eleitores aptos</p>
        </Secao>
      ) : null}

      <div id="cargos" className="grid gap-12 md:grid-cols-2">
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
                  detalhe: v.partido,
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
              candidatos={c.votaveis
                .filter((v) => v.tipo === "candidato")
                .map((v) => ({
                  numero: v.numero,
                  nome: v.nome ?? `Nº ${v.numero}`,
                  partido: v.partido,
                  federacao: null,
                  votos: v.votos,
                  pct: v.pct,
                  situacao: situacaoNaUf.get(`${c.codigo}-${v.numero}`) ?? null,
                  posicao: v.posicao ?? 0,
                }))}
            />
            <BrancosNulos votaveis={c.votaveis} />
            <p className="mt-1 text-xs text-tinta-2">
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
                <tr className="border-b border-tinta text-left text-xs text-tinta-2">
                  <th scope="col" className="py-1 font-medium">Zona</th>
                  {MAJORITARIOS.filter((cd) => it.cargos.some((c) => c.codigo === cd)).map((cd) => (
                    <th key={cd} scope="col" className="py-1 font-medium">{NOME_CARGO[cd]}: mais votado</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {it.zonas.map((z) => (
                  <tr key={z.zona} className="border-b border-regua">
                    <th scope="row" className="num py-1 text-left font-normal">{z.zona}</th>
                    {MAJORITARIOS.filter((cd) => it.cargos.some((c) => c.codigo === cd)).map((cd) => {
                      const v = maisVotado(z.cargos, cd);
                      return (
                        <td key={cd} className="py-1">
                          {v ? <>{v.nome} <span className="num text-tinta-2">{pct(v.pct)}</span></> : "—"}
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
            <caption className="mb-2 text-left text-xs text-tinta-2">
              Locais de votação e mais votado para {NOME_CARGO[cargoMapa]}
            </caption>
            <thead>
              <tr className="border-b border-tinta text-left text-xs text-tinta-2">
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
                  <tr key={`${l.zona}-${l.local}`} className="border-b border-regua align-top">
                    <th scope="row" className="py-1.5 pr-3 text-left font-normal">
                      {l.nome}
                      {l.endereco ? <span className="block text-xs text-tinta-2">{l.endereco}</span> : null}
                    </th>
                    <td className="py-1.5 pr-3">{l.bairro ?? "—"}</td>
                    <td className="num py-1.5 pr-3">{l.secoes.join(", ")}</td>
                    <td className="py-1.5">
                      {v ? <>{v.nome} <span className="num text-tinta-2">{pct(v.pct)}</span></> : "—"}
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
      <div className="space-y-12">
        {MAJORITARIOS.map((cargo) => {
          const eleicoes = historicoPorCargo(h, cargo);
          if (!eleicoes.length) return null;
          return (
            <div key={cargo}>
              <h3 className="mb-4 font-display text-xl font-semibold">{NOME_CARGO[cargo]}</h3>
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
                    }))}
                  />
                ))}
              </div>
              <table className="mt-4 w-full max-w-xl text-sm">
                <caption className="mb-1 text-left text-xs text-tinta-2">Comparecimento em Itajubá, {NOME_CARGO[cargo]}</caption>
                <thead>
                  <tr className="border-b border-tinta text-left text-xs text-tinta-2">
                    <th scope="col" className="py-1 font-medium">Eleição</th>
                    <th scope="col" className="py-1 text-right font-medium">Aptos</th>
                    <th scope="col" className="py-1 text-right font-medium">Comparecimento</th>
                    <th scope="col" className="py-1 text-right font-medium">Abstenção</th>
                  </tr>
                </thead>
                <tbody>
                  {eleicoes.map((e) =>
                    e.comparecimento ? (
                      <tr key={`${e.ano}-${e.turno}`} className="border-b border-regua">
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
