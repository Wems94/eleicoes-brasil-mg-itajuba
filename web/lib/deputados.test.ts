import { describe, expect, it } from "vitest";

import { VISIVEIS, visiveis } from "./deputados";
import type { Candidato } from "./tipos";

const c = (posicao: number, situacao: string | null): Candidato => ({
  numero: 1000 + posicao, nome: `C${posicao}`, partido: "X", federacao: null,
  votos: 10_000 - posicao, pct: null, situacao, posicao,
});

describe("deputados visíveis na página", () => {
  it("mostra os mais votados e nenhum eleito fica de fora", () => {
    // eleito por média bem abaixo no ranking (acontece nos dados reais)
    const lista = Array.from({ length: 200 }, (_, i) =>
      c(i + 1, i === 150 ? "ELEITO POR MÉDIA" : i < 5 ? "ELEITO POR QP" : "SUPLENTE"),
    );
    const v = visiveis(lista);
    expect(v).toHaveLength(VISIVEIS + 1);
    expect(v.map((x) => x.posicao)).toContain(151);
  });

  it("lista curta aparece inteira", () => {
    expect(visiveis([c(1, "ELEITO"), c(2, null)])).toHaveLength(2);
  });
});
