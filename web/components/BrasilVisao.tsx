import Link from "next/link";

import { BarrasTabela } from "@/components/BarrasTabela";
import { MapaMunicipal } from "@/components/mapa/MapaMunicipal";
import { CabecalhoPagina, Participacao, SeletorEleicao, Secao } from "@/components/base";
import { dados } from "@/lib/dados";
import { NOME_UF, nomeTurno, numero, pct } from "@/lib/formato";
import { type Cor, coresDaDisputa } from "@/lib/partidos";
import type { Candidato, Eleicao } from "@/lib/tipos";

function mancheteDoPresidente(c: Candidato[]): string | null {
  const [a, b] = c;
  if (!a) return null;
  if (a.situacao === "ELEITO") return `${a.nome} é eleito Presidente com ${pct(a.pct)} dos votos válidos.`;
  if (b && a.situacao === "2º TURNO" && b.situacao === "2º TURNO") {
    return `${a.nome} (${pct(a.pct)}) e ${b.nome} (${pct(b.pct)}) disputam o 2º turno.`;
  }
  return `${a.nome} lidera para Presidente com ${pct(a.pct)} dos votos válidos.`;
}

function DestaqueItajuba({ ano, turno, cores }: Eleicao & { cores: Map<string, Cor> }) {
  const it = dados.itajuba(ano, turno);
  const cargo = it.cargos.find((c) => c.codigo === 1) ?? it.cargos[0];
  if (!cargo) return null;
  const top = cargo.votaveis.filter((v) => v.tipo === "candidato").slice(0, 3);
  return (
    <Secao
      id="itajuba"
      titulo="Itajubá (MG)"
      sobretitulo={`Em destaque · ${cargo.nome}`}
      acao={
        <Link
          href={`/itajuba/${ano}/${turno}/`}
          className="shrink-0 rounded-lg border border-borda px-3 py-1.5 text-sm font-medium hover:bg-realce"
        >
          Ver Itajubá →
        </Link>
      }
    >
      <BarrasTabela
        legenda={`${cargo.nome} em Itajubá: percentual dos votos válidos`}
        ocultarLegenda
        linhas={top.map((v, i) => ({
          chave: String(v.numero),
          rotulo: v.nome ?? `Nº ${v.numero}`,
          detalhe: v.partido,
          votos: v.votos,
          pct: v.pct,
          destaque: i === 0,
          partido: v.partido,
          // no Presidente, a mesma cor do gráfico nacional desta página
          cor: cargo.codigo === 1 ? cores.get(v.partido ?? "") : undefined,
        }))}
      />
      {cargo.comparecimento ? (
        <p className="num mt-3 text-xs text-texto-3">
          {numero(cargo.comparecimento.comparecimento)} eleitores compareceram ·{" "}
          {pct(cargo.comparecimento.pct_comparecimento)}
        </p>
      ) : null}
    </Secao>
  );
}

/** Props do mapa municipal a partir dos snapshots (cargos do turno, fotos, Itajubá). */
export function propsDoMapa(ano: number, turno: number) {
  const fotos: Record<string, string> = {};
  for (const c of dados.brasil(ano, turno).presidente?.candidatos ?? []) {
    const sq = c.foto?.match(/(\d+)\.jpg$/)?.[1];
    if (sq && c.foto) fotos[sq] = c.foto;
  }
  return {
    ano,
    turno,
    cargos: dados.cargosMapa(ano, turno).map((cargo) => ({ cargo, nome: dados.mapa(ano, turno, cargo).nome })),
    itajuba: dados.manifesto().municipio?.ibge ?? null,
    fotos,
  };
}

export function MapaDaEleicao({ ano, turno, uf }: Eleicao & { uf?: string }) {
  return <MapaMunicipal {...propsDoMapa(ano, turno)} ufInicial={uf ?? null} fixarUf={Boolean(uf)} />;
}

function Hero({ ano, turno }: Eleicao) {
  const m = dados.manifesto();
  return (
    <section aria-labelledby="hero-t" className="mx-auto max-w-3xl pb-4 pt-6 text-center sm:pt-12">
      <p className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-texto-2">
        <span className="size-1.5 rounded-full bg-acento shadow-[0_0_8px_2px_rgb(167_139_250/0.7)]" aria-hidden="true" />
        <span className="font-medium text-texto">Eleições {ano}</span>
        <span aria-hidden="true">·</span> {nomeTurno(turno)}, totalização oficial do TSE
      </p>
      <h1 id="hero-t" className="mt-6 text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl md:text-7xl">
        Cada voto do Brasil,
        <br />
        <span className="texto-degrade">num só mapa.</span>
      </h1>
      <p className="mx-auto mt-6 max-w-2xl text-base text-texto-2 sm:text-lg">
        Resultados oficiais de {m.eleicoes[0]?.ano} a {m.eleicoes[m.eleicoes.length - 1]?.ano} para Presidente,
        Governador, Senador e Deputados, município por município, com a abstenção e o detalhe de cada zona
        eleitoral.
      </p>
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <a href="#mapa" className="botao-principal rounded-xl px-5 py-2.5 text-sm font-semibold text-white">
          Explorar o mapa
        </a>
        <Link
          href={`/itajuba/${ano}/${turno}/`}
          className="rounded-xl border border-white/15 bg-white/[0.03] px-5 py-2.5 text-sm font-medium hover:bg-white/10"
        >
          Ver Itajubá →
        </Link>
      </div>
      <p className="mt-4 text-xs text-texto-3">Sem projeções · dados abertos do TSE e malha do IBGE</p>
    </section>
  );
}

