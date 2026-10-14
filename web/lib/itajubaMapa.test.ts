import path from "node:path";
import { describe, expect, it } from "vitest";

import { SnapshotsDados } from "./dados";
import { colocados, pontosPorBairro, pontosPorLocal, raio, taxa } from "./itajubaMapa";

const dados = new SnapshotsDados(path.resolve(import.meta.dirname, "..", ".snapshots-fixture"));
const it22 = dados.itajuba(2022, 1);
const secoes = dados.itajubaSecoes(2022, 1);

describe("mapas de Itajubá", () => {
  const locais = pontosPorLocal(it22, secoes);

  it("soma as seções de cada local", () => {
    expect(locais.length).toBeGreaterThan(0);
    for (const l of locais) {
      const somaAptos = l.secoes.reduce((s, x) => s + (x.participacao["1"]?.aptos ?? 0), 0);
      expect(l.participacao["1"]?.aptos ?? 0).toBe(somaAptos);
      expect(l.aptos).toBe(somaAptos);
    }
  });

  it("os bairros somam os mesmos eleitores dos locais", () => {
    const bairros = pontosPorBairro(locais);
    const total = (ps: typeof locais) => ps.reduce((s, p) => s + p.aptos, 0);
    expect(total(bairros)).toBe(total(locais));
    expect(new Set(bairros.map((b) => b.bairro)).size).toBe(bairros.length);
    const votos = (ps: typeof locais) => ps.reduce((s, p) => s + (p.votos["1"] ?? []).reduce((a, v) => a + v.votos, 0), 0);
    expect(votos(bairros)).toBe(votos(locais));
  });

  it("colocados em ordem, com percentual sobre os votos nos candidatos", () => {
    const [primeiro, segundo] = colocados(locais[0], 1, 2);
    expect(primeiro.votos).toBeGreaterThanOrEqual(segundo?.votos ?? 0);
    const total = (locais[0].votos["1"] ?? []).reduce((s, v) => s + v.votos, 0);
    expect(primeiro.pct).toBeCloseTo((100 * primeiro.votos) / total);
  });

  it("calcula as taxas sobre a base certa", () => {
    const p = { aptos: 200, comparecimento: 160, abstencoes: 40, brancos: 8, nulos: 4 };
    expect(taxa(p, "abstencao")).toBe(20);
    expect(taxa(p, "brancos")).toBe(5);
    expect(taxa(p, "nulos")).toBe(2.5);
    expect(taxa({ ...p, aptos: 0, comparecimento: 0 }, "nulos")).toBeNull();
    expect(taxa(undefined, "abstencao")).toBeNull();
  });

  it("raio cresce com a raiz do eleitorado", () => {
    expect(raio(0, 100)).toBe(4);
    expect(raio(100, 100)).toBe(13);
    expect(raio(25, 100)).toBeCloseTo(4 + 9 * 0.5);
  });
});
