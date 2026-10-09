"use client";

import { useState } from "react";

import { CabecaDeputados, LinhasDeputados } from "@/components/LinhasDeputados";
import { numero } from "@/lib/formato";
import type { Candidato } from "@/lib/tipos";

/** Carrega o restante dos candidatos de um JSON estático, só quando pedido. */
export function ListaCompleta({
  url,
  codigo,
  legenda,
  ocultos,
  jaMostrados,
}: {
  url: string;
  codigo: number;
  legenda: string;
  ocultos: number;
  jaMostrados: number[];
}) {
  const [estado, setEstado] = useState<"fechado" | "carregando" | "erro" | Candidato[]>("fechado");

  async function abrir() {
    setEstado("carregando");
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(String(r.status));
      const listas: Record<string, Candidato[]> = await r.json();
      const vistos = new Set(jaMostrados);
      setEstado((listas[String(codigo)] ?? []).filter((c) => !vistos.has(c.numero)));
    } catch {
      setEstado("erro");
    }
  }

  if (Array.isArray(estado)) {
    return (
      <table className="mt-2 w-full min-w-[36rem] text-sm">
        <caption className="sr-only">{legenda}: demais candidatos</caption>
        <CabecaDeputados />
        <tbody>
          <LinhasDeputados candidatos={estado} />
        </tbody>
      </table>
    );
  }
  return (
    <div className="mt-3" aria-live="polite">
      <button
        type="button"
        onClick={abrir}
        disabled={estado === "carregando"}
        className="rounded-lg border border-borda px-3 py-1.5 text-sm font-medium text-texto-2 hover:bg-realce hover:text-texto disabled:opacity-60"
      >
        {estado === "carregando" ? "Carregando…" : `Ver os outros ${numero(ocultos)} candidatos`}
      </button>
      {estado === "erro" ? (
        <p className="mt-2 text-xs text-texto-2">Não foi possível carregar a lista completa.</p>
      ) : null}
    </div>
  );
}