/** Barra lateral do painel: eleições, seções da página e atalhos para as UFs. */
function BarraLateral({ ano, turno }: Eleicao) {
  const ufs = dados.ufs(ano, turno).filter((u) => u !== "ZZ");
  const secoes = [
    ["#participacao", "Participação"],
    ["#presidente", "Presidente"],
    ["#itajuba", "Itajubá (MG)"],
    ["#mapa", "Mapa por município"],
  ];
  const titulo = "mb-2 px-2 text-[11px] font-medium uppercase tracking-wider text-texto-3";
  return (
    <aside className="hidden border-r border-borda p-4 lg:block" aria-label="Navegação do painel">
      <p className={titulo}>Eleição</p>
      <ul className="mb-6 space-y-0.5 text-sm">
        {dados.eleicoes().map((e) => {
          const ativo = e.ano === ano && e.turno === turno;
          return (
            <li key={`${e.ano}-${e.turno}`}>
              <Link
                href={`/${e.ano}/${e.turno}/`}
                aria-current={ativo ? "page" : undefined}
                className={`flex items-center justify-between rounded-lg px-2 py-1.5 transition-colors ${
                  ativo ? "bg-acento-claro text-texto ring-1 ring-acento/30" : "text-texto-2 hover:bg-white/5 hover:text-texto"
                }`}
              >
                <span className="num font-medium">{e.ano}</span>
                <span className="text-xs opacity-80">{nomeTurno(e.turno)}</span>
              </Link>
            </li>
          );
        })}
      </ul>
      <p className={titulo}>Nesta página</p>
      <ul className="mb-6 space-y-0.5 text-sm">
        {secoes.map(([href, rotulo]) => (
          <li key={href}>
            <a href={href} className="block rounded-lg px-2 py-1.5 text-texto-2 hover:bg-white/5 hover:text-texto">
              {rotulo}
            </a>
          </li>
        ))}
      </ul>
      <p className={titulo}>Estados</p>
      <ul className="grid grid-cols-4 gap-1 text-xs">
        {ufs.map((uf) => (
          <li key={uf}>
            <Link
              href={`/${ano}/${turno}/uf/${uf}/`}
              title={NOME_UF[uf]}
              className="block rounded-md py-1 text-center font-medium text-texto-2 ring-1 ring-borda hover:bg-white/5 hover:text-texto"
            >
              {uf}
            </Link>
          </li>
        ))}
      </ul>
    </aside>
  );
}

export function BrasilVisao({ ano, turno, hero = false }: Eleicao & { hero?: boolean }) {
  const b = dados.brasil(ano, turno);
  const candidatos = b.presidente?.candidatos ?? [];
  // cores da disputa nacional, por partido (as mesmas do mapa e do destaque de Itajubá)
  const cores = coresDaDisputa(candidatos.map((c) => c.partido));
  const manchete = mancheteDoPresidente(candidatos);
  return (
    <div className="space-y-10">
      {hero ? (
        <Hero ano={ano} turno={turno} />
      ) : (
        <CabecalhoPagina sobretitulo={`Resultado oficial · ${nomeTurno(turno)}`} titulo={`Eleições ${ano}`} subtitulo={manchete} />
      )}

      <div className="moldura overflow-hidden rounded-2xl border border-borda bg-superficie/80 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-borda px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-2 text-sm">
            <span className="font-semibold">Painel de resultados</span>
            <span className="text-texto-3" aria-hidden="true">·</span>
            <span className="truncate text-texto-2">{hero && manchete ? manchete : `${ano}, ${nomeTurno(turno)}`}</span>
          </div>
          <div className="lg:hidden">
            <SeletorEleicao eleicoes={dados.eleicoes()} atual={{ ano, turno }} href={(e) => `/${e.ano}/${e.turno}/`} />
          </div>
          <span className="hidden items-center gap-1.5 rounded-lg border border-borda px-2.5 py-1 text-xs text-texto-2 lg:inline-flex">
            <span className="size-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
            Totalização oficial
          </span>
        </div>
        <div className="grid lg:grid-cols-[14rem_minmax(0,1fr)]">
          <BarraLateral ano={ano} turno={turno} />
          <div className="min-w-0 space-y-6 p-4 sm:p-6">
      {b.comparecimento ? (
        <div id="participacao" className="scroll-mt-24">
          <Participacao dados={b.comparecimento} />
        </div>
      ) : null}

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <Secao id="presidente" titulo="Presidente" sobretitulo="Brasil">
            {b.presidente ? (
              <>
                <BarrasTabela
                  legenda={`Presidente, ${ano}, ${nomeTurno(turno)}: percentual dos votos válidos`}
                  ocultarLegenda
                  linhas={candidatos.map((c) => ({
                    chave: String(c.numero),
                    rotulo: c.nome,
                    detalhe: [`Nº ${c.numero}`, c.partido, c.federacao, c.situacao].filter(Boolean).join(" · "),
                    votos: c.votos,
                    pct: c.pct,
                    destaque: c.posicao === 1,
                    partido: c.partido,
                    foto: c.foto,
                    cor: cores.get(c.partido ?? ""),
                  }))}
                />
                <p className="num mt-3 text-xs text-texto-3">{numero(b.presidente.votos_validos)} votos válidos</p>
              </>
            ) : (
              <p className="text-texto-2">Sem disputa presidencial neste turno.</p>
            )}
          </Secao>
        <DestaqueItajuba ano={ano} turno={turno} cores={cores} />
      </div>

      <Secao id="mapa" titulo="Resultado por município" sobretitulo="Mapa">
        <MapaDaEleicao ano={ano} turno={turno} />
      </Secao>
          </div>
        </div>
      </div>
    </div>
  );
}
