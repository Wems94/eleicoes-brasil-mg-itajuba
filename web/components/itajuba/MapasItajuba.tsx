"use client";

import { useMemo, useState } from "react";

import { MapaPontos, Pilulas, type Ponto } from "@/components/itajuba/MapaPontos";
import { numero, pct } from "@/lib/formato";
import { NOME_CARGO } from "@/lib/itajuba";
import {
  BASE_METRICA,
  CARGOS_ITAJUBA,
  FAIXAS_METRICA,
  type Metrica,
  NOME_METRICA,
  type PontoItajuba,
  colocados,
  pontosPorBairro,
  raio,
  taxa,
} from "@/lib/itajubaMapa";
import { NEUTRO, corAbstencao, corIntensidade, coresDaDisputa, faixa, rotuloFaixas } from "@/lib/partidos";

type Agrupamento = "bairro" | "local";
const AGRUPAMENTOS = [
  ["bairro", "Por bairro"],
  ["local", "Por local de votação"],
] as const;

// Escala sequencial da abstenção do mapa do Brasil, reaproveitada por faixa (0 a 4).
const COR_FAIXA = [0, 15, 20, 25, 30].map((l) => corAbstencao(l, "escuro"));

function usePontos(locais: PontoItajuba[], agrupamento: Agrupamento) {
  const bairros = useMemo(() => pontosPorBairro(locais), [locais]);
  const pontos = agrupamento === "bairro" ? bairros : locais;
  const maximo = Math.max(1, ...pontos.map((p) => p.aptos));
  return { pontos, maximo };
}

function cargosDisponiveis(locais: PontoItajuba[]) {
  return CARGOS_ITAJUBA.filter((c) => locais.some((l) => (l.votos[String(c)] ?? []).length)).map(
    (c) => [c, NOME_CARGO[c]] as const,
  );
}

