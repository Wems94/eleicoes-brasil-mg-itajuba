"use client";

import { useMemo, useState } from "react";

import { NOME_UF, pct } from "@/lib/formato";
import { type Camada, pctCem, rotuloVotavel } from "@/lib/mapa";
import type { CamadaMapa, CelulaMapa } from "@/lib/tipos";

type Municipio = { codigo: string; nome: string };

/**
 * Tabela equivalente ao mapa: por UF na visão Brasil e por município com uma UF
 * aberta, com busca. "Abrir" leva ao mesmo painel do clique no mapa.
 */
export function TabelaMapa({
  camada,
  modo,
  uf,
  municipios,
  onAbrirUf,
  onAbrirMunicipio,
}: {
  camada: CamadaMapa;
  modo: Camada;
  uf: string | null;
  municipios: Municipio[]; // da UF aberta, em ordem alfabética
  onAbrirUf: (uf: string) => void;
  onAbrirMunicipio: (codigo: string) => void;
}) {
  const [busca, setBusca] = useState("");
  const normalizar = (s: string) =>
    s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const filtrados = useMemo(() => {
    const b = normalizar(busca.trim());
    return b ? municipios.filter((m) => normalizar(m.nome).includes(b)) : municipios;
  }, [busca, municipios]);

  const linhas: { chave: string; nome: string; celula: CelulaMapa | undefined; abrir: () => void }[] = uf
    ? filtrados.map((m) => ({
        chave: m.codigo,
        nome: m.nome,
        celula: camada.municipios[m.codigo],
        abrir: () => onAbrirMunicipio(m.codigo),
      }))
    : Object.keys(camada.ufs).map((u) => ({
        chave: u,
        nome: NOME_UF[u] ?? u,
        celula: camada.ufs[u],
        abrir: () => onAbrirUf(u),
      }));

  return (
    <details className="mt-4 rounded-xl border border-borda">
      <summary className="cursor-pointer px-4 py-2.5 text-sm font-medium text-texto-2 hover:text-texto">
        {uf ? `Ver tabela e buscar município de ${NOME_UF[uf] ?? uf}` : "Ver tabela por UF"}
      </summary>
      <div className="px-4 pb-3">
        {uf ? (
          <label className="mb-2 block text-sm">
            <span className="text-texto-2">Buscar município</span>
            <input
              type="search"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-borda bg-superficie px-3 py-1.5 text-sm"
              placeholder="Ex.: Itajubá"
            />
          </label>
        ) : null}
        <div className="max-h-96 overflow-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">
              {camada.nome}: {modo === "abstencao" ? "abstenção" : "mais votado"} por {uf ? "município" : "UF"}
            </caption>
            <thead>
              <tr className="border-b border-borda text-left text-xs text-texto-3">
                <th scope="col" className="py-2 font-medium">{uf ? "Município" : "UF"}</th>
                <th scope="col" className="py-2 font-medium">
                  {camada.por === "partido" ? "Partido mais votado" : "Mais votado"}
                </th>
                <th scope="col" className="py-2 text-right font-medium">Válidos</th>
                <th scope="col" className="py-2 text-right font-medium">Abstenção</th>
                <th scope="col" className="py-2"><span className="sr-only">Ação</span></th>
              </tr>
            </thead>
            <tbody>
              {linhas.map((l) => {
                const [idx, p, a] = l.celula ?? [-2, null, null];
                const v = idx >= 0 ? camada.votaveis[idx] : undefined;
                return (
                  <tr key={l.chave} className="border-b border-borda last:border-0">
                    <th scope="row" className="py-1.5 text-left font-normal">{l.nome}</th>
                    <td className="py-1.5">
                      {idx === -1 ? "Empate" : v ? (
                        <>
                          {rotuloVotavel(v, camada.por)}
                          {camada.por === "candidato" && v.partido ? (
                            <span className="text-xs text-texto-3"> {v.partido}</span>
                          ) : null}
                        </>
                      ) : "—"}
                    </td>
                    <td className="num py-1.5 text-right">{pct(pctCem(p))}</td>
                    <td className="num py-1.5 text-right text-texto-2">{pct(pctCem(a))}</td>
                    <td className="py-1.5 text-right">
                      <button
                        type="button"
                        onClick={l.abrir}
                        className="rounded-md px-2 py-0.5 text-xs font-medium text-texto-2 hover:bg-realce hover:text-texto"
                        aria-label={`Abrir ${l.nome}`}
                      >
                        Abrir
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {uf && filtrados.length === 0 ? <p className="py-2 text-sm text-texto-2">Nenhum município encontrado.</p> : null}
        </div>
      </div>
    </details>
  );
}
