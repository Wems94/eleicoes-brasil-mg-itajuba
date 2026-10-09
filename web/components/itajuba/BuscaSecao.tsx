"use client";

import { useEffect, useId, useState } from "react";

import { numero, pct } from "@/lib/formato";
import { buscarSecao, secoesDisponiveis } from "@/lib/itajuba";
import type { ItajubaSecoes } from "@/lib/tipos";

/** Busca de seção eleitoral: carrega o JSON da eleição só quando a página abre. */
export function BuscaSecao({ ano, turno }: { ano: number; turno: number }) {
  const id = useId();
  const [dados, setDados] = useState<ItajubaSecoes | null>(null);
  const [erro, setErro] = useState(false);
  const [escolha, setEscolha] = useState("");

  useEffect(() => {
    setDados(null);
    setEscolha("");
    fetch(`/dados/${ano}/${turno}/itajuba_secoes.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setDados)
      .catch(() => setErro(true));
  }, [ano, turno]);

  if (erro) return <p className="text-sm text-tinta-2">Não foi possível carregar as seções.</p>;
  if (!dados) return <p className="text-sm text-tinta-2">Carregando seções…</p>;

  const opcoes = secoesDisponiveis(dados);
  const [zona, secao] = escolha.split("-").map(Number);
  const r = escolha ? buscarSecao(dados, zona, secao) : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-3">
        <label htmlFor={id} className="text-sm">
          <span className="block text-xs uppercase tracking-wider text-tinta-2">Zona e seção</span>
          <select
            id={id}
            value={escolha}
            onChange={(e) => setEscolha(e.target.value)}
            className="num mt-1 border border-tinta bg-papel px-3 py-2"
          >
            <option value="">Escolha uma seção…</option>
            {opcoes.map((o) => (
              <option key={`${o.zona}-${o.secao}`} value={`${o.zona}-${o.secao}`}>
                Zona {o.zona} · Seção {o.secao}
              </option>
            ))}
          </select>
        </label>
        <p className="text-xs text-tinta-2">{numero(opcoes.length)} seções nesta eleição</p>
      </div>

      <div aria-live="polite">
        {r ? (
          <div className="grid gap-8 md:grid-cols-2">
            {r.cargos.map((c) => (
              <table key={c.codigo} className="w-full text-sm">
                <caption className="mb-2 text-left">
                  <span className="font-display text-lg font-semibold">{c.nome}</span>
                  {c.comparecimento ? (
                    <span className="num block text-xs text-tinta-2">
                      {numero(c.comparecimento.comparecimento)} de {numero(c.comparecimento.aptos)}{" "}
                      aptos compareceram (
                      {pct((100 * c.comparecimento.comparecimento) / c.comparecimento.aptos)})
                    </span>
                  ) : null}
                </caption>
                <thead className="sr-only">
                  <tr>
                    <th scope="col">Votável</th>
                    <th scope="col">Votos</th>
                  </tr>
                </thead>
                <tbody>
                  {c.votos.map((v) => (
                    <tr key={v.numero} className="border-b border-regua">
                      <th scope="row" className="py-1 text-left font-normal">
                        {v.nome}
                        {v.numero < 95 || v.numero > 97 ? (
                          <span className="num ml-1.5 text-xs text-tinta-2">{v.numero}</span>
                        ) : null}
                      </th>
                      <td className="num py-1 text-right">{numero(v.votos)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ))}
          </div>
        ) : escolha ? (
          <p className="text-sm text-tinta-2">Seção não encontrada.</p>
        ) : null}
      </div>
    </div>
  );
}