/** Mapa de votos: cada bairro (ou local) na cor do partido do mais votado. */
export function MapaVotosItajuba({
  locais,
  ordemPartidos,
}: {
  locais: PontoItajuba[];
  ordemPartidos: Record<string, (string | null)[]>; // por cargo: siglas na ordem de votos na cidade
}) {
  const cargos = cargosDisponiveis(locais);
  const [cargo, setCargo] = useState<number>(cargos[0]?.[0] ?? 1);
  const [agrupamento, setAgrupamento] = useState<Agrupamento>("bairro");
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const { pontos, maximo } = usePontos(locais, agrupamento);
  const cores = useMemo(() => coresDaDisputa(ordemPartidos[String(cargo)] ?? []), [ordemPartidos, cargo]);

  const pontosMapa: Ponto[] = useMemo(
    () =>
      pontos.map((p) => {
        const [v1, v2] = colocados(p, cargo, 2);
        const base = v1 ? (cores.get(v1.partido ?? "")?.fundo ?? NEUTRO.semDados.escuro) : NEUTRO.semDados.escuro;
        return {
          id: p.id,
          nome: p.nome,
          lat: p.lat,
          lon: p.lon,
          raio: raio(p.aptos, maximo),
          cor: v1 ? corIntensidade(base, v1.pct, "escuro") : NEUTRO.semDados.escuro,
          linhas: [
            ...(v1 ? [`${v1.nome} (${v1.partido ?? "—"}) · ${pct(v1.pct)}`] : ["Sem votos"]),
            ...(v2 ? [`${v2.nome} (${v2.partido ?? "—"}) · ${pct(v2.pct)}`] : []),
            `${numero(p.aptos)} eleitores`,
          ],
        };
      }),
    [pontos, cargo, cores, maximo],
  );

  // legenda: só os partidos que vencem em algum ponto
  const vencedores = useMemo(() => {
    const vistos = new Map<string, { nome: string; partido: string | null; pontos: number }>();
    for (const p of pontos) {
      const [v] = colocados(p, cargo, 1);
      if (!v) continue;
      const k = String(v.numero);
      vistos.set(k, { nome: v.nome, partido: v.partido, pontos: (vistos.get(k)?.pontos ?? 0) + 1 });
    }
    return [...vistos.values()].sort((a, b) => b.pontos - a.pontos);
  }, [pontos, cargo]);

  const atual = pontos.find((p) => p.id === selecionado) ?? null;
  const unidade = agrupamento === "bairro" ? "bairros" : "locais de votação";

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        <Pilulas rotulo="Cargo" opcoes={cargos} valor={cargo} onMudar={setCargo} />
        <Pilulas
          rotulo="Agrupar"
          opcoes={AGRUPAMENTOS}
          valor={agrupamento}
          onMudar={(a) => {
            setAgrupamento(a);
            setSelecionado(null);
          }}
        />
      </div>
      <MapaPontos
        pontos={pontosMapa}
        selecionado={selecionado}
        onSelecionar={setSelecionado}
        rotulo={`Mapa de Itajubá com o mais votado para ${NOME_CARGO[cargo]} em ${pontos.length} ${unidade}; os números estão na tabela abaixo.`}
      />
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs" aria-label="Legenda: mais votados">
        {vencedores.map((v) => (
          <li key={v.nome} className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full" style={{ background: cores.get(v.partido ?? "")?.fundo }} aria-hidden="true" />
            <span className="text-texto">{v.nome}</span>
            <span className="text-texto-2">
              {v.partido} · vence em {v.pontos} de {pontos.length}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-1 text-xs text-texto-3">
        Cor mais forte = vitória mais folgada. Tamanho do círculo = número de eleitores.
      </p>

      {atual ? (
        <CardPonto ponto={atual} onFechar={() => setSelecionado(null)}>
          <ol className="mt-2 space-y-1 text-sm">
            {colocados(atual, cargo, 3).map((v, i) => (
              <li key={v.numero} className="flex justify-between gap-4">
                <span>
                  {i + 1}. {v.nome} <span className="text-texto-2">({v.partido ?? "—"})</span>
                </span>
                <span className="num text-texto-2">
                  {pct(v.pct)} · {numero(v.votos)}
                </span>
              </li>
            ))}
          </ol>
        </CardPonto>
      ) : null}

      <details className="mt-4 rounded-xl border border-borda px-4 py-2 text-sm">
        <summary className="cursor-pointer text-texto-2 hover:text-texto">
          Ver tabela: mais votado por {agrupamento === "bairro" ? "bairro" : "local de votação"}
        </summary>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[32rem] text-sm">
            <caption className="sr-only">
              Mais votado para {NOME_CARGO[cargo]} por {agrupamento === "bairro" ? "bairro" : "local de votação"} em Itajubá
            </caption>
            <thead>
              <tr className="border-b border-borda text-left text-xs text-texto-2">
                <th scope="col" className="py-1 font-medium">{agrupamento === "bairro" ? "Bairro" : "Local"}</th>
                <th scope="col" className="py-1 font-medium">Mais votado</th>
                <th scope="col" className="py-1 text-right font-medium">%</th>
                <th scope="col" className="py-1 text-right font-medium">Eleitores</th>
              </tr>
            </thead>
            <tbody>
              {pontos.map((p) => {
                const [v] = colocados(p, cargo, 1);
                return (
                  <tr key={p.id} className="border-b border-borda align-top">
                    <th scope="row" className="py-1.5 pr-3 text-left font-normal">
                      {p.nome}
                      {agrupamento === "local" ? <span className="block text-xs text-texto-2">{p.bairro}</span> : null}
                    </th>
                    <td className="py-1.5 pr-3">{v ? `${v.nome} (${v.partido ?? "—"})` : "—"}</td>
                    <td className="num py-1.5 pr-3 text-right">{v ? pct(v.pct) : "—"}</td>
                    <td className="num py-1.5 text-right">{numero(p.aptos)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

/** Mapa de participação: abstenção, brancos ou nulos por bairro ou local, com as seções. */
export function MapaParticipacaoItajuba({ locais }: { locais: PontoItajuba[] }) {
  const cargos = cargosDisponiveis(locais);
  const [metrica, setMetrica] = useState<Metrica>("abstencao");
  const [cargo, setCargo] = useState<number>(cargos[0]?.[0] ?? 1);
  const [agrupamento, setAgrupamento] = useState<Agrupamento>("bairro");
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const { pontos, maximo } = usePontos(locais, agrupamento);
  const faixas = FAIXAS_METRICA[metrica];
  const chaveCargo = String(cargo);

  const pontosMapa: Ponto[] = useMemo(
    () =>
      pontos.map((p) => {
        const t = taxa(p.participacao[chaveCargo], metrica);
        const pp = p.participacao[chaveCargo];
        return {
          id: p.id,
          nome: p.nome,
          lat: p.lat,
          lon: p.lon,
          raio: raio(p.aptos, maximo),
          cor: t == null ? NEUTRO.semDados.escuro : COR_FAIXA[faixa(t, faixas)],
          linhas: pp
            ? [
                `Abstenção ${pct(taxa(pp, "abstencao") ?? 0)} · Brancos ${pct(taxa(pp, "brancos") ?? 0)} · Nulos ${pct(taxa(pp, "nulos") ?? 0)}`,
                `${numero(pp.aptos)} eleitores · ${p.secoes.length} seções`,
              ]
            : ["Sem dados"],
        };
      }),
    [pontos, chaveCargo, metrica, faixas, maximo],
  );

  const atual = pontos.find((p) => p.id === selecionado) ?? null;
  const rotulos = rotuloFaixas(faixas);
  const nomeUnidade = agrupamento === "bairro" ? "bairro" : "local de votação";

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        <Pilulas
          rotulo="Indicador"
          opcoes={[
            ["abstencao", "Abstenção"],
            ["brancos", "Brancos"],
            ["nulos", "Nulos"],
          ]}
          valor={metrica}
          onMudar={setMetrica}
        />
        {metrica !== "abstencao" ? <Pilulas rotulo="Cargo" opcoes={cargos} valor={cargo} onMudar={setCargo} /> : null}
        <Pilulas
          rotulo="Agrupar"
          opcoes={AGRUPAMENTOS}
          valor={agrupamento}
          onMudar={(a) => {
            setAgrupamento(a);
            setSelecionado(null);
          }}
        />
      </div>
      <label className="mb-3 flex flex-wrap items-center gap-2 text-sm text-texto-2">
        Filtrar {nomeUnidade}:
        <select
          value={selecionado ?? ""}
          onChange={(e) => setSelecionado(e.target.value || null)}
          className="rounded-lg border border-borda bg-[#12101c] px-3 py-1.5 text-texto"
        >
          <option value="">Todos</option>
          {pontos.map((p) => (
            <option key={p.id} value={p.id}>
              {p.nome}
            </option>
          ))}
        </select>
      </label>
      <MapaPontos
        pontos={pontosMapa}
        selecionado={selecionado}
        onSelecionar={setSelecionado}
        rotulo={`Mapa de Itajubá: ${NOME_METRICA[metrica].toLowerCase()} por ${nomeUnidade}; os números estão na tabela abaixo.`}
      />
      <ul className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs" aria-label="Legenda">
        <li className="text-texto-2">
          {NOME_METRICA[metrica]} {BASE_METRICA[metrica]}:
        </li>
        {rotulos.map((r, i) => (
          <li key={r} className="flex items-center gap-1.5">
            <span className="h-2.5 w-4 rounded-sm" style={{ background: COR_FAIXA[i] }} aria-hidden="true" />
            <span className="text-texto">{r}</span>
          </li>
        ))}
      </ul>
      {metrica === "abstencao" ? (
        <p className="mt-1 text-xs text-texto-3">A abstenção é a mesma para todos os cargos; brancos e nulos variam por cargo.</p>
      ) : null}

      {atual ? (
        <CardPonto ponto={atual} onFechar={() => setSelecionado(null)}>
          <TabelaSecoes ponto={atual} cargo={chaveCargo} />
        </CardPonto>
      ) : (
        <details className="mt-4 rounded-xl border border-borda px-4 py-2 text-sm">
          <summary className="cursor-pointer text-texto-2 hover:text-texto">Ver tabela por {nomeUnidade}</summary>
          <div className="mt-3 overflow-x-auto">
            <TabelaParticipacao pontos={pontos} cargo={chaveCargo} rotulo={agrupamento === "bairro" ? "Bairro" : "Local"} />
          </div>
        </details>
      )}
    </div>
  );
}

function CardPonto({ ponto, onFechar, children }: { ponto: PontoItajuba; onFechar: () => void; children: React.ReactNode }) {
  return (
    <div className="mt-4 rounded-xl border border-acento/40 bg-white/[0.03] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-texto">{ponto.nome}</p>
          {ponto.detalhe ? <p className="text-xs text-texto-2">{ponto.detalhe}</p> : null}
          <p className="num text-xs text-texto-2">
            {numero(ponto.aptos)} eleitores · {ponto.secoes.length} seções
          </p>
        </div>
        <button
          type="button"
          onClick={onFechar}
          aria-label="Fechar"
          className="rounded-lg border border-borda px-2 py-0.5 text-texto-2 hover:bg-realce hover:text-texto"
        >
          ✕
        </button>
      </div>
      {children}
    </div>
  );
}

function celulas(p: { aptos: number; comparecimento: number; abstencoes: number; brancos: number; nulos: number } | undefined) {
  if (!p) return ["—", "—", "—", "—"];
  return [
    numero(p.aptos),
    `${pct(taxa(p, "abstencao") ?? 0)} (${numero(p.abstencoes)})`,
    `${pct(taxa(p, "brancos") ?? 0)} (${numero(p.brancos)})`,
    `${pct(taxa(p, "nulos") ?? 0)} (${numero(p.nulos)})`,
  ];
}

const COLUNAS = ["Eleitores", "Abstenção", "Brancos", "Nulos"];

function TabelaParticipacao({ pontos, cargo, rotulo }: { pontos: PontoItajuba[]; cargo: string; rotulo: string }) {
  return (
    <table className="w-full min-w-[36rem] text-sm">
      <caption className="sr-only">Abstenção, brancos e nulos por {rotulo.toLowerCase()} em Itajubá</caption>
      <thead>
        <tr className="border-b border-borda text-left text-xs text-texto-2">
          <th scope="col" className="py-1 font-medium">{rotulo}</th>
          {COLUNAS.map((c) => (
            <th key={c} scope="col" className="py-1 text-right font-medium">{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {pontos.map((p) => (
          <tr key={p.id} className="border-b border-borda">
            <th scope="row" className="py-1.5 pr-3 text-left font-normal">{p.nome}</th>
            {celulas(p.participacao[cargo]).map((c, i) => (
              <td key={i} className="num py-1.5 pl-3 text-right">{c}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TabelaSecoes({ ponto, cargo }: { ponto: PontoItajuba; cargo: string }) {
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full min-w-[36rem] text-sm">
        <caption className="mb-2 text-left text-xs text-texto-2">Seções de {ponto.nome}</caption>
        <thead>
          <tr className="border-b border-borda text-left text-xs text-texto-2">
            <th scope="col" className="py-1 font-medium">Seção</th>
            {COLUNAS.map((c) => (
              <th key={c} scope="col" className="py-1 text-right font-medium">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ponto.secoes.map((s) => (
            <tr key={s.secao} className="border-b border-borda">
              <th scope="row" className="num py-1.5 text-left font-normal">{s.secao}</th>
              {celulas(s.participacao[cargo]).map((c, i) => (
                <td key={i} className="num py-1.5 pl-3 text-right">{c}</td>
              ))}
            </tr>
          ))}
          <tr className="font-semibold">
            <th scope="row" className="py-1.5 text-left">Total</th>
            {celulas(ponto.participacao[cargo]).map((c, i) => (
              <td key={i} className="num py-1.5 pl-3 text-right">{c}</td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
